import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import chat, health
from app.dependencies import get_dependencies

# Set logging level to INFO
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Product Recommendation ChatBot",
    description="A FastAPI backend for product recommendations and order management.",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Routers
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(health.router, prefix="/api", tags=["Health"])

@app.on_event("startup")
def startup_event():
    # Initialize dependencies at startup so logs are visible
    get_dependencies()

@app.get("/")
def root():
    return {"message": "Welcome to the Product Recommendation ChatBot API!"}