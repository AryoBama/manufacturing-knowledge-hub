from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from src.api.routes import router

app = FastAPI(
    title="Chandra Asri Manufacturing Knowledge Hub API",
    description=(
        "Backend REST API for CALIBER 2026 Case 1: AI-Powered Industrial Knowledge Integration, "
        "Multi-Signal Semantic Retrieval, Document Conflict Resolution, and Active Failure Memory."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for decoupled frontend clients (Streamlit, React, Vue, mobile)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount main API endpoints
app.include_router(router)


@app.get("/", include_in_schema=False)
def root_redirect():
    """Redirects root URL directly to interactive Swagger API documentation."""
    return RedirectResponse(url="/docs")
