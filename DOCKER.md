# Installing MAi-RAG-P.A. with Docker

> **Docker is optional.** The recommended installation for most users is the standalone installer (`./install.sh`). This guide is for people who decide to run MAi-RAG-P.A. in a container — typical on servers and in locked-down environments. The privacy posture is unchanged either way: models, database, and documents never leave your own machine.

## Prerequisites

- Docker Engine 24.0+
- Docker Compose v2.20+
- Optional, for GPU acceleration: an NVIDIA GPU and the nvidia-container-toolkit (see GPU Acceleration below)

## Installation

The three files this guide asks you to create (`Dockerfile`, `docker-compose.yml`, `.dockerignore`) do not ship with the repository — each step shows exactly what to put in them.

### 1. Clone the Repository

```bash
git clone https://github.com/MAi-RAG-PA/MAi-RAG-PA.git
cd MAi-RAG-PA
```

No `.env` file is needed for the containerized setup: the containers get their configuration directly from the `environment` block in `docker-compose.yml` (step 3). Models and API keys are managed in the WebUI after startup.

### 2. Create the Dockerfile

Create `Dockerfile` in the project root:

```dockerfile
FROM python:3.12-slim AS backend

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git && \
    rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Frontend build stage (Node is not needed at runtime)
FROM node:20-alpine AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Final image
FROM backend
COPY --from=frontend /build/dist ./frontend/dist
COPY --from=frontend /build/public ./frontend/public

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

The multi-stage build compiles the React frontend with Node and then drops the Node toolchain from the final image. The `public` copy matters: notification sounds and fonts are served from `frontend/public/` at runtime, not from the built `dist/`. Schema migrations and API-key generation run automatically on first start — no extra entrypoint steps are required.

### 3. Create docker-compose.yml

Create `docker-compose.yml` in the project root:

```yaml
services:
  mai-rag:
    build: .
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - ./workspace:/app/workspace
      - mai_rag_data:/app/memory
    environment:
      - OLLAMA_URL=http://ollama:11434
      - QDRANT_URL=http://qdrant:6333
      - MAI_ALLOW_REMOTE_AUTOKEY=1
      - HF_HUB_OFFLINE=1
      - TRANSFORMERS_OFFLINE=1
    depends_on:
      ollama:
        condition: service_healthy
      qdrant:
        condition: service_started
    restart: unless-stopped

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "127.0.0.1:11434:11434"
    healthcheck:
      test: ["CMD", "ollama", "list"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    # For NVIDIA GPU support, uncomment the deploy block:
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: all
    #           capabilities: [gpu]

  qdrant:
    image: qdrant/qdrant:v1.17.0
    volumes:
      - qdrant_data:/qdrant/storage
    ports:
      - "127.0.0.1:6333:6333"
    restart: unless-stopped

volumes:
  ollama_data:
  qdrant_data:
  mai_rag_data:
```

Why each choice:

- `MAI_ALLOW_REMOTE_AUTOKEY=1` is required inside containers. On first load the WebUI fetches the API key automatically; that request reaches the server from the Docker bridge network instead of loopback, where it would otherwise be refused with 403 and the UI could never authenticate.
- Every port binds to `127.0.0.1`, so nothing is reachable from the local network unless you deliberately change it (see "Access from another machine" in step 6).
- `OLLAMA_URL` and `QDRANT_URL` use Docker's service names, which resolve to the sibling containers on the compose network.

### 4. Create .dockerignore

Create `.dockerignore` in the project root so host-only material — virtualenvs, node modules, your documents — stays out of the build context:

```
.git
.env
**/venv
**/node_modules
**/__pycache__
*.pyc
*.bak-*
logs/
memory/
storage/
qdrant/
models/
dev-sandbox/
workspace/
docs/
gh-pages/
input/
```

### 5. Build and Start

```bash
docker compose up -d --build
```

The backend serves the built WebUI itself, so no Node runtime is needed on the host.

### 6. Open the WebUI

Browse to http://localhost:8000. The frontend retrieves the API key automatically on first load — no manual key handling for local use.

**Access from another machine (optional — changes the privacy posture):**

1. Publish the port beyond loopback: change `127.0.0.1:8000:8000` to `8000:8000`.
2. Allow your server's origin, for example `- CORS_ORIGINS=http://192.168.1.10:8000` in the `environment` block.
3. Keep `MAI_ALLOW_REMOTE_AUTOKEY=1` (already set above).

With these settings any allowed device can read the API key and drive the assistant, so keep the loopback binding unless you truly need network access.

### 7. Pull the Models

Models live in the `ollama_data` volume and must be pulled after the first start. Beyond a primary chat model that fits your RAM (example for 16GB; see `MAi-OLLAMA-MODELS.md` for guidance), two support models are required for core features:

```bash
# Primary chat model (pick one that fits your hardware):
docker compose exec ollama ollama pull qwen2.5-coder:14b

# Protected system model - required for STM quick-entry and Self-Healing:
docker compose exec ollama ollama pull codeqwen:7b

# Embedding model - required for RAG document ingestion:
docker compose exec ollama ollama pull nomic-embed-text:latest
```

## GPU Acceleration (optional)

1. Install the NVIDIA Container Toolkit on the host (Debian/Ubuntu shown; other distributions use the toolkit's package repositories):

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

2. Uncomment the `deploy:` block in the `ollama` service of `docker-compose.yml`.
3. Verify after a model is loaded:

```bash
docker compose exec ollama ollama ps
```

Output showing `100% GPU` confirms the model runs on the GPU.

## Data Persistence, Backup and Restore

All persistent data lives in named volumes:

| Volume | Contents |
|---|---|
| `ollama_data` | Downloaded AI models |
| `qdrant_data` | Vector embeddings and collections |
| `mai_rag_data` | SQLite database: settings, API key, chat history, memory |

`./workspace` is a host bind mount, so files the assistant creates appear directly in the project folder on the host.

**Back up** (taken with the stack stopped for a consistent snapshot):

```bash
docker compose down
docker run --rm -v mai_rag_data:/data -v "$(pwd)":/backup alpine tar czf /backup/mai-rag-backup.tar.gz /data
docker compose up -d
```

**Restore** (replaces the current database with the backup contents):

```bash
docker compose down
docker run --rm -v mai_rag_data:/data -v "$(pwd)":/backup alpine tar xzf /backup/mai-rag-backup.tar.gz -C /
docker compose up -d
```

## Troubleshooting

| Issue | Solution |
|---|---|
| WebUI loads but API calls return 403 (key denied) | `MAI_ALLOW_REMOTE_AUTOKEY=1` is missing from the compose environment, or you are visiting from a non-local host (add that origin to `CORS_ORIGINS`) |
| Ollama health check never passes | On first start the image is still being pulled; inspect with `docker compose logs ollama` |
| Qdrant connection refused | Port 6333 is already in use on the host — free it or change the published port |
| RAG ingestion fails with an embeddings error | `nomic-embed-text:latest` has not been pulled yet (step 7) |
| GPU not detected | Toolkit installed, `nvidia-ctk runtime configure --runtime=docker` run, Docker restarted, `deploy:` block uncommented; confirm with `ollama ps` |
| Permission errors on volumes | Back up first (commands above): removing a volume deletes its data. Then `docker compose down && docker volume rm mai_rag_data` and `docker compose up -d` to recreate it empty |
| Code outdated after `git pull` | `docker compose up -d --build` |

## Docker vs Standalone Installation

| Aspect | Standalone (`./install.sh`) | Docker |
|---|---|---|
| Setup complexity | Single command | Three files plus Docker knowledge |
| Resource overhead | Minimal | ~200MB base plus Docker daemon |
| GPU setup | Automatic detection | Manual toolkit configuration |
| Updates | `git pull && ./start.sh` | `git pull && docker compose up -d --build` |
| Uninstall | `rm -rf ~/MAi-RAG-PA` | `docker compose down -v` (removes containers **and data**) |
| Recommended for | Most users | Servers and locked-down environments |
