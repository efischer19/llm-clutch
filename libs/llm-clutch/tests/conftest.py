"""Pytest configuration for llm-clutch tests.

This module imports shared fixtures from the testing/ directory,
making them available to all tests in this package.
"""

import sys
from pathlib import Path

# Add the project root to the path so we can import from testing/
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import and re-export fixtures from the shared testing module
pytest_plugins = ["testing.conftest"]
