# Use Ubuntu-based Python image for better compatibility
FROM mcr.microsoft.com/devcontainers/python:1-3.11-bullseye

# Install Node.js 20.x
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@latest

# Install additional system dependencies
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
        build-essential \
        curl \
        git \
        wget \
        vim \
        postgresql-client \
        libpq-dev \
        libjpeg-dev \
        libpng-dev \
        libfreetype6-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python tools
RUN pip install --upgrade pip setuptools wheel

# Install common Python development tools
RUN pip install \
    black \
    flake8 \
    pylint \
    pytest \
    pytest-cov \
    ipython \
    ipdb

# Set working directory
WORKDIR /workspace

# Copy requirements first for better caching
COPY backend/requirements.txt /tmp/backend-requirements.txt
RUN pip install -r /tmp/backend-requirements.txt

# Install frontend dependencies (if package.json exists)
COPY frontend/package*.json /tmp/frontend/
RUN cd /tmp/frontend && npm install

# Create non-root user (vscode user is already created by base image)
# Configure shell
RUN echo 'alias ll="ls -lah"' >> /home/vscode/.bashrc \
    && echo 'alias gs="git status"' >> /home/vscode/.bashrc \
    && echo 'export PS1="\[\e[36m\]🐳 devcontainer\[\e[m\] \[\e[33m\]\w\[\e[m\] \$ "' >> /home/vscode/.bashrc

# Set user
USER vscode