import sys
sys.path.append(".")
import importlib.util
from pathlib import Path
import json

spec = importlib.util.spec_from_file_location("relative_capture", "tools/golden/relative-capture.py")
rc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc)

manifest = {
  "outcome": "dependency-missing",
  "missingDependency": {"kind": "unknown"},
}

try:
    rc.materialize_g6(".", manifest, ".")
except Exception as e:
    print(e)
