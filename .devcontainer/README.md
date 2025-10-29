# Development Container Setup

This project uses VS Code Dev Containers to provide a consistent development environment.

## Prerequisites

1. **Docker Desktop** installed and running
   - [Download for Mac](https://www.docker.com/products/docker-desktop)
   - [Download for Windows](https://www.docker.com/products/docker-desktop)
   - [Download for Linux](https://docs.docker.com/desktop/install/linux-install/)

2. **VS Code** with the Dev Containers extension
   - Install VS Code: https://code.visualstudio.com/
   - Install extension: `ms-vscode-remote.remote-containers`

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd <your-repo-name>
   ```

2. **Open in VS Code**
   ```bash
   code .
   ```

3. **Reopen in Container**
   - VS Code will detect the `.devcontainer` folder
   - Click "Reopen in Container" when prompted
   - OR: Press `F1` → "Dev Containers: Reopen in Container"

4. **Wait for setup** (first time only)
   - Docker will build the container (~5-10 minutes)
   - Extensions will be installed automatically
   - Dependencies will be installed via `post-create.sh`

5. **Configure environment**
   - Update `backend/.env` with your API keys:
     ```
     OPENAI_API_KEY=your_key_here
     HF_TOKEN=your_token_here
     EMAIL_HOST_PASSWORD=your_password_here
     ```

6. **Start the services**
   
   Terminal 1 (Backend):
   ```bash
   cd backend
   uvicorn main:app --reload --host 0.0.0.0
   ```
   
   Terminal 2 (Frontend):
   ```bash
   cd frontend
   npm run dev
   ```

## What's Included

### Installed Tools
- Python 3.12
- Node.js 20.x

### Services
- **app**: Main development container
- **chromadb**: ChromaDB vector database (localhost:8001)

### Port Forwarding
- **8000**: FastAPI backend
- **5173**: Vite frontend
- **8001**: ChromaDB

## Troubleshooting

### Container won't start
1. Ensure Docker Desktop is running
2. Check Docker has enough resources (4GB+ RAM recommended)
3. Try rebuilding: `F1` → "Dev Containers: Rebuild Container"

### Can't access Google Cloud
The container mounts your local `~/.config/gcloud` directory. Ensure:
1. You've run `gcloud auth application-default login` on your host machine
2. The credentials file exists at `~/.config/gcloud/application_default_credentials.json`

### Port already in use
If port 8000 or 5173 is already in use:
1. Stop the conflicting service on your host
2. OR: Change the port mapping in `.devcontainer/docker-compose.yml`

### Python packages not found
Rebuild the container:
```bash
# In VS Code
F1 → "Dev Containers: Rebuild Container"
```

### Node modules missing
```bash
cd frontend
npm install
```

## Customization

### Add Python packages
1. Add to `backend/requirements.txt`
2. Rebuild container OR run `pip install <package>` in container

### Add Node packages
1. Add to `frontend/package.json`
2. Run `npm install` in container

### Add VS Code extensions
Edit `.devcontainer/devcontainer.json`:
```json
"extensions": [
  "your.extension.id"
]
```

### Modify container settings
Edit `.devcontainer/docker-compose.yml` for:
- Environment variables
- Port mappings
- Volume mounts
- Additional services

## Best Practices

1. **Commit `.devcontainer/` to git** - Share setup with your team
2. **Never commit `.env` files** - Add to `.gitignore`
3. **Use the integrated terminal** - It's already inside the container
4. **Rebuild after major changes** - Especially to dependencies
5. **Mount Google Cloud credentials** - Don't copy them into the container

## Additional Resources

- [VS Code Dev Containers Docs](https://code.visualstudio.com/docs/devcontainers/containers)
- [Dev Container Features](https://containers.dev/features)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)