#!/usr/bin/env bash
set -Eeuo pipefail
VERSION="11.8.0"
ROOT="/opt/sustainable-catalyst/research-librarian-ai"
LIVE_BACKEND="$ROOT/backend"
COMPOSE="$ROOT/compose.yml"
ENV_FILE="$ROOT/.env.contabo"
CORE_ENV="/opt/sustainable-catalyst/core/.env.production"
CORE_CONTAINER="sc-core"
SERVICE="research-librarian"
CONTAINER="sc-research-librarian"
BACKUP_ROOT="/opt/sustainable-catalyst/backups/research-librarian-ai"
ARCHIVE="${1:-/tmp/sustainable-catalyst-research-librarian-backend-v11.8.0.zip}"
TMP="$(mktemp -d /tmp/sc-rl-v1180.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT
fail(){ echo "ERROR: $*" >&2; exit 1; }
for c in docker unzip rsync python3 curl tar grep; do command -v "$c" >/dev/null 2>&1 || fail "$c is required"; done
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
grep -q '__version__ = "11.8.0"' "$INIT" || fail "backend package version mismatch"
for f in app/api/core.py app/async_jobs.py app/services/document_jobs.py app/contracts/unified_scholarly_ai_environment.py app/services/unified_scholarly_ai_environment.py app/contracts/research_integrity_methodological_audit.py app/services/research_integrity_methodological_audit.py app/contracts/peer_review_scholarly_critique_intelligence.py app/services/peer_review_scholarly_critique_intelligence.py tests/test_v1180_peer_review_scholarly_critique_intelligence.py migrations/033_peer_review_scholarly_critique_intelligence.sql; do
  [[ -f "$SRC_BACKEND/$f" ]] || fail "required backend file missing: $f"
done
grep -q 'SCHOLARLY_CRITIQUE_SCHEMA' "$SRC_BACKEND/app/contracts/peer_review_scholarly_critique_intelligence.py" || fail "v11.8 critique contract missing"
grep -q '"peer-review-scholarly-critique-intelligence-snapshot"' "$SRC_BACKEND/app/async_jobs.py" || fail "v11.8 durable snapshot job missing"
grep -q '/peer-review-scholarly-critique-intelligence/critique-projects/{critique_project_id}/editorial-handoff' "$SRC_BACKEND/app/api/core.py" || fail "v11.8 editorial handoff API missing"
grep -q 'automatic_accept_reject.*False' "$SRC_BACKEND/app/services/peer_review_scholarly_critique_intelligence.py" || fail "v11.8 accept/reject guardrail missing"
grep -q 'automatic_reviewer_ranking.*False' "$SRC_BACKEND/app/services/peer_review_scholarly_critique_intelligence.py" || fail "v11.8 reviewer ranking guardrail missing"
grep -q 'automatic_scientific_validity_verdict.*False' "$SRC_BACKEND/app/services/peer_review_scholarly_critique_intelligence.py" || fail "v11.8 validity guardrail missing"

echo "=== BACKUP RESEARCH LIBRARIAN ==="
mkdir -p "$BACKUP_ROOT"; stamp="$(date +%Y%m%d-%H%M%S)"
tar -C "$ROOT" -czf "$BACKUP_ROOT/backend-before-v${VERSION}-${stamp}.tgz" backend
cp -a "$COMPOSE" "$BACKUP_ROOT/compose-before-v${VERSION}-${stamp}.yml"
cp -a "$ENV_FILE" "$BACKUP_ROOT/env-before-v${VERSION}-${stamp}"

echo "=== INSTALL v${VERSION} BACKEND ==="
rsync -a --exclude='data/' --exclude='__pycache__/' --exclude='.pytest_cache/' --exclude='*.pyc' --exclude='.env' --exclude='.env.*' "$SRC_BACKEND/" "$LIVE_BACKEND/"
python3 - "$COMPOSE" <<'PYCOMPOSE1180'
from pathlib import Path
import re,sys
p=Path(sys.argv[1]); s=p.read_text()
s=re.sub(r'(?m)^(\s*image:\s*sustainable-catalyst-research-librarian:).*$', r'\g<1>11.8.0', s)
s=re.sub(r'(?m)^(\s*SC_RL_RELEASE_VERSION:\s*)["\']?[^"\'\n]+["\']?\s*$', r'\g<1>"11.8.0"', s)
p.write_text(s)
PYCOMPOSE1180
python3 - "$ENV_FILE" "$CORE_ENV" <<'PYENV1180'
from pathlib import Path
import sys
def parse(path):
    out={}
    try: content=Path(path).read_text()
    except (FileNotFoundError,PermissionError,OSError): return out
    for raw in content.splitlines():
        line=raw.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        k,v=line.split('=',1); out[k.strip()]=v.strip().strip('"').strip("'")
    return out
