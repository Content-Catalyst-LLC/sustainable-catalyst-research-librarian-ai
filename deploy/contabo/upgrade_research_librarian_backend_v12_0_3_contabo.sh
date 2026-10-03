#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="12.0.3"
ROOT="/opt/sustainable-catalyst/research-librarian-ai"
LIVE_BACKEND="$ROOT/backend"
COMPOSE="$ROOT/compose.yml"
ENV_FILE="$ROOT/.env.contabo"
CORE_ENV="/opt/sustainable-catalyst/core/.env.production"
CORE_CONTAINER="sc-core"
SERVICE="research-librarian"
CONTAINER="sc-research-librarian"
BACKUP_ROOT="/opt/sustainable-catalyst/backups/research-librarian-ai"
ARCHIVE="${1:-/tmp/sustainable-catalyst-research-librarian-backend-v12.0.3.zip}"
TMP="$(mktemp -d /tmp/sc-rl-v1203.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT

fail(){ echo "ERROR: $*" >&2; exit 1; }

for c in docker unzip rsync python3 curl tar grep; do
  command -v "$c" >/dev/null 2>&1 || fail "$c is required"
done

[[ -f "$ARCHIVE" ]] || fail "backend package not found: $ARCHIVE"
[[ -d "$ROOT" && -d "$LIVE_BACKEND" ]] || fail "runtime root/backend missing: $ROOT"
[[ -f "$COMPOSE" ]] || fail "compose file missing: $COMPOSE"
[[ -f "$ENV_FILE" ]] || fail "Research Librarian environment file missing: $ENV_FILE"
docker inspect "$CORE_CONTAINER" >/dev/null 2>&1 || fail "Platform Core container is not present: $CORE_CONTAINER"

unzip -tq "$ARCHIVE" >/dev/null || fail "invalid backend ZIP"
unzip -q "$ARCHIVE" -d "$TMP/package"

INIT="$(find "$TMP/package" -type f -path '*/backend/app/__init__.py' | head -1)"
[[ -n "$INIT" ]] || fail "backend/app/__init__.py missing from package"
SRC_BACKEND="$(dirname "$(dirname "$INIT")")"

grep -q '__version__ = "12.0.3"' "$INIT" || fail "backend package version mismatch"

for f in \
  app/main.py \
  app/api/independent.py \
  app/contracts/persistent_research_session_conversation.py \
  app/services/persistent_research_session_conversation.py \
  app/contracts/independent_research_librarian_api.py \
  app/services/independent_research_librarian_api.py \
  tests/test_v1203_persistent_research_session_conversation.py \
  migrations/038_persistent_research_session_conversation.sql
do
  [[ -f "$SRC_BACKEND/$f" ]] || fail "required backend file missing: $f"
done

grep -q 'PERSISTENT_RESEARCH_SESSION_SCHEMA' "$SRC_BACKEND/app/contracts/persistent_research_session_conversation.py" || fail "persistent session contract missing"
grep -q 'sc_rl_persistent_research_sessions' "$SRC_BACKEND/app/services/persistent_research_session_conversation.py" || fail "persistent Postgres session store missing"
grep -q '@router.post("/sessions"' "$SRC_BACKEND/app/api/independent.py" || fail "independent session create route missing"
grep -q 'persistent_session_store.history_for_generation' "$SRC_BACKEND/app/main.py" || fail "legacy ask persistent history integration missing"
if grep -q '_sessions\[session_id\]\.extend' "$SRC_BACKEND/app/main.py"; then
  fail "legacy in-memory session append is still present"
fi

echo "=== BACKUP RESEARCH LIBRARIAN ==="
mkdir -p "$BACKUP_ROOT"
stamp="$(date +%Y%m%d-%H%M%S)"
tar -C "$ROOT" -czf "$BACKUP_ROOT/backend-before-v${VERSION}-${stamp}.tgz" backend
cp -a "$COMPOSE" "$BACKUP_ROOT/compose-before-v${VERSION}-${stamp}.yml"
cp -a "$ENV_FILE" "$BACKUP_ROOT/env-before-v${VERSION}-${stamp}"

