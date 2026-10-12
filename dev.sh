#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROXY_DIR="${LITELLM_PROXY_DIR:-$HOME/litellm-proxy}"
COMPOSE_FILE="$PROXY_DIR/docker-compose.quickstart.yml"
ENV_FILE="$PROXY_DIR/.env"

# Validate the LiteLLM deployment files.
if [[ ! -f "$COMPOSE_FILE" || ! -f "$ENV_FILE" ]]; then
    echo "Error: LiteLLM Compose file or .env not found."
    exit 1
fi

# Docker must already be installed and running.
if ! docker info >/dev/null 2>&1; then
    echo "Error: Start Docker Desktop or the Docker daemon first."
    exit 1
fi

echo "Starting LiteLLM Proxy and PostgreSQL..."

docker compose \
    --env-file "$ENV_FILE" \
    -f "$COMPOSE_FILE" \
    up -d

# Wait up to 60 seconds for LiteLLM readiness.
ready=false

for attempt in {1..30}; do
    if curl -fsS \
        http://127.0.0.1:4000/health/readiness \
        >/dev/null; then
        ready=true
        break
    fi

    sleep 2
done
echo "Waiting for LiteLLM readiness..."

ready=false

for attempt in {1..30}; do
    if curl -fsS --max-time 2 \
        http://127.0.0.1:4000/health/readiness \
        >/dev/null 2>&1; then
        ready=true
        break
    fi

    sleep 2
done

if [[ "$ready" != true ]]; then
    echo "ERROR: LiteLLM did not become ready."
    echo "FastAPI will not be started."

    docker compose \
        --env-file "$ENV_FILE" \
        -f "$COMPOSE_FILE" \
        ps -a

    docker compose \
        --env-file "$ENV_FILE" \
        -f "$COMPOSE_FILE" \
        logs --tail=100 litellm

    exit 1
fi

echo "LiteLLM is ready."
echo "Dashboard: http://localhost:4000/ui"
echo "Starting FastAPI..."