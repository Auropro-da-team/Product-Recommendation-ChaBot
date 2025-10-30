#!/bin/bash

# This script runs after the container is created

echo "🚀 Running post-create setup..."

# Verify Python installation
python --version
pip --version

# Verify Node.js installation
node --version
npm --version

# Install frontend dependencies if package.json exists
if [ -f "frontend/package.json" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
else
    echo "⚠️  frontend/package.json not found, skipping npm install"
fi

# Set proper permissions
sudo chown -R vscode:vscode /home/vscode
sudo chmod -R 755 /home/vscode

echo "✅ Post-create setup complete!"
echo "👉 To start the backend: cd backend && uvicorn main:app --reload --host 0.0.0.0"
echo "👉 To start the frontend: cd frontend && npm run dev"