echo "=== INSTALL v${VERSION} BACKEND ==="
rsync -a \
  --exclude='data/' \
  --exclude='__pycache__/' \
  --exclude='.pytest_cache/' \
  --exclude='*.pyc' \
  --exclude='.env' \
  --exclude='.env.*' \
  "$SRC_BACKEND/" "$LIVE_BACKEND/"

python3 - "$COMPOSE" <<'PYCOMPOSE1203'
from pathlib import Path
import re,sys
p=Path(sys.argv[1])
s=p.read_text()
s=re.sub(r'(?m)^(\s*image:\s*sustainable-catalyst-research-librarian:).*$', r'\g<1>12.0.3', s)
s=re.sub(r'(?m)^(\s*SC_RL_RELEASE_VERSION:\s*)["\']?[^"\'\n]+["\']?\s*$', r'\g<1>"12.0.3"', s)
p.write_text(s)
PYCOMPOSE1203

python3 - "$ENV_FILE" "$CORE_ENV" <<'PYENV1203'
from pathlib import Path
import sys

def parse(path):
    out={}
    try:
        content=Path(path).read_text()
    except (FileNotFoundError,PermissionError,OSError):
        return out
    for raw in content.splitlines():
        line=raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k,v=line.split('=',1)
        out[k.strip()]=v.strip().strip('"').strip("'")
    return out

def set_values(path,updates):
    p=Path(path)
    lines=p.read_text().splitlines()
    result=[]
    done=set()
    for raw in lines:
        if '=' in raw and not raw.lstrip().startswith('#'):
            k=raw.split('=',1)[0].strip()
            if k in updates:
                result.append(f"{k}={updates[k]}")
                done.add(k)
                continue
        result.append(raw)
    for k,v in updates.items():
        if k not in done:
            result.append(f"{k}={v}")
    p.write_text('\n'.join(result).rstrip()+'\n')

rl=parse(sys.argv[1])
core=parse(sys.argv[2])
core_key=core.get('SC_CORE_WRITE_API_KEY','').strip()
rl_key=rl.get('SC_RL_CORE_WRITE_API_KEY','').strip()
if not core_key and not rl_key:
    raise SystemExit('SC_CORE_WRITE_API_KEY is missing and no existing Librarian Core write key is configured.')

updates={
    'SC_RL_RELEASE_VERSION':'12.0.3',
    'SC_RL_CORE_ENABLED':'true',
    'SC_RL_CORE_BASE_URL':'http://sc-core:8090',
    'SC_RL_CORE_MINIMUM_VERSION':'3.3.0',
    'SC_RL_CORE_SUPPORTED_MAJOR':'3',
    'SC_RL_CORE_FAIL_CLOSED_WRITES':'true',
    'SC_RL_ASYNC_JOBS_ENABLED':'true',
}
if core_key:
    updates['SC_RL_CORE_WRITE_API_KEY']=core_key

set_values(sys.argv[1],updates)
print('PASS: Research Librarian environment aligned (secret not displayed).')
PYENV1203

cd "$ROOT"
docker compose -f "$COMPOSE" config --quiet

if grep -qE '^[[:space:]]*build:' "$COMPOSE"; then
  docker compose -f "$COMPOSE" build "$SERVICE"
else
  docker build -t "sustainable-catalyst-research-librarian:${VERSION}" "$LIVE_BACKEND"
fi

docker compose -f "$COMPOSE" up -d --force-recreate "$SERVICE"

