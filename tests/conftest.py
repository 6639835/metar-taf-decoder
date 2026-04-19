"""Pytest configuration and shared fixtures."""

import sys
import os

# Ensure the project root is on sys.path so imports work regardless of how
# pytest is invoked (installed or not).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
