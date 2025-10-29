#!/bin/bash

echo "🚀 Starting Product Recommendation Chatbot Backend..."

# Wait for ChromaDB to be ready
echo "⏳ Waiting for ChromaDB..."
sleep 5

# Start the FastAPI application
cd /workspace/backend
uvicorn main:app --host 0.0.0.0 --port 8001 --reload