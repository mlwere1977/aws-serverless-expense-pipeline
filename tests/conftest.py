import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "ingest"))
os.environ.setdefault("STUDENT_NAME", "Test Student")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")


def load_module(name, relative_path):
    """Load a Lambda's app.py under a unique name (all three are called app.py)."""
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
