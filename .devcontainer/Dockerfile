FROM python:3.11-slim-bullseye

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    sudo \
    build-essential \
    wget \
    vim \
    ca-certificates \
    gnupg \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install newer SQLite3 from source (required for ChromaDB)
RUN wget https://www.sqlite.org/2024/sqlite-autoconf-3450100.tar.gz && \
    tar xvfz sqlite-autoconf-3450100.tar.gz && \
    cd sqlite-autoconf-3450100 && \
    ./configure --prefix=/usr/local && \
    make && \
    make install && \
    cd .. && \
    rm -rf sqlite-autoconf-3450100 sqlite-autoconf-3450100.tar.gz && \
    ldconfig

# Set SQLite library path
ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

# Install Node.js 20.x
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y nodejs && \
    npm install -g npm@latest && \
    rm -rf /var/lib/apt/lists/*

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
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Install Python development tools
RUN pip install black flake8 pylint pytest pytest-cov ipython ipdb

# Ensure workspace permissions
RUN mkdir -p /workspace && chown -R vscode:vscode /workspace

# Set vscode as the default user
USER vscode

# Configure shell aliases
RUN echo 'alias ll="ls -lah"' >> /home/vscode/.bashrc && \
    echo 'alias gs="git status"' >> /home/vscode/.bashrc && \
    echo 'export PS1="\[\e[36m\]🐳 devcontainer\[\e[m\] \[\e[33m\]\w\[\e[m\] \$ "' >> /home/vscode/.bashrc

# Set environment variables
ENV PATH="/home/vscode/.local/bin:${PATH}"
ENV PYTHONUNBUFFERED=1
ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH