# Docker Setup Overview

This document explains how the AnaGuide RAG application is packaged and run with Docker.

## Executive Summary

The application runs as **three Docker services**:

1. **Qdrant**: the vector database
2. **Backend**: the FastAPI Python application
3. **Frontend**: the React application served through nginx

There are **two custom Dockerfiles** in this repository:

1. `src/be/Dockerfile` for the backend
2. `src/fe/Dockerfile` for the frontend

The third service, Qdrant, does **not** use a local Dockerfile. It uses the official published image `qdrant/qdrant:v1.13.2` directly from Docker Hub.

The file `docker-compose.yml` ties all three services together and defines how they communicate.

## Architecture

```text
Browser
  |
  v
Frontend container (nginx, port 80)
  |
  +--> serves the React static files
  |
  +--> proxies API requests to Backend
                         |
                         v
                Backend container (FastAPI, port 8000)
                         |
                         +--> talks to OpenAI
                         |
                         +--> talks to Qdrant
                                      |
                                      v
                           Qdrant container (ports 6333/6334)
```

## Why There Are Three Services

The application has three distinct responsibilities:

- **Frontend**: user interface
- **Backend**: application logic, ingestion, chat orchestration, API endpoints
- **Qdrant**: vector storage and similarity search

Separating them provides cleaner deployment boundaries and mirrors how the system would run in a real environment such as OpenShift or Kubernetes.

## File-by-File Explanation

### 1. `src/be/Dockerfile`

This file builds the **backend image**.

What it does:

- Starts from `python:3.13-slim`
- Sets `/app` as the working directory
- Copies `src/be/pyproject.toml` first so Python dependencies can be installed with Docker layer caching
- Runs `pip install ./src/be`
- Copies the backend application source into the image
- Creates `/app/documents` and `/app/data`
- Switches to `/app/src/be`
- Starts the API with `uvicorn app.main:app --host 0.0.0.0 --port 8000`

Important design detail:

The backend code calculates `PROJECT_ROOT` based on its file path. The Dockerfile preserves the repository path shape inside the container so that logic still works.

### 2. `src/fe/Dockerfile`

This file builds the **frontend image**.

It uses a **multi-stage build**:

- **Build stage**:
  - Starts from `node:22-alpine`
  - Installs frontend dependencies with `npm ci`
  - Copies the frontend source
  - Runs `npm run build` to produce the production bundle in `dist/`
- **Runtime stage**:
  - Starts from `nginx:alpine`
  - Copies the built static files into `/usr/share/nginx/html`
  - Copies a custom nginx configuration into `/etc/nginx/conf.d/default.conf`

Why this matters:

- The final runtime image is much smaller than a Node-based runtime image
- The container only contains production assets and nginx
- It is better aligned with production deployment practices

### 3. `src/fe/nginx.conf`

This is not a Dockerfile, but it is part of the frontend container behavior.

It does three important things:

1. Serves the built React app
2. Proxies API traffic such as `/chat`, `/ingest`, `/health`, and `/documents/` to the backend container
3. Supports SPA routing with `try_files ... /index.html`

This is why a user can load the frontend on port 80 and still have backend API requests work through the same origin.

### 4. `docker-compose.yml`

This file defines how all three services run together.

It defines:

- which image to use or build
- which ports to expose
- which environment variables to inject
- which directories to mount as volumes
- service startup dependencies
- service health checks

## How Docker Compose Runs the Stack

When `docker compose up --build` is run, Docker Compose does the following:

1. Builds the backend image from `src/be/Dockerfile`
2. Builds the frontend image from `src/fe/Dockerfile`
3. Pulls the official Qdrant image if it is not already local
4. Starts the `qdrant` service first
5. Waits for Qdrant's health check to pass
6. Starts the backend service
7. Starts the frontend service

At runtime:

- The browser talks to the frontend on port `80`
- nginx inside the frontend container proxies API requests to `http://backend:8000`
- The backend talks to Qdrant at `http://qdrant:6333`

The service names `frontend`, `backend`, and `qdrant` work as hostnames because Docker Compose creates an internal network for the stack automatically.

## Service Details

### Qdrant Service

Defined directly in `docker-compose.yml` using:

`qdrant/qdrant:v1.13.2`

Key points:

- Exposes ports `6333` and `6334`
- Mounts `./data/qdrant` to persist vector data
- Uses a TCP-based health check
- Runs independently of the backend and frontend build process

### Backend Service

Built from `src/be/Dockerfile`.

Key points:

- Exposes port `8000`
- Reads configuration from `.env`
- Overrides `QDRANT_URL` to `http://qdrant:6333`
- Mounts `./documents` into `/app/documents`
- Mounts `./data` into `/app/data`
- Waits for Qdrant to become healthy before starting

### Frontend Service

Built from `src/fe/Dockerfile`.

Key points:

- Exposes port `80`
- Passes `VITE_API_URL` as an empty string so the application uses same-origin requests
- Depends on the backend service
- Serves the static React application through nginx

## Why the Frontend Uses nginx

The frontend container does not run the Vite development server in production.

Instead, it:

- builds the site once during image build
- serves the compiled assets with nginx
- proxies API traffic to the backend

This is more appropriate for production because it is lighter, more predictable, and avoids running a development server in a deployment environment.

## Data Persistence

Two parts of the setup write data that should survive container restarts:

- `./data/qdrant` for Qdrant storage
- `./documents` and `./data` for backend-managed files and application data

These are mounted as Docker volumes from the host machine into the containers.

That means:

- rebuilding the images does not delete this data
- restarting the containers does not delete this data
- deleting the containers does not delete the host directories

## Why Only Two Dockerfiles Exist

The client may notice that there are three services but only two Dockerfiles.

That is intentional:

- The **backend** and **frontend** are custom application components, so they need custom Dockerfiles
- **Qdrant** is a standard third-party product, so it is simpler and more reliable to use the vendor's published image directly

This is a common Docker pattern.

## Commands

Build and start the full stack:

```bash
docker compose up --build
```

Start the stack without rebuilding:

```bash
docker compose up
```

Stop the stack:

```bash
docker compose down
```

Check running services:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs
```

## Expected Runtime Endpoints

- Frontend: `http://localhost`
- Backend health: `http://localhost:8000/health`
- Backend via frontend proxy: `http://localhost/health`
- Qdrant: `http://localhost:6333`

## Summary

This Docker setup is designed to package the application into three cooperating services:

- **Qdrant** for vector storage
- **Backend** for RAG and API logic
- **Frontend** for the user interface

The repository contains two custom Dockerfiles because only the backend and frontend are custom-built. Docker Compose orchestrates all three services together, provides internal networking, manages startup order, and mounts persistent data directories from the host.
