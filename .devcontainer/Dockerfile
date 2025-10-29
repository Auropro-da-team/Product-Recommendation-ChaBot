FROM python:3.11-slim-bullseye

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Create vscode user with sudo privileges
RUN useradd -m -s /bin/bash vscode && \
    echo "vscode ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
    mkdir -p /home/vscode/.vscode-server && \
    mkdir -p /home/vscode/.vscode-server-insiders && \
    chown -R vscode:vscode /home/vscode

# Set working directory
WORKDIR /workspace

# Copy requirements from backend directory
COPY backend/requirements.txt /tmp/requirements.txt

# Install Python dependencies as root
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Ensure workspace permissions
RUN mkdir -p /workspace && chown -R vscode:vscode /workspace

# Set vscode as the default user
USER vscode

# Set environment variables
ENV PATH="/home/vscode/.local/bin:${PATH}"
ENV PYTHONUNBUFFERED=1