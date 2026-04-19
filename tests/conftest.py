"""Pytest configuration and shared fixtures."""

import os
import sys

# Ensure the src layout is importable when pytest is run without an editable
# install.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_ROOT = os.path.join(PROJECT_ROOT, "src")

if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)
