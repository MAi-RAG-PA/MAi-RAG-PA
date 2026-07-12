
# 1. DOCKER.md (Optional Containerization Guide)

## Docker Deployment (Optional)

> **Note:** Docker is **not required** for MAi-RAG-PA. The recommended installation method uses standalone binaries via `./install.sh`. This guide is provided for users who prefer containerized deployments.

## Prerequisites

- Docker Engine 24.0+
- Docker Compose v2.20+
- NVIDIA GPU + nvidia-container-toolkit (optional, for GPU acceleration)

## Quick Start

### 1. Clone and Configure

```bash
    git clone https://github.com/MAi-RAG-PA/MAi-RAG-PA.git
    cd MAi-RAG-PA
    cp .env.example .env
```

**Edit .env to set your preferred models and API keys.**

# 2. Build and Run

```bash
docker compose up -d --build
```

**The Web UI will be available at http://localhost:8000.**

3. Pull Models
Models must be pulled into the Ollama volume after first start:


    docker compose exec ollama ollama pull qwen2.5-coder:14b


## Docker Compose Configuration

**Create docker-compose.yml in the project root:**

**yaml**

    services:
      mai-rag:
        build: .
        ports:
          - "8000:8000"
        volumes:
          - ./workspace:/app/workspace
          - mai_rag_data:/app/memory
        environment:
          - OLLAMA_URL=http://ollama:11434
          - QDRANT_URL=http://qdrant:6333
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
          - "11434:11434"
        healthcheck:
          test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
          interval: 10s
          timeout: 5s
          retries: 5
        restart: unless-stopped
        # Uncomment for NVIDIA GPU support:
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
          - "6333:6333"
        restart: unless-stopped

    volumes:
      ollama_data:
      qdrant_data:
      mai_rag_data:


## Dockerfile

**Create Dockerfile in the project root:**

**dockerfile**

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

    # Frontend build stage
    FROM node:20-alpine AS frontend
    WORKDIR /build
    COPY frontend/package*.json ./
    RUN npm ci
    COPY frontend/ .
    RUN npm run build

    # Final image
    FROM backend
    COPY --from=frontend /build/dist ./frontend/dist

    EXPOSE 8000

    CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


## GPU Acceleration

**For NVIDIA GPU passthrough, install the NVIDIA Container Toolkit
, then uncomment the deploy section in the Ollama service above.
Verify GPU access:**

    docker compose exec ollama nvidia-smi


## Data Persistence

**All persistent data lives in named Docker volumes:**

|Volume |Contents |
|ollama_data |Downloaded AI models |
|qdrant_data |Vector embeddings and collections |
|mai_rag_data |SQLite database, settings, chat history |

**To backup all data:**

    docker compose down
    docker run --rm -v mai_rag_data:/data -v $(pwd):/backup alpine tar czf /backup/mai-rag-backup.tar.gz /data

## Troubleshooting

|Issue |Solution |
|Ollama health check fails |Wait 30s after first start; model download takes time |
|Qdrant connection refused |Ensure port 6333 is not occupied on host |
|GPU not detected |Verify nvidia-smi works on host and toolkit is installed |
|Permission errors on volumes |Run docker compose down && docker volume rm mai_rag_data and rebuild|

## Differences from Standalone Installation

|Aspect |Standalone (./install.sh) |Docker |
|Setup complexity |Single command |Requires Docker knowledge |
|Resource overhead |Minimal |~200MB base + Docker daemon|
|GPU setup |Automatic detection |Manual toolkit configuration |
|Updates |git pull && ./start.sh |Rebuild image |
|Uninstall |rm -rf ~/MAi-RAG-PA |Remove containers + volumes |
|Recommended for |Most users |Server/enterprise deployments|