def set_values(path,updates):
    p=Path(path); lines=p.read_text().splitlines(); result=[]; done=set()
    for raw in lines:
        if '=' in raw and not raw.lstrip().startswith('#'):
            k=raw.split('=',1)[0].strip()
            if k in updates: result.append(f"{k}={updates[k]}"); done.add(k); continue
        result.append(raw)
    for k,v in updates.items():
        if k not in done: result.append(f"{k}={v}")
    p.write_text('\n'.join(result).rstrip()+'\n')
rl=parse(sys.argv[1]); core=parse(sys.argv[2]); core_key=core.get('SC_CORE_WRITE_API_KEY','').strip(); rl_key=rl.get('SC_RL_CORE_WRITE_API_KEY','').strip()
if not core_key and not rl_key: raise SystemExit('SC_CORE_WRITE_API_KEY is missing and no existing Librarian Core write key is configured.')
updates={'SC_RL_RELEASE_VERSION':'11.8.0','SC_RL_CORE_ENABLED':'true','SC_RL_CORE_BASE_URL':'http://sc-core:8090','SC_RL_CORE_MINIMUM_VERSION':'3.3.0','SC_RL_CORE_SUPPORTED_MAJOR':'3','SC_RL_CORE_FAIL_CLOSED_WRITES':'true','SC_RL_ASYNC_JOBS_ENABLED':'true'}
if core_key: updates['SC_RL_CORE_WRITE_API_KEY']=core_key
set_values(sys.argv[1],updates)
print('PASS: Research Librarian Core integration environment aligned (secret not displayed).')
PYENV1180
cd "$ROOT"; docker compose -f "$COMPOSE" config --quiet
if grep -qE '^[[:space:]]*build:' "$COMPOSE"; then docker compose -f "$COMPOSE" build "$SERVICE"; else docker build -t "sustainable-catalyst-research-librarian:${VERSION}" "$LIVE_BACKEND"; fi
docker compose -f "$COMPOSE" up -d --force-recreate "$SERVICE"
for i in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:8093/health >"$TMP/health.json" 2>/dev/null && python3 - "$TMP/health.json" <<'PYHEALTH1180' >/dev/null 2>&1
import json,sys
x=json.load(open(sys.argv[1])); assert x.get('version')=='11.8.0' and x.get('ready') is True
PYHEALTH1180
  then break; fi
  if [[ "$i" == 90 ]]; then docker logs --tail=240 "$CONTAINER" >&2 || true; cat "$TMP/health.json" >&2 2>/dev/null || true; fail "Research Librarian v11.8.0 did not become ready"; fi
  sleep 2
done

echo "=== VERIFY v11.8 PEER REVIEW & SCHOLARLY CRITIQUE INTELLIGENCE ==="
docker exec -i "$CONTAINER" python - <<'PYV1180VERIFY'
import os
from app.services.peer_review_scholarly_critique_intelligence import capabilities, PeerReviewScholarlyCritiqueIntelligenceStore
from app.async_jobs import JOB_TYPES
from app.main import app
cap=capabilities(); assert cap['milestone']=='11.8' and cap['durable'] is True
assert cap['human_reviewer_critiques'] is True and cap['cross_review_matrix'] is True and cap['editorial_handoff'] is True
assert cap['automatic_accept_reject'] is False and cap['automatic_editorial_decision'] is False
assert cap['automatic_reviewer_ranking'] is False and cap['automatic_scientific_validity_verdict'] is False
assert cap['automatic_misconduct_inference'] is False and cap['automatic_publication_block'] is False
assert cap['automatic_execution'] is False and cap['automatic_truth_promotion'] is False
assert 'peer-review-scholarly-critique-intelligence-snapshot' in JOB_TYPES
paths={getattr(r,'path','') for r in app.routes}
required={'/v1/core/peer-review-scholarly-critique-intelligence/capabilities','/v1/core/peer-review-scholarly-critique-intelligence/critique-projects','/v1/core/peer-review-scholarly-critique-intelligence/critique-projects/{critique_project_id}/cross-review-matrix','/v1/core/peer-review-scholarly-critique-intelligence/critique-projects/{critique_project_id}/editorial-handoff','/v1/core/peer-review-scholarly-critique-intelligence/snapshots/freeze'}
assert not(required-paths),required-paths
store=PeerReviewScholarlyCritiqueIntelligenceStore()
if os.environ.get('SC_RL_DATABASE_BACKEND','').lower() in {'postgres','postgresql','neon'}: assert store.backend=='postgres'
print('PASS: v11.8 peer review/scholarly critique intelligence active on',store.backend)
PYV1180VERIFY

docker exec -i "$CONTAINER" python - <<'PYJOBS1180'
from app.async_jobs import JOB_TYPES
for job in ['reproduction-replication-intelligence-snapshot','cross-study-synthesis-meta-research-snapshot','research-integrity-methodological-audit-snapshot','peer-review-scholarly-critique-intelligence-snapshot']: assert job in JOB_TYPES
print('PASS: v11.5/v11.6/v11.7/v11.8 durable snapshot jobs registered')
PYJOBS1180

echo "PASS: Research Librarian AI v11.8.0 Peer Review & Scholarly Critique Intelligence backend deployed and verified."
