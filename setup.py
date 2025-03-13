#!/usr/bin/env python
from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="autocom",
    version="0.2.0",
    author="Tyler Kirby",
    author_email="tyler.kirby9398@gmail.com",
    description="Automatic commentary generator for Latin and Greek texts",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tylerkirby/auto-commentary",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.25.0",
        "unicodedata2>=15.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "black>=21.5b2",
            "flake8>=3.9.0",
            "isort>=5.9.0",
        ],
        "advanced": [
            "cltk>=1.0.0",  # For enhanced Latin and Greek NLP
            "PyPDF2>=2.0.0",  # For PDF processing
            "pylatexenc>=2.0",  # For enhanced LaTeX handling
        ],
    },
    entry_points={
        "console_scripts": [
            "autocom=autocom.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "autocom": ["data/*.json"],
    },
)
