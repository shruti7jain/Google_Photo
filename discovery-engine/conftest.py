"""
conftest.py
────────────────────────────────────────────────────────────────
Root-level pytest configuration.

Adds the project root to sys.path so that `from models.schema import …`
works in tests without requiring an editable install.
"""

import sys
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).parent))
