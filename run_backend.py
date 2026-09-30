import uvicorn
import sys
from pathlib import Path

# Ensure root directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

if __name__ == "__main__":
    print("\n" + "=" * 76)
    print(" 🏭 CHANDRA ASRI PACIFIC — MANUFACTURING KNOWLEDGE HUB BACKEND API")
    print(" 🚀 Starting FastAPI server on http://127.0.0.1:8000")
    print(" 📖 Interactive Swagger API Docs: http://127.0.0.1:8000/docs")
    print("=" * 76 + "\n")
    uvicorn.run("src.api.server:app", host="127.0.0.1", port=8000, reload=False)
