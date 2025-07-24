"""
Metadata extraction processor
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime

from ..core.models import ParsedDocument, ParserConfig, DocumentMetadata


class MetadataExtractor:
    """Extract and enhance document metadata"""
    
    async def extract_async(
        self, 
        file_path: Optional[Path], 
        document: ParsedDocument, 
        config: ParserConfig
    ) -> DocumentMetadata:
        """
        Extract enhanced metadata from document
        
        Args:
            file_path: Original file path (if available)
            document: Parsed document
            config: Parser configuration
            
        Returns:
            Enhanced metadata
        """
        metadata = document.metadata
        
        try:
            # File system metadata
            if file_path and file_path.exists():
                metadata = await self._extract_file_metadata(file_path, metadata)
            
            # Content-based metadata
            metadata = await self._extract_content_metadata(document, metadata, config)
            
            # Language detection
            if config.custom_settings.get('detect_language', False):
                metadata.language = await self._detect_language(document.content)
            
            # Document structure analysis
            metadata = await self._analyze_structure(document, metadata)
            
        except Exception as e:
            logging.warning(f"Error extracting metadata: {str(e)}")
        
        return metadata
    
    async def _extract_file_metadata(self, file_path: Path, metadata: DocumentMetadata) -> DocumentMetadata:
        """Extract file system metadata"""
        try:
            stat = file_path.stat()
            
            # Update file size if not set
            if not metadata.file_size:
                metadata.file_size = stat.st_size
            
            # Update dates if not set
            if not metadata.creation_date:
                metadata.creation_date = datetime.fromtimestamp(stat.st_ctime)
            
            if not metadata.modification_date:
                metadata.modification_date = datetime.fromtimestamp(stat.st_mtime)
            
            # Add file system metadata
            metadata.custom_metadata.update({
                'file_path': str(file_path),
                'file_extension': file_path.suffix.lower(),
                'file_stem': file_path.stem,
                'access_time': datetime.fromtimestamp(stat.st_atime).isoformat(),
                'inode': stat.st_ino if hasattr(stat, 'st_ino') else None,
            })
            
        except Exception as e:
            logging.warning(f"Error extracting file metadata: {str(e)}")
        
        return metadata
    
    async def _extract_content_metadata(
        self, 
        document: ParsedDocument, 
        metadata: DocumentMetadata, 
        config: ParserConfig
    ) -> DocumentMetadata:
        """Extract metadata from document content"""
        
        content = document.content
        
        # Word and character counts
        if not metadata.word_count:
            metadata.word_count = len(content.split())
        
        if not metadata.character_count:
            metadata.character_count = len(content)
        
        # Content analysis
        content_stats = await self._analyze_content_stats(content)
        metadata.custom_metadata.update(content_stats)
        
        # Extract potential title if not set
        if not metadata.title:
            metadata.title = await self._extract_title_from_content(document)
        
        # Extract potential author mentions
        if not metadata.author:
            metadata.author = await self._extract_author_from_content(content)
        
        return metadata
    
    async def _analyze_content_stats(self, content: str) -> Dict[str, Any]:
        """Analyze content statistics"""
        stats = {}
        
        try:
            lines = content.split('\n')
            paragraphs = content.split('\n\n')
            sentences = content.split('.')
            words = content.split()
            
            # Calculate word count from current content
            word_count = len(words)
            sentence_count = len([s for s in sentences if s.strip()])
            
            stats.update({
                'line_count': len(lines),
                'paragraph_count': len([p for p in paragraphs if p.strip()]),
                'sentence_count': sentence_count,
                'word_count': word_count,
                'avg_words_per_sentence': word_count / max(sentence_count, 1),
                'avg_chars_per_word': len(content) / max(word_count, 1),
                'whitespace_ratio': len([c for c in content if c.isspace()]) / max(len(content), 1),
                'uppercase_ratio': len([c for c in content if c.isupper()]) / max(len(content), 1),
                'digit_ratio': len([c for c in content if c.isdigit()]) / max(len(content), 1),
            })
            
        except Exception as e:
            logging.warning(f"Error analyzing content stats: {str(e)}")
        
        return stats
    
    async def _extract_title_from_content(self, document: ParsedDocument) -> Optional[str]:
        """Extract title from document content"""
        
        # Try to find title from content blocks
        for block in document.content_blocks:
            if block.block_type in ['title', 'header_1']:
                title = block.content.strip()
                if len(title) > 3 and len(title) < 200:  # Reasonable title length
                    return title
        
        # Try first line if it looks like a title
        lines = document.content.split('\n')
        if lines:
            first_line = lines[0].strip()
            if (len(first_line) > 3 and len(first_line) < 200 and 
                not first_line.endswith('.') and
                len(first_line.split()) < 20):  # Not too many words
                return first_line
        
        return None
    
    async def _extract_author_from_content(self, content: str) -> Optional[str]:
        """Extract author from content using patterns"""
        import re
        
        # Common author patterns
        patterns = [
            r'[Bb]y\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'[Aa]uthor:?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'[Ww]ritten\s+by\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'^([A-Z][a-z]+\s+[A-Z][a-z]+)\s*$',  # Name on its own line
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content[:1000])  # Search first 1000 chars
            if matches:
                return matches[0].strip()
        
        return None
    
    async def _detect_language(self, content: str) -> Optional[str]:
        """Detect document language"""
        try:
            # Try using langdetect if available
            try:
                from langdetect import detect
                return detect(content[:1000])  # Use first 1000 chars for detection
            except ImportError:
                pass
            
            # Simple English detection fallback
            english_words = ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']
            words = content.lower().split()[:100]  # First 100 words
            
            english_count = sum(1 for word in words if word in english_words)
            if english_count / max(len(words), 1) > 0.1:  # 10% threshold
                return 'en'
            
        except Exception as e:
            logging.warning(f"Error detecting language: {str(e)}")
        
        return None
    
    async def _analyze_structure(self, document: ParsedDocument, metadata: DocumentMetadata) -> DocumentMetadata:
        """Analyze document structure"""
        
        structure_info = {
            'has_headers': False,
            'header_levels': [],
            'has_tables': len(document.tables) > 0,
            'has_images': len(document.images) > 0,
            'has_links': len(document.links) > 0,
            'content_block_types': {},
            'table_count': len(document.tables),
            'image_count': len(document.images),
            'link_count': len(document.links),
        }
        
        # Analyze content blocks
        for block in document.content_blocks:
            block_type = block.block_type
            structure_info['content_block_types'][block_type] = structure_info['content_block_types'].get(block_type, 0) + 1
            
            if block_type.startswith('header'):
                structure_info['has_headers'] = True
                if block.formatting and 'header_level' in block.formatting:
                    level = block.formatting['header_level']
                    if level not in structure_info['header_levels']:
                        structure_info['header_levels'].append(level)
        
        # Sort header levels
        structure_info['header_levels'].sort()
        
        # Calculate structure complexity
        complexity_score = 0
        complexity_score += len(structure_info['content_block_types']) * 2
        complexity_score += len(structure_info['header_levels']) * 3
        complexity_score += structure_info['table_count'] * 5
        complexity_score += structure_info['image_count'] * 2
        complexity_score += min(structure_info['link_count'], 10)  # Cap at 10
        
        structure_info['complexity_score'] = complexity_score
        
        metadata.custom_metadata.update(structure_info)
        
        return metadata