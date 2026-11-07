#!/usr/bin/env bash
# One-command launcher for SWASTI (macOS / Linux). Requires Docker Desktop running.
set -euo pipefail
cd "$(dirname "$0")"

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running. Start Docker Desktop, wait until it says 'running', then re-run ./start.sh"; exit 1
fi

if [ ! -f .env ]; then
  echo "Creating .env with fresh secrets and demo data enabled..."
  jwt=$(LC_ALL=C tr -dc 'a-f0-9' </dev/urandom | head -c 64)
  fernet=$(head -c 32 /dev/urandom | base64 | tr '+/' '-_' | tr -d '\n')
  sed -e "s|^JWT_SECRET=.*|JWT_SECRET=${jwt}|" \
      -e "s|^TRANSCRIPT_ENCRYPTION_KEY=.*|TRANSCRIPT_ENCRYPTION_KEY=${fernet}|" \
      -e "s|^SEED_FLAGS=.*|SEED_FLAGS=--demo|" .env.example > .env
fi

docker compose up --build -d
echo "Waiting for SWASTI to start (first run can take a few minutes)..."
for _ in $(seq 1 120); do
  if curl -fs http://localhost:8080/api/health >/dev/null 2>&1; then
    echo "SWASTI is running at http://localhost:8080  (demo password: Demo@1234)"
    (command -v open >/dev/null && open http://localhost:8080) || (command -v xdg-open >/dev/null && xdg-open http://localhost:8080) || true
    echo "Logs: docker compose logs -f    Stop: docker compose down"
    exit 0
  fi
  sleep 5
done
echo "SWASTI did not become healthy in time. Recent API logs:"; docker compose logs --tail 40 api; exit 1
