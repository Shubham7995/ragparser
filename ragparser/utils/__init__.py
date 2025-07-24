"""Utility modules"""

from .file_detector import FileDetector

# Optional HTTP client
try:
    from .http_client import HttpClient, download_file_from_url, get_url_file_info

    __all__ = [
        "FileDetector",
        "HttpClient",
        "download_file_from_url",
        "get_url_file_info",
    ]
except ImportError:
    __all__ = ["FileDetector"]
