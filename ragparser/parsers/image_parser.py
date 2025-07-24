"""
Image parser with OCR support
"""

import asyncio
import logging
from typing import List, Dict, Any
from pathlib import Path
import io

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

from .base import BaseParser
from ..core.models import (
    ParsedDocument, ParserConfig, FileType, ContentBlock
)
from ..core.exceptions import ProcessingError


class ImageParser(BaseParser):
    """Parser for image files with OCR support"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = [FileType.IMAGE]
        
        if not HAS_PIL:
            raise ImportError(
                "Image parsing requires Pillow. Install with: pip install Pillow"
            )
    
    async def parse_async(self, file_path: Path, config: ParserConfig) -> ParsedDocument:
        """Parse image file asynchronously"""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, self._parse_image_sync, str(file_path), config
            )
        except Exception as e:
            raise ProcessingError(f"Failed to parse image: {str(e)}", e)
    
    async def parse_from_bytes_async(
        self, data: bytes, filename: str, config: ParserConfig
    ) -> ParsedDocument:
        """Parse image from bytes asynchronously"""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, self._parse_image_from_bytes_sync, data, filename, config
            )
        except Exception as e:
            raise ProcessingError(f"Failed to parse image from bytes: {str(e)}", e)
    
    def _parse_image_sync(self, file_path: str, config: ParserConfig) -> ParsedDocument:
        """Synchronous image parsing"""
        path = Path(file_path)
        document = asyncio.run(self._create_base_document(
            path, path.name, FileType.IMAGE, path.stat().st_size
        ))
        
        try:
            with Image.open(file_path) as img:
                return self._extract_content(img, document, config, file_path)
        except Exception as e:
            raise ProcessingError(f"Failed to open image: {str(e)}", e)
    
    def _parse_image_from_bytes_sync(
        self, data: bytes, filename: str, config: ParserConfig
    ) -> ParsedDocument:
        """Synchronous image parsing from bytes"""
        document = asyncio.run(self._create_base_document(
            None, filename, FileType.IMAGE, len(data)
        ))
        
        try:
            with Image.open(io.BytesIO(data)) as img:
                return self._extract_content(img, document, config, filename)
        except Exception as e:
            raise ProcessingError(f"Failed to open image from bytes: {str(e)}", e)
    
    def _extract_content(
        self, img: Image.Image, document: ParsedDocument, config: ParserConfig, source: str
    ) -> ParsedDocument:
        """Extract content from image"""
        
        # Extract image metadata
        document.metadata = self._extract_image_metadata(img, document.metadata)
        
        # Store image information
        document.images.append({
            "source": source,
            "format": img.format,
            "mode": img.mode,
            "size": img.size,
            "has_transparency": img.mode in ['RGBA', 'LA'] or 'transparency' in img.info
        })
        
        # Extract text using OCR if enabled
        extracted_text = ""
        if config.enable_ocr:
            extracted_text = self._extract_text_with_ocr(img, config)
        
        if extracted_text.strip():
            document.content = extracted_text
            document.content_blocks.append(ContentBlock(
                content=extracted_text,
                block_type="ocr_text",
                confidence=self._estimate_ocr_confidence(extracted_text, config)
            ))
        else:
            # No text extracted
            document.content = f"[Image: {document.metadata.file_name}]"
            document.content_blocks.append(ContentBlock(
                content=document.content,
                block_type="image_placeholder"
            ))
        
        # Update metadata
        document.metadata.word_count = len(document.content.split())
        document.metadata.character_count = len(document.content)
        
        return document
    
    def _extract_image_metadata(self, img: Image.Image, metadata) -> any:
        """Extract metadata from image"""
        
        # Basic image properties
        metadata.custom_metadata.update({
            'image_format': img.format,
            'image_mode': img.mode,
            'image_size': img.size,
            'image_width': img.size[0],
            'image_height': img.size[1],
        })
        
        # EXIF data if available
        if hasattr(img, '_getexif') and img._getexif():
            try:
                exif_data = {}
                exif = img._getexif()
                
                # Common EXIF tags
                exif_tags = {
                    271: 'make',
                    272: 'model', 
                    306: 'datetime',
                    34665: 'exif_ifd',
                    36867: 'datetime_original',
                    36868: 'datetime_digitized',
                }
                
                for tag_id, tag_name in exif_tags.items():
                    if tag_id in exif:
                        exif_data[tag_name] = str(exif[tag_id])
                
                if exif_data:
                    metadata.custom_metadata['exif'] = exif_data
                    
            except Exception as e:
                logging.warning(f"Error extracting EXIF data: {str(e)}")
        
        # Image info
        if img.info:
            metadata.custom_metadata['image_info'] = {
                k: str(v) for k, v in img.info.items() 
                if isinstance(v, (str, int, float))
            }
        
        return metadata
    
    def _extract_text_with_ocr(self, img: Image.Image, config: ParserConfig) -> str:
        """Extract text from image using OCR"""
        
        if not HAS_TESSERACT:
            logging.warning("Tesseract not available for OCR")
            return ""
        
        try:
            # Preprocess image for better OCR
            processed_img = self._preprocess_image_for_ocr(img)
            
            # Configure Tesseract
            ocr_config = self._get_tesseract_config(config)
            
            # Extract text
            extracted_text = pytesseract.image_to_string(
                processed_img, 
                lang=config.ocr_language,
                config=ocr_config
            )
            
            # Clean OCR output
            cleaned_text = self._clean_ocr_text(extracted_text, config)
            
            return cleaned_text
            
        except Exception as e:
            logging.warning(f"OCR extraction failed: {str(e)}")
            return ""
    
    def _preprocess_image_for_ocr(self, img: Image.Image) -> Image.Image:
        """Preprocess image to improve OCR accuracy"""
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize if image is too small (OCR works better on larger images)
        width, height = img.size
        if width < 300 or height < 300:
            scale_factor = max(300 / width, 300 / height)
            new_size = (int(width * scale_factor), int(height * scale_factor))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Convert to grayscale for better OCR
        img = img.convert('L')
        
        # Enhance contrast
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)
        
        return img
    
    def _get_tesseract_config(self, config: ParserConfig) -> str:
        """Get Tesseract configuration string"""
        
        # Base configuration
        tesseract_config = '--oem 3 --psm 6'  # LSTM OCR Engine, uniform text block
        
        # Add custom configurations
        if config.custom_settings.get('ocr_psm'):
            psm = config.custom_settings['ocr_psm']
            tesseract_config = tesseract_config.replace('--psm 6', f'--psm {psm}')
        
        if config.custom_settings.get('ocr_whitelist'):
            whitelist = config.custom_settings['ocr_whitelist']
            tesseract_config += f' -c tessedit_char_whitelist={whitelist}'
        
        return tesseract_config
    
    def _clean_ocr_text(self, text: str, config: ParserConfig) -> str:
        """Clean OCR output text"""
        
        if not text:
            return ""
        
        # Remove extra whitespace
        import re
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Remove common OCR artifacts
        artifacts = [
            r'[|Il1]{3,}',  # Vertical lines misread as characters
            r'[^\w\s.,!?;:()\-\'"]{3,}',  # Long sequences of special characters
        ]
        
        for pattern in artifacts:
            text = re.sub(pattern, '', text)
        
        # Fix common OCR errors
        corrections = {
            r'\b0\b': 'O',  # Zero to O
            r'\bl\b': 'I',  # lowercase l to I (context dependent)
            r'\s+([,.!?;:])': r'\1',  # Remove space before punctuation
        }
        
        for pattern, replacement in corrections.items():
            text = re.sub(pattern, replacement, text)
        
        return text.strip()
    
    def _estimate_ocr_confidence(self, text: str, config: ParserConfig) -> float:
        """Estimate OCR confidence based on text characteristics"""
        
        if not text.strip():
            return 0.0
        
        confidence = 1.0
        
        # Penalize for too many special characters (likely OCR errors)
        import re
        special_chars = len(re.findall(r'[^\w\s.,!?;:()\-\'"]', text))
        if special_chars > 0:
            special_ratio = special_chars / len(text)
            confidence *= max(0.3, 1.0 - special_ratio * 2)
        
        # Penalize for very short words (often OCR errors)
        words = text.split()
        if words:
            short_words = len([w for w in words if len(w) == 1])
            short_ratio = short_words / len(words)
            confidence *= max(0.5, 1.0 - short_ratio)
        
        # Penalize for excessive uppercase (often OCR errors)
        if text.isupper() and len(text) > 20:
            confidence *= 0.7
        
        # Boost confidence for dictionary words
        if config.custom_settings.get('ocr_dictionary_check', False):
            confidence = self._check_dictionary_words(text, confidence)
        
        return max(0.0, min(1.0, confidence))
    
    def _check_dictionary_words(self, text: str, base_confidence: float) -> float:
        """Check OCR text against dictionary for confidence boost"""
        
        try:
            # Simple English word check
            common_words = {
                'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
                'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after',
                'above', 'below', 'between', 'among', 'under', 'over', 'around'
            }
            
            words = text.lower().split()
            if len(words) > 5:
                common_word_count = sum(1 for word in words if word in common_words)
                common_ratio = common_word_count / len(words)
                
                if common_ratio > 0.15:  # 15% common words is good
                    base_confidence *= 1.2
                elif common_ratio < 0.05:  # Less than 5% is suspicious
                    base_confidence *= 0.8
            
        except Exception:
            pass
        
        return base_confidence