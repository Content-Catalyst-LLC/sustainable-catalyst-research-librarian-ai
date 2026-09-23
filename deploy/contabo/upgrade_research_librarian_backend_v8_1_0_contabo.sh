#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="8.2.0"
TARGET_KEY="research-librarian"
PRODUCT="Research Librarian"
ARCHIVE="${1:-/tmp/sustainable-catalyst-research-librarian-backend-v8.2.0.zip}"
ROOT="${SC_TARGET_ROOT:-/opt/sustainable-catalyst/research-librarian}"
LIVE_BACKEND="$ROOT/backend"
COMPOSE="${SC_TARGET_COMPOSE:-$ROOT/compose.yml}"
SERVICE="${SC_TARGET_SERVICE:-research-librarian}"
CONTAINER="${SC_TARGET_CONTAINER:-sc-research-librarian}"
BACKUP_ROOT="/opt/sustainable-catalyst/backups"
TMP="$(mktemp -d /tmp/sc-energy-consumer-research-librarian.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT

fail(){ echo "ERROR: $*" >&2; exit 1; }
for cmd in unzip rsync docker python3 tar; do command -v "$cmd" >/dev/null || fail "$cmd is required"; done
[[ -f "$ARCHIVE" ]] || fail "backend package not found: $ARCHIVE"
[[ -d "$ROOT" && -d "$LIVE_BACKEND" ]] || fail "runtime root/backend missing: $ROOT"
[[ -f "$COMPOSE" ]] || fail "Compose file not found: $COMPOSE (override with SC_TARGET_COMPOSE if this service uses a nonstandard path)"
unzip -tq "$ARCHIVE" >/dev/null || fail "invalid backend ZIP"
unzip -q "$ARCHIVE" -d "$TMP/package"
consumer="$(find "$TMP/package" -type f -path '*/backend/app/energy_runtime_consumer.py' | head -1)"
[[ -n "$consumer" ]] || fail "energy runtime consumer missing from package"
SRC_BACKEND="$(dirname "$(dirname "$consumer")")"
grep -q "CONSUMER_VERSION = '$VERSION'" "$consumer" || fail "package version mismatch"
grep -q "TARGET_KEY = '$TARGET_KEY'" "$consumer" || fail "package target mismatch"

if [[ ! -d "$BACKUP_ROOT" ]]; then
  if mkdir -p "$BACKUP_ROOT" 2>/dev/null; then :; else
    command -v sudo >/dev/null || fail "$BACKUP_ROOT is unwritable and sudo is unavailable"
    sudo install -d -o "$(id -un)" -g "$(id -gn)" -m 750 "$BACKUP_ROOT"
  fi
fi
if [[ ! -w "$BACKUP_ROOT" ]]; then
  command -v sudo >/dev/null || fail "$BACKUP_ROOT is unwritable and sudo is unavailable"
  sudo chown "$(id -un):$(id -gn)" "$BACKUP_ROOT"
  sudo chmod 750 "$BACKUP_ROOT"
fi
stamp="$(date +%Y%m%d-%H%M%S)"
echo "=== BACKING UP $PRODUCT BACKEND ==="
tar -C "$ROOT" -czf "$BACKUP_ROOT/research-librarian-backend-before-v$VERSION-$stamp.tgz" backend
cp -a "$COMPOSE" "$BACKUP_ROOT/research-librarian-compose-before-v$VERSION-$stamp.yml"

# Overlay code only; preserve runtime data, local environment files, and service-specific state.
rsync -a   --exclude='data/' --exclude='__pycache__/' --exclude='.pytest_cache/' --exclude='*.pyc'   --exclude='.env' --exclude='.env.*'   "$SRC_BACKEND/" "$LIVE_BACKEND/"

# If the package carries a release compose file (Workbench / Decision Studio), adopt it while preserving env files and volumes.
PACKAGE_ROOT="$(dirname "$SRC_BACKEND")"
if [[ -f "$PACKAGE_ROOT/compose.yml" ]]; then
  cp "$PACKAGE_ROOT/compose.yml" "$COMPOSE"
fi

# Keep an existing release-version environment setting aligned without touching secrets.
for envfile in "$ROOT/.env.production" "$ROOT/.env"; do
  if [[ -f "$envfile" ]] && grep -q '^SC_RL_RELEASE_VERSION=' "$envfile"; then
    cp -a "$envfile" "$BACKUP_ROOT/research-librarian-env-before-v8.2.0-$stamp"
    python3 - "$envfile" <<'PYENV'
from pathlib import Path
import sys,re
p=Path(sys.argv[1]); s=p.read_text(); s=re.sub(r'(?m)^SC_RL_RELEASE_VERSION=.*$', 'SC_RL_RELEASE_VERSION=8.2.0', s); p.write_text(s)
PYENV
  fi
done

cd "$ROOT"
docker compose -f "$COMPOSE" config --quiet
echo "=== BUILDING $PRODUCT v$VERSION ==="
docker compose -f "$COMPOSE" build "$SERVICE"
docker compose -f "$COMPOSE" up -d --force-recreate "$SERVICE"

ready=0
for _ in $(seq 1 60); do
  state="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$CONTAINER" 2>/dev/null || true)"
  case "$state" in
    healthy) ready=1; break ;;
    running) sleep 3; ready=1; break ;;
    unhealthy|exited|dead) docker logs --tail=180 "$CONTAINER" >&2 || true; fail "$CONTAINER entered $state" ;;
  esac
  sleep 2
done
[[ "$ready" == 1 ]] || { docker logs --tail=180 "$CONTAINER" >&2 || true; fail "$CONTAINER did not become ready"; }

echo "=== VERIFYING ENERGY SYSTEMS CONSUMER ==="
docker exec -i "$CONTAINER" python - <<'PYVERIFY'
from app.main import app
from app.energy_runtime_consumer import framework
f=framework()
assert f['consumer_version']=='8.2.0', f
assert f['target_key']=='research-librarian', f
assert f['capabilities']['handoff_intake'] is True
assert f['capabilities']['automatic_execution'] is False
assert f['capabilities']['persistence'] is False
paths={getattr(r,'path',None) for r in app.routes}
assert '/v1/energy-runtime/consumer' in paths
assert '/v1/energy-runtime/consume' in paths
print('PASS: Research Librarian v8.2.0 Energy Systems contract intake is active')
print('PASS: intake remains ephemeral and performs no automatic target execution')
PYVERIFY

echo "PASS: $PRODUCT v$VERSION target-side Energy Systems runtime consumer deployed and verified."
