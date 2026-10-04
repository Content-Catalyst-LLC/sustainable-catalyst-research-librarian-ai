#!/usr/bin/env bash
set -Eeuo pipefail

ENV_FILE="/opt/sustainable-catalyst/research-librarian-ai/.env.contabo"
BASE_URL="${SC_RL_LOCAL_URL:-http://127.0.0.1:8093}"

[[ -f "$ENV_FILE" ]] || { echo "ERROR: Research Librarian environment file missing: $ENV_FILE" >&2; exit 1; }

API_KEY="$(python3 - "$ENV_FILE" <<'PYKEY'
from pathlib import Path
import sys
for raw in Path(sys.argv[1]).read_text().splitlines():
    if raw.startswith('SC_RL_BACKEND_API_KEY='):
        print(raw.split('=',1)[1].strip().strip('"').strip("'"))
        break
PYKEY
)"
[[ -n "$API_KEY" ]] || { echo "ERROR: SC_RL_BACKEND_API_KEY is not configured." >&2; exit 1; }

read -r -p "Owner email: " OWNER_EMAIL
read -r -p "Owner display name: " OWNER_NAME
read -r -s -p "Owner password (12+ characters): " OWNER_PASSWORD
echo
read -r -s -p "Confirm owner password: " OWNER_PASSWORD_CONFIRM
echo

[[ "$OWNER_PASSWORD" == "$OWNER_PASSWORD_CONFIRM" ]] || { echo "ERROR: passwords do not match." >&2; exit 1; }
[[ "${#OWNER_PASSWORD}" -ge 12 ]] || { echo "ERROR: password must be at least 12 characters." >&2; exit 1; }

TMP="$(mktemp /tmp/sc-rl-owner.XXXXXX.json)"
trap 'rm -f "$TMP"; unset API_KEY OWNER_PASSWORD OWNER_PASSWORD_CONFIRM' EXIT

OWNER_EMAIL="$OWNER_EMAIL" OWNER_NAME="$OWNER_NAME" OWNER_PASSWORD="$OWNER_PASSWORD" python3 - "$TMP" <<'PYPAYLOAD'
import json,os,sys
payload={
  "email":os.environ["OWNER_EMAIL"],
  "display_name":os.environ["OWNER_NAME"],
  "password":os.environ["OWNER_PASSWORD"],
  "role":"owner",
}
open(sys.argv[1],"w").write(json.dumps(payload))
PYPAYLOAD

curl -fsS \
  -H "Content-Type: application/json" \
  -H "X-SC-RL-Key: $API_KEY" \
  --data-binary "@$TMP" \
  "$BASE_URL/v1/research-librarian/auth/provision" \
  | python3 -m json.tool

echo "PASS: owner provisioning request completed."
echo "You can now sign in through the independent Research Librarian web app."
