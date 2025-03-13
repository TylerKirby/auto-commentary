import sys
import warnings

from setuptools import find_packages, setup

# Define core requirements
core_requirements = [
    "cltk>=1.1.6",
    "requests>=2.28.2",
    "tqdm>=4.65.0",
]

# Define development requirements
dev_requirements = [
    "pytest>=7.3.1,<8.0.0",
]

# Check if whitakers_words is already installed
try:
    import whitakers_words

    has_whitakers = True
except ImportError:
    has_whitakers = False
    warnings.warn(
        "\nThe whitakers_words package is required but could not be found.\n"
        "Please install it with one of the following methods:\n"
        "1. pip install git+https://github.com/blagae/whitakers_words.git\n"
        "2. Clone and install manually: \n"
        "   git clone https://github.com/blagae/whitakers_words.git\n"
        "   cd whitakers_words\n"
        "   pip install -e .\n"
        "See the README.md for more installation options."
    )

setup(
    name="autocom",
    version="0.1.0",
    packages=find_packages(),
    install_requires=core_requirements,
    dependency_links=[
        "git+https://github.com/blagae/whitakers_words.git#egg=whitakers_words",
    ],
    extras_require={
        "dev": dev_requirements,
        "all": dev_requirements + ["whitakers_words"],
    },
    python_requires=">=3.9",
    author="Your Name",
    author_email="your.email@example.com",
    description="Auto-commentary tool for Latin and Greek texts",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
