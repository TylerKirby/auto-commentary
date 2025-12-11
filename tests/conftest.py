"""
Pytest configuration for test discovery and import path setup.

Ensures the project root is on sys.path so that imports like
`from src.agents.latin.parsing import LatinParsingTools` work
regardless of how pytest is invoked (e.g., `pytest` or `pytest tests/`).
"""

import os
import sys
from typing import List


def _ensure_project_root_on_sys_path(sys_path: List[str]) -> None:
    """
    Add the project root directory to sys.path if it is not already present.

    :param sys_path: The current Python sys.path list.
    :return: None
    """
    tests_dir = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(tests_dir, os.pardir))
    if project_root not in sys_path:
        sys_path.insert(0, project_root)


_ensure_project_root_on_sys_path(sys.path)
