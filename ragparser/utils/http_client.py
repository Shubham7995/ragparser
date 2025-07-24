"""
HTTP client utilities for RAG parser (for downloading remote files)
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from pathlib import Path

try:
    import httpx

    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

from ..core.exceptions import ProcessingError


class HttpClient:
    """HTTP client for downloading remote documents"""

    def __init__(
        self,
        timeout: float = 30.0,
        max_file_size: int = 100 * 1024 * 1024,  # 100MB
        follow_redirects: bool = True,
    ):
        """
        Initialize HTTP client

        Args:
            timeout: Request timeout in seconds
            max_file_size: Maximum file size to download
            follow_redirects: Whether to follow redirects
        """
        if not HAS_HTTPX:
            raise ImportError(
                "HTTP client requires httpx. Install with: pip install httpx"
            )

        self.timeout = timeout
        self.max_file_size = max_file_size
        self.follow_redirects = follow_redirects
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry"""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout), follow_redirects=self.follow_redirects
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def download_file(self, url: str) -> bytes:
        """
        Download file from URL

        Args:
            url: URL to download from

        Returns:
            File content as bytes

        Raises:
            ProcessingError: If download fails
        """
        if not self._client:
            raise ProcessingError(
                "HTTP client not initialized. Use async context manager."
            )

        try:
            logging.info(f"Downloading file from: {url}")

            # Stream download to handle large files
            async with self._client.stream("GET", url) as response:
                response.raise_for_status()

                # Check content length
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > self.max_file_size:
                    raise ProcessingError(
                        f"File too large: {content_length} bytes exceeds limit of {self.max_file_size}"
                    )

                # Download in chunks
                content = b""
                downloaded = 0

                async for chunk in response.aiter_bytes(chunk_size=8192):
                    content += chunk
                    downloaded += len(chunk)

                    # Check size limit during download
                    if downloaded > self.max_file_size:
                        raise ProcessingError(
                            f"File too large: {downloaded} bytes exceeds limit of {self.max_file_size}"
                        )

                logging.info(f"Downloaded {downloaded} bytes from {url}")
                return content

        except httpx.HTTPStatusError as e:
            raise ProcessingError(
                f"HTTP error downloading {url}: {e.response.status_code}"
            )
        except httpx.RequestError as e:
            raise ProcessingError(f"Request error downloading {url}: {str(e)}")
        except Exception as e:
            raise ProcessingError(f"Unexpected error downloading {url}: {str(e)}")

    async def get_file_info(self, url: str) -> Dict[str, Any]:
        """
        Get file information without downloading

        Args:
            url: URL to get info for

        Returns:
            Dictionary with file information
        """
        if not self._client:
            raise ProcessingError(
                "HTTP client not initialized. Use async context manager."
            )

        try:
            response = await self._client.head(url)
            response.raise_for_status()

            info = {
                "url": url,
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type"),
                "content_length": response.headers.get("content-length"),
                "last_modified": response.headers.get("last-modified"),
                "etag": response.headers.get("etag"),
            }

            # Try to determine filename
            content_disposition = response.headers.get("content-disposition")
            if content_disposition:
                import re

                filename_match = re.search(r"filename[*]?=([^;]+)", content_disposition)
                if filename_match:
                    filename = filename_match.group(1).strip("\"'")
                    info["filename"] = filename

            # Fallback to URL path
            if "filename" not in info:
                path = Path(url).name
                if path and "." in path:
                    info["filename"] = path

            return info

        except httpx.HTTPStatusError as e:
            raise ProcessingError(
                f"HTTP error getting info for {url}: {e.response.status_code}"
            )
        except httpx.RequestError as e:
            raise ProcessingError(f"Request error getting info for {url}: {str(e)}")
        except Exception as e:
            raise ProcessingError(f"Unexpected error getting info for {url}: {str(e)}")


async def download_file_from_url(
    url: str, timeout: float = 30.0, max_file_size: int = 100 * 1024 * 1024
) -> bytes:
    """
    Convenience function to download file from URL

    Args:
        url: URL to download from
        timeout: Request timeout in seconds
        max_file_size: Maximum file size to download

    Returns:
        File content as bytes
    """
    async with HttpClient(timeout=timeout, max_file_size=max_file_size) as client:
        return await client.download_file(url)


async def get_url_file_info(url: str, timeout: float = 30.0) -> Dict[str, Any]:
    """
    Convenience function to get file info from URL

    Args:
        url: URL to get info for
        timeout: Request timeout in seconds

    Returns:
        Dictionary with file information
    """
    async with HttpClient(timeout=timeout) as client:
        return await client.get_file_info(url)
