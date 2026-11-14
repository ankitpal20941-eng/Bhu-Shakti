"""BHUSHAKTI AI backend package."""

import sys
from pathlib import Path

# Ensure backend root is on sys.path so 'import app...' succeeds from any execution cwd
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

__version__ = "0.9.0"
