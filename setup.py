from setuptools import setup, find_packages
import os


def get_version():
    """Get version from __init__.py"""
    init_file = os.path.join(os.path.dirname(__file__), "ragparser", "__init__.py")
    if os.path.exists(init_file):
        with open(init_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("__version__"):
                    return line.split("=")[1].strip().strip('"').strip("'")
    return "1.0.5"


def get_long_description():
    """Get long description from README.md"""
    readme_path = os.path.join(os.path.dirname(__file__), "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as fh:
            return fh.read()
    return ""


def get_requirements():
    """Get requirements from requirements.txt"""
    req_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
    requirements = ["aiofiles>=0.8.0"]

    if os.path.exists(req_path):
        with open(req_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#"):
                    requirements.append(line)

    return requirements


setup(
    name="ragparser",
    version=get_version(),
    author="Shubham Shinde",
    author_email="shubhamshinde7995@gmail.com",
    description="A comprehensive document parser for RAG applications with support for PDF, DOCX, PPTX, XLSX, and more",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    url="https://github.com/shubham7995/ragparser",
    project_urls={
        "Bug Tracker": "https://github.com/shubham7995/ragparser/issues",
        "Documentation": "https://github.com/shubham7995/ragparser#readme",
        "Source": "https://github.com/shubham7995/ragparser",
        "Download": "https://pypi.org/project/ragparser/",
    },
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Text Processing :: Markup",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Framework :: AsyncIO",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "Natural Language :: English",
    ],
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=["aiofiles>=0.8.0"],
    extras_require={
        "pdf": [
            "PyMuPDF>=1.23.0",
            "pdfplumber>=0.9.0",
        ],
        "office": [
            "python-docx>=0.8.11",
            "python-pptx>=0.6.21",
            "openpyxl>=3.1.0",
        ],
        "html": [
            "beautifulsoup4>=4.11.0",
            "lxml>=4.9.0",
        ],
        "ocr": [
            "pytesseract>=0.3.10",
            "Pillow>=9.0.0",
        ],
        "advanced": [
            "sentence-transformers>=2.2.0",
            "nltk>=3.8",
            "spacy>=3.5.0",
        ],
        "all": [
            "PyMuPDF>=1.23.0",
            "pdfplumber>=0.9.0",
            "python-docx>=0.8.11",
            "python-pptx>=0.6.21",
            "openpyxl>=3.1.0",
            "beautifulsoup4>=4.11.0",
            "lxml>=4.9.0",
            "pytesseract>=0.3.10",
            "Pillow>=9.0.0",
            "sentence-transformers>=2.2.0",
            "nltk>=3.8",
            "spacy>=3.5.0",
        ],
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=23.0",
            "mypy>=1.0",
            "flake8>=6.0",
            "pre-commit>=3.0.0",
            "twine>=4.0.0",
        ],
        "test": [
            "pytest>=7.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "pytest-mock>=3.10.0",
        ],
        "langchain": [
            "langchain>=0.1.0",
            "langchain-community>=0.0.10",
        ],
        "llamaindex": [
            "llama-index>=0.9.0",
        ],
    },
    keywords=[
        "rag",
        "document parsing",
        "pdf",
        "docx",
        "pptx",
        "xlsx",
        "chunking",
        "embedding",
        "langchain",
        "llamaindex",
        "async",
        "ocr",
        "metadata extraction",
        "artificial intelligence",
        "machine learning",
        "nlp",
        "text processing",
    ],
    include_package_data=True,
    zip_safe=False,
)
