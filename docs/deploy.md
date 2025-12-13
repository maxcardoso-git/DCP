# Deploying DCP (API + UI + Docs) with Docker Compose

This repo now ships:
- FastAPI backend (`dcp-api`) with Postgres
- React frontend (`dcp-frontend`)
- Docs + specs served via nginx (`dcp-docs`)
Use Docker Compose to run all, or run individual services as needed.

## Prerequisites
- Docker and Docker Compose Plugin on the target host.
- Network access to fetch this repository or a tarball.

## Local build and run (full stack)
```bash
docker compose up -d  # builds backend, frontend, docs, and starts Postgres
# override ports if busy:
# HOST_API_PORT=8110 HOST_FRONTEND_PORT=8100 PORT=8080 docker compose up -d
```

## Service endpoints (defaults)
- API: http://localhost:8110/api/v2/dcp (OpenAPI at /openapi.json)
- Frontend: http://localhost:8100 (Vite preview)
- Docs: http://localhost:8080 (set PORT to override; production server uses 8090)
- Postgres: exposed on host port 55435 by default (user dcp / pass dcp / db dcp)

## Run docs only
```bash
PORT=8080 docker compose up -d dcp-docs
```

## Remote deployment (example: root@72.61.52.70)
```bash
ssh root@72.61.52.70
git clone https://github.com/maxcardoso-git/DCP.git /opt/DCP
cd /opt/DCP
HOST_API_PORT=8110 HOST_FRONTEND_PORT=8100 PORT=8090 docker compose up -d
```

## Contents served by docs container
- `/README.md`
- `/docs` (includes OpenAPI `docs/api/openapi.yaml`, event contracts, data model, policy DSL)
- `/i18n` (locale bundles)
