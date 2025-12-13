# Deploying DCP Docs (Docker)

This repository currently ships documentation (OpenAPI, events, policy DSL, i18n bundles). You can serve it via nginx inside Docker.

## Prerequisites
- Docker and Docker Compose Plugin on the target host.
- Network access to fetch this repository or a tarball.

## Local build and run
```bash
docker build -t dcp-docs:latest .
docker run -d --name dcp-docs -p 8080:80 dcp-docs:latest
# Visit http://localhost:8080 to browse docs and openapi.yaml
```

Or with Compose:
```bash
docker compose up -d
```

## Remote deployment (example: root@72.61.52.70)
```bash
ssh root@72.61.52.70
# install docker/compose if needed
# apt-get update && apt-get install -y docker.io docker-compose-plugin
# fetch repo (requires your SSH key or HTTPS credentials)
git clone https://github.com/maxcardoso-git/DCP.git /opt/DCP
cd /opt/DCP
docker compose up -d
```

## Contents served
- `/README.md`
- `/docs` (includes OpenAPI `docs/api/openapi.yaml`, event contracts, data model, policy DSL)
- `/i18n` (locale bundles)
