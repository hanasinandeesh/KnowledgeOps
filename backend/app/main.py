from fastapi import FastAPI

from app.core.exceptions import setup_exception_handlers
from app.modules.auth.router import router as auth_router
from app.modules.documents.router import router as documents_router

app = FastAPI(
    title="KnowledgeOps API",
    version="0.1.0",
    description="KnowledgeOps enterprise knowledge discovery platform backend",
)

# Register uniform error envelope handlers
setup_exception_handlers(app)

# Register API routers under /api/v1 prefix
app.include_router(auth_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health-check endpoint confirming the API process is running."""
    return {"status": "ok"}
