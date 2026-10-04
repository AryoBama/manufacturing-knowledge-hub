import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure repository root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import uvicorn

if __name__ == "__main__":
    print("\n" + "=" * 76)
    print(" CHANDRA ASRI PACIFIC - MANUFACTURING KNOWLEDGE HUB BACKEND API")
    print(" Starting FastAPI server on http://127.0.0.1:8000")
    print(" Interactive Swagger API Docs: http://127.0.0.1:8000/docs")
    print("=" * 76 + "\n")
    uvicorn.run("src.api.server:app", host="127.0.0.1", port=8000, reload=False)