for i in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:8093/health >"$TMP/health.json" 2>/dev/null && python3 - "$TMP/health.json" <<'PYHEALTH1203' >/dev/null 2>&1
import json,sys
x=json.load(open(sys.argv[1]))
assert x.get('version')=='12.0.3'
assert x.get('ready') is True
assert x.get('runtime_authority')=='python-fastapi-backend'
assert x.get('wordpress_required') is False
assert x.get('independent_api_version')=='v1'
assert x.get('persistent_research_sessions') is True
PYHEALTH1203
  then
    break
  fi

  if [[ "$i" == 90 ]]; then
    docker logs --tail=240 "$CONTAINER" >&2 || true
    cat "$TMP/health.json" >&2 2>/dev/null || true
    fail "Research Librarian v12.0.3 did not become ready"
  fi
  sleep 2
done

echo "=== VERIFY v12.0.3 PERSISTENT RESEARCH SESSION & CONVERSATION RUNTIME ==="
docker exec -i "$CONTAINER" python - <<'PYV1203VERIFY'
import os,uuid
from app.main import app
from app.contracts.persistent_research_session_conversation import (
    ResearchSessionCreateRequest,
    ResearchSessionTurnAddRequest,
    ResearchSessionSnapshotRequest,
)
from app.services.persistent_research_session_conversation import (
    PersistentResearchSessionStore,
    capabilities,
)
from app.services.independent_research_librarian_api import api_manifest

cap=capabilities()
assert cap['milestone']=='12.0.3'
assert cap['persistent_sessions'] is True
assert cap['persistent_conversations'] is True
assert cap['legacy_ask_persistence'] is True
assert cap['wordpress_required'] is False
assert cap['client_ref_is_identity'] is False
assert cap['identity_sessions'] is False

manifest=api_manifest()
assert manifest['api_version']=='v1'
assert manifest['scope']['persistent_conversations'] is True
assert manifest['scope']['identity_sessions'] is False
assert manifest['next_boundary']=='independent-web-app-foundation'

paths={getattr(r,'path','') for r in app.routes}
required={
  '/v1/research-librarian/sessions',
  '/v1/research-librarian/sessions/{session_id}',
  '/v1/research-librarian/sessions/{session_id}/turns',
  '/v1/research-librarian/sessions/{session_id}/context',
  '/v1/research-librarian/sessions/{session_id}/state',
  '/v1/research-librarian/sessions/{session_id}/reset',
  '/v1/research-librarian/sessions/{session_id}/summary',
  '/v1/research-librarian/sessions/{session_id}/snapshots/freeze',
}
assert not(required-paths),required-paths

store=PersistentResearchSessionStore()
if os.environ.get('SC_RL_DATABASE_BACKEND','').lower() in {'postgres','postgresql','neon'}:
    assert store.backend=='postgres'

sid='deploy-v1203-'+uuid.uuid4().hex
session=store.create(
    ResearchSessionCreateRequest(title='v12.0.3 deployment verification',client_ref='deployment-verifier'),
    requested_session_id=sid,
)
store.add_turn(sid,ResearchSessionTurnAddRequest(role='user',content='Verify durable research session persistence.'))
store.add_turn(sid,ResearchSessionTurnAddRequest(role='assistant',content='Persistence verification receipt.'))

# Reconstruct the store and confirm the conversation survives object lifecycle.
store2=PersistentResearchSessionStore()
loaded=store2.get(sid)
turns=store2.turns(sid)
assert loaded['turn_count']==2
assert len(turns)==2
assert turns[1]['previous_turn_hash']==turns[0]['record_hash']
assert store2.history_for_generation(sid,2)[-1]['content']=='Persistence verification receipt.'
snapshot=store2.freeze_snapshot(sid,ResearchSessionSnapshotRequest(actor_ref='deployment-v12.0.3'))
assert len(snapshot['snapshot_hash'])==64
assert snapshot['governance']['wordpress_required'] is False

print('PASS: v12.0.3 persistent research-session runtime active on',store.backend)
print('PASS: session + turn hash chain + snapshot remained readable through store reconstruction')
print('PASS: client_ref remains non-identity; WordPress remains optional')
PYV1203VERIFY

echo "PASS: Research Librarian AI v12.0.3 Persistent Research Session & Conversation Runtime backend deployed and verified."
