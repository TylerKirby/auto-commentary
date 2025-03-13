"""
Tests for the core utils module.

This module tests the utility functions used across the application.
"""

import json
import os
import pickle
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from autocom.core.utils import (
    clear_cache,
    ensure_dir_exists,
    get_cache_dir,
    get_file_contents,
    load_cache,
    read_data_file,
    save_cache,
    write_file_contents,
)


@patch("autocom.core.utils.Path")
def test_get_cache_dir(mock_path):
    """Test getting the cache directory."""
    mock_path_instance = MagicMock()
    mock_path.return_value = mock_path_instance
    mock_path_instance.mkdir.return_value = None

    # Call the function
    result = get_cache_dir()

    # Check the result
    assert result == mock_path_instance
    mock_path.assert_called_once()
    mock_path_instance.mkdir.assert_called_once_with(parents=True, exist_ok=True)


@patch("autocom.core.utils.get_cache_dir")
@patch("autocom.core.utils.pickle.load")
@patch("builtins.open", new_callable=mock_open, read_data=b"test data")
def test_load_cache_exists(mock_file, mock_pickle_load, mock_get_cache_dir):
    """Test loading cache when the cache file exists."""
    # Setup
    mock_path = MagicMock()
    mock_path.exists.return_value = True
    mock_get_cache_dir.return_value = mock_path
    mock_path.__truediv__.return_value = mock_path
    mock_pickle_load.return_value = {"key": "value"}

    # Call the function
    result = load_cache("test_cache")

    # Check the result
    assert result == {"key": "value"}
    mock_get_cache_dir.assert_called_once()
    mock_path.__truediv__.assert_called_once_with("test_cache.pkl")
    mock_path.exists.assert_called_once()
    mock_file.assert_called_once_with(mock_path, "rb")
    mock_pickle_load.assert_called_once()


@patch("autocom.core.utils.get_cache_dir")
def test_load_cache_not_exists(mock_get_cache_dir):
    """Test loading cache when the cache file doesn't exist."""
    # Setup
    mock_path = MagicMock()
    mock_path.exists.return_value = False
    mock_get_cache_dir.return_value = mock_path
    mock_path.__truediv__.return_value = mock_path

    # Call the function
    result = load_cache("test_cache")

    # Check the result
    assert result == {}
    mock_get_cache_dir.assert_called_once()
    mock_path.__truediv__.assert_called_once_with("test_cache.pkl")
    mock_path.exists.assert_called_once()


@patch("autocom.core.utils.get_cache_dir")
@patch("builtins.open", new_callable=mock_open)
@patch("autocom.core.utils.pickle.dump")
def test_save_cache(mock_pickle_dump, mock_file, mock_get_cache_dir):
    """Test saving cache to disk."""
    # Setup
    mock_path = MagicMock()
    mock_get_cache_dir.return_value = mock_path
    mock_path.__truediv__.return_value = mock_path
    test_data = {"key": "value"}

    # Call the function
    save_cache("test_cache", test_data)

    # Check the function called correctly
    mock_get_cache_dir.assert_called_once()
    mock_path.__truediv__.assert_called_once_with("test_cache.pkl")
    mock_file.assert_called_once_with(mock_path, "wb")
    mock_pickle_dump.assert_called_once_with(test_data, mock_file())


@patch("autocom.core.utils.get_cache_dir")
@patch("autocom.core.utils.os.remove")
def test_clear_cache_specific(mock_remove, mock_get_cache_dir):
    """Test clearing a specific cache."""
    # Setup
    mock_path = MagicMock()
    mock_path.exists.return_value = True
    mock_get_cache_dir.return_value = mock_path
    mock_path.__truediv__.return_value = mock_path

    # Call the function
    clear_cache("test_cache")

    # Check the function called correctly
    mock_get_cache_dir.assert_called_once()
    mock_path.__truediv__.assert_called_once_with("test_cache.pkl")
    mock_path.exists.assert_called_once()
    mock_remove.assert_called_once_with(mock_path)


@patch("autocom.core.utils.get_cache_dir")
@patch("autocom.core.utils.os.remove")
def test_clear_cache_all(mock_remove, mock_get_cache_dir):
    """Test clearing all caches."""
    # Setup
    mock_path = MagicMock()
    mock_cache_files = [MagicMock(), MagicMock()]
    mock_path.glob.return_value = mock_cache_files
    mock_get_cache_dir.return_value = mock_path

    # Call the function
    clear_cache()

    # Check the function called correctly
    mock_get_cache_dir.assert_called_once()
    mock_path.glob.assert_called_once_with("*.pkl")
    assert mock_remove.call_count == 2


def test_ensure_dir_exists():
    """Test ensuring a directory exists."""
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = os.path.join(temp_dir, "test_dir")

        # Ensure the directory exists
        result = ensure_dir_exists(test_dir)

        # Check the directory was created
        assert os.path.isdir(test_dir)
        assert isinstance(result, Path)

        # Call again to test the existing directory case
        result2 = ensure_dir_exists(test_dir)
        assert result2 == result


def test_get_file_contents():
    """Test reading file contents."""
    # Create a temporary file with content
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_file:
        temp_file.write("Test content")
        temp_file_path = temp_file.name

    try:
        # Read the file
        content = get_file_contents(temp_file_path)

        # Check the content
        assert content == "Test content"
    finally:
        # Clean up
        os.unlink(temp_file_path)


def test_write_file_contents():
    """Test writing file contents."""
    # Create a temporary file path
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file_path = temp_file.name

    try:
        # Write content to the file
        write_file_contents(temp_file_path, "New content")

        # Read the file to verify
        with open(temp_file_path, "r") as f:
            content = f.read()

        # Check the content
        assert content == "New content"
    finally:
        # Clean up
        os.unlink(temp_file_path)
