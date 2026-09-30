import sys
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import json
from typing import Dict, Any, List, Tuple

from schemas.validators import validate_schema_dict


def validate_file(path: Path) -> List[Tuple[Path, bool, str]]:
    results = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return [(path, False, f"JSON parse error: {e}")]

    items = data if isinstance(data, list) else [data]
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            results.append((path, False, f"Item [{idx}] is not a JSON object"))
            continue
        valid, result = validate_schema_dict(item)
        msg = "OK" if valid else (f"Item [{idx}]: {result}" if len(items) > 1 else str(result))
        results.append((path, valid, msg))
    return results


def validate_dir(directory: Path) -> bool:
    all_passed = True
    files = list(directory.rglob("*.json"))
    if not files:
        print(f"[WARN] No .json files found in {directory}")
        return True

    print(f"\nScanning {len(files)} file(s) in {directory}...")
    for f in sorted(files):
        results = validate_file(f)
        for path, valid, msg in results:
            if valid:
                print(f"  [PASS] {path.relative_to(directory)}")
            else:
                print(f"  [FAIL] {path.relative_to(directory)} -> {msg}")
                all_passed = False

    print("\nResult: " + ("ALL PASSED" if all_passed else "SOME FAILED"))
    return all_passed


if __name__ == "__main__":
    target_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/extracted")
    success = validate_dir(target_dir)
    sys.exit(0 if success else 1)
