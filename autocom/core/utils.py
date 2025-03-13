"""
Core Utilities Module.

This module provides utility functions that are used across the application.
"""

import json
import os
import pickle
from pathlib import Path
from typing import Any, Dict, List, Union


def get_cache_dir() -> Path:
    """
    Get the directory for caching data.

    Returns:
        Path: Path to the cache directory
    """
    cache_dir = Path(os.path.expanduser("~/.autocom/cache"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def load_cache(cache_name: str) -> Dict:
    """
    Load cached data from disk.

    Args:
        cache_name: Name of the cache file

    Returns:
        Dict: Cached data or empty dict if no cache exists
    """
    cache_path = get_cache_dir() / f"{cache_name}.pkl"

    if cache_path.exists():
        try:
            with open(cache_path, "rb") as f:
                return pickle.load(f)
        except (pickle.PickleError, EOFError):
            return {}

    return {}


def save_cache(cache_name: str, data: Dict) -> None:
    """
    Save data to cache.

    Args:
        cache_name: Name of the cache file
        data: Data to cache
    """
    cache_path = get_cache_dir() / f"{cache_name}.pkl"

    with open(cache_path, "wb") as f:
        pickle.dump(data, f)


def clear_cache(cache_name: str = None) -> None:
    """
    Clear the specified cache or all caches if none specified.

    Args:
        cache_name: Optional name of specific cache to clear
    """
    cache_dir = get_cache_dir()

    if cache_name:
        cache_path = cache_dir / f"{cache_name}.pkl"
        if cache_path.exists():
            os.remove(cache_path)
    else:
        for cache_file in cache_dir.glob("*.pkl"):
            os.remove(cache_file)


def read_data_file(filename: str) -> Any:
    """
    Read data from a JSON file in the data directory.

    Args:
        filename: Name of the file (with or without .json extension)

    Returns:
        Contents of the JSON file
    """
    if not filename.endswith(".json"):
        filename += ".json"

    data_dir = Path(__file__).parent.parent / "data"
    data_path = data_dir / filename

    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_dir_exists(directory_path: Union[str, Path]) -> Path:
    """
    Ensure that a directory exists, creating it if necessary.

    Args:
        directory_path: Path to the directory

    Returns:
        Path: Path to the directory
    """
    path = Path(directory_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_file_contents(file_path: Union[str, Path], encoding: str = "utf-8") -> str:
    """
    Read the contents of a file.

    Args:
        file_path: Path to the file
        encoding: File encoding (default: utf-8)

    Returns:
        str: Contents of the file
    """
    with open(file_path, "r", encoding=encoding) as f:
        return f.read()


def write_file_contents(file_path: Union[str, Path], contents: str, encoding: str = "utf-8") -> None:
    """
    Write contents to a file.

    Args:
        file_path: Path to the file
        contents: Contents to write
        encoding: File encoding (default: utf-8)
    """
    with open(file_path, "w", encoding=encoding) as f:
        f.write(contents)
