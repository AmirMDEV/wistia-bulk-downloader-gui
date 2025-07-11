#!/usr/bin/env python3
"""
Setup script for Wistia Video Downloader
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (
    (this_directory / "README.md").read_text(encoding="utf-8")
    if (this_directory / "README.md").exists()
    else ""
)

setup(
    name="wistia-downloader",
    version="1.0.0",
    author="Ahmet Emre Aladağ",
    description="A production-ready CLI tool for downloading Wistia videos",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/aladagemre/wistia-downloader",
    py_modules=["wistia"],
    python_requires=">=3.6",
    install_requires=[
        "requests>=2.25.1",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "black>=21.0",
            "flake8>=3.8",
        ],
    },
    entry_points={
        "console_scripts": [
            "wistia=wistia:main",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Multimedia :: Video",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Utilities",
    ],
    keywords="wistia video downloader cli batch download",
    project_urls={
        "Bug Reports": "https://github.com/aladagemre/wistia-downloader/issues",
        "Source": "https://github.com/aladagemre/wistia-downloader",
    },
)
