from fastapi import APIRouter
import os

router = APIRouter(prefix="/mcp", tags=["diagnostic"])

@router.get("/check")
def mcp_check():
    """
    Diagnostic endpoint for internal/dev-only environments.
    Strictly forbidden in production per TRD section 8.4.
    """
    return {
        "status": "healthy",
        "diagnostic_active": True,
        "environment": os.getenv("ENVIRONMENT", "development")
    }
