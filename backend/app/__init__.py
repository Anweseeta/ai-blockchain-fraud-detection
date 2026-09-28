"""Backend package init: make the project's `src` package importable.

The validated preprocessor.joblib was pickled against src.preprocessing.pipeline,
so the project root must be on sys.path before joblib.load runs.
"""
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
