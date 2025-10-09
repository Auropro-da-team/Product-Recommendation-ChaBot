
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def home():
    """Health check endpoint."""
    return {"message": "Chatbot API is up!!"}

@router.get("/health")
def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "service": "Essilor Chatbot API"
    }

