#!/usr/bin/env bash
set -Eeuo pipefail

RELEASE_VERSION="7.0.0"
RELEASE_TAG="v${RELEASE_VERSION}"
SCRIPT_REVISION="v700-py312-connected-research-platform-r1"
REPO_URL="git@github.com:Content-Catalyst-LLC/sustainable-catalyst-research-librarian-ai.git"
ZIP_PATH="${1:-$HOME/Downloads/sustainable-catalyst-research-librarian-ai-v7.0.0.zip}"
REPO_DIR="${2:-$HOME/Downloads/sustainable-catalyst-research-librarian-ai-repo-v700-clean}"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

run_clean() {
  env \
    -u VIRTUAL_ENV \
    -u PYTHONHOME \
    -u PYTHONPATH \
    -u PYTHONEXECUTABLE \
    -u __PYVENV_LAUNCHER__ \
    -u CONDA_PREFIX \
    -u CONDA_DEFAULT_ENV \
    -u PYENV_VERSION \
    "$@"
}

for command_name in git unzip rsync php node ssh; do
  command -v "$command_name" >/dev/null 2>&1 || fail "$command_name is required."
done
[[ -f "$ZIP_PATH" ]] || fail "Release ZIP not found: $ZIP_PATH"

echo "Research Librarian v${RELEASE_VERSION} push script (${SCRIPT_REVISION})"

find_python_312() {
  local candidate resolved version brew_prefix
  local -a candidates=()
  [[ -n "${SC_RL_PYTHON:-}" ]] && candidates+=("$SC_RL_PYTHON")
  if command -v brew >/dev/null 2>&1; then
    brew_prefix="$(brew --prefix python@3.12 2>/dev/null || true)"
    [[ -n "$brew_prefix" ]] && candidates+=("$brew_prefix/bin/python3.12")
  fi
  candidates+=(
    "/opt/homebrew/opt/python@3.12/bin/python3.12"
    "/usr/local/opt/python@3.12/bin/python3.12"
    "python3.12"
  )

  for candidate in "${candidates[@]}"; do
    if [[ "$candidate" == */* ]]; then
      [[ -x "$candidate" ]] || continue
      resolved="$candidate"
    else
      resolved="$(command -v "$candidate" 2>/dev/null || true)"
      [[ -n "$resolved" ]] || continue
    fi
    version="$(run_clean "$resolved" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
    if [[ "$version" == "3.12" ]]; then
      printf '%s\n' "$resolved"
      return 0
    fi
  done
  return 1
}

PYTHON_BIN="$(find_python_312 || true)"
[[ -n "$PYTHON_BIN" ]] || fail "Python 3.12 is required. Install it with: brew install python@3.12"
PYTHON_VERSION="$(run_clean "$PYTHON_BIN" --version 2>&1)"
PYTHON_EXECUTABLE="$(run_clean "$PYTHON_BIN" -c 'import os,sys; print(os.path.realpath(sys.executable))')"
PYTHON_MINOR="$(run_clean "$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
[[ "$PYTHON_MINOR" == "3.12" ]] || fail "Selected interpreter is not Python 3.12: $PYTHON_VERSION ($PYTHON_EXECUTABLE)"
printf 'Using release Python: %s\nResolved executable: %s\n' "$PYTHON_VERSION" "$PYTHON_EXECUTABLE"

echo "Checking GitHub SSH authentication..."
SSH_OUTPUT="$(ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -T git@github.com 2>&1 || true)"
grep -qi "successfully authenticated" <<<"$SSH_OUTPUT" || fail "GitHub SSH authentication is not ready. Run: ssh -T git@github.com"

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/sc-rl-v700.XXXXXX")"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

unzip -q "$ZIP_PATH" -d "$TMP_DIR/release"
SOURCE_DIR="$TMP_DIR/release/sustainable-catalyst-research-librarian-ai"
[[ -f "$SOURCE_DIR/sustainable-catalyst-research-librarian-ai.php" ]] || fail "The ZIP does not contain the expected plugin folder."
[[ -f "$SOURCE_DIR/backend/app/store.py" ]] || fail "The package does not contain the durable SQLite backend."
[[ -f "$SOURCE_DIR/tests/hybrid-retrieval-citation-contract-test.php" ]] || fail "The inherited hybrid retrieval contract test is missing."
[[ -f "$SOURCE_DIR/tests/retrieval-calibration-regression-contract-test.php" ]] || fail "The inherited retrieval calibration contract test is missing."
[[ -f "$SOURCE_DIR/tests/production-public-workspace-contract-test.php" ]] || fail "The inherited v6.5.0 public workspace contract test is missing."
[[ -f "$SOURCE_DIR/data/research_librarian_public_workspace_manifest_v6.5.0.json" ]] || fail "The inherited v6.5.0 public workspace manifest is missing."
[[ -f "$SOURCE_DIR/tests/accessibility-performance-interface-contract-test.php" ]] || fail "The v6.5.1 accessibility/performance contract test is missing."
[[ -f "$SOURCE_DIR/data/research_librarian_accessibility_performance_manifest_v6.5.1.json" ]] || fail "The v6.5.1 accessibility/performance manifest is missing."
[[ -f "$SOURCE_DIR/docs/V651_ACCESSIBILITY_PERFORMANCE_INTERFACE_RELIABILITY.md" ]] || fail "The v6.5.1 release documentation is missing."
[[ -f "$SOURCE_DIR/docs/V650_PRODUCTION_PUBLIC_RESEARCH_WORKSPACE.md" ]] || fail "The v6.5.0 release documentation is missing."
[[ -f "$SOURCE_DIR/tests/platform-intelligence-typed-handoffs-contract-test.php" ]] || fail "The v6.6.0 platform intelligence contract test is missing."
[[ -f "$SOURCE_DIR/tests/platform-handoff-wordpress-functional-test.php" ]] || fail "The v6.6.0 WordPress handoff functional test is missing."
[[ -f "$SOURCE_DIR/data/research_librarian_platform_handoffs_manifest_v6.6.0.json" ]] || fail "The v6.6.0 platform handoff manifest is missing."
[[ -f "$SOURCE_DIR/docs/V660_PLATFORM_INTELLIGENCE_TYPED_HANDOFFS.md" ]] || fail "The v6.6.0 release documentation is missing."
[[ -f "$SOURCE_DIR/backend/app/platform_handoffs.py" ]] || fail "The platform handoff backend module is missing."
[[ -f "$SOURCE_DIR/backend/app/governance.py" ]] || fail "The governance backend module is missing."
[[ -f "$SOURCE_DIR/includes/class-sc-rl-v670-governance-center.php" ]] || fail "The WordPress governance module is missing."
[[ -f "$SOURCE_DIR/backend/tests/test_platform_handoffs.py" ]] || fail "The platform handoff backend tests are missing."
[[ -f "$SOURCE_DIR/tests/research-quality-governance-contract-test.php" ]] || fail "The inherited governance contract test is missing."
[[ -f "$SOURCE_DIR/tests/research-quality-governance-functional-test.php" ]] || fail "The inherited governance functional test is missing."
[[ -f "$SOURCE_DIR/backend/tests/test_governance.py" ]] || fail "The inherited governance backend tests are missing."
[[ -f "$SOURCE_DIR/data/research_librarian_quality_governance_manifest_v7.0.0.json" ]] || fail "The inherited governance manifest is missing."
[[ -f "$SOURCE_DIR/docs/V670_RESEARCH_QUALITY_GOVERNANCE_CENTER.md" ]] || fail "The inherited governance documentation is missing."
[[ -f "$SOURCE_DIR/includes/class-sc-rl-v700-connected-platform.php" ]] || fail "The WordPress connected platform module is missing."
[[ -f "$SOURCE_DIR/backend/app/platform_v7.py" ]] || fail "The connected platform backend service is missing."
[[ -f "$SOURCE_DIR/backend/app/generation_adapter.py" ]] || fail "The provider-independent generation adapter is missing."
[[ -f "$SOURCE_DIR/backend/tests/test_connected_platform_v7.py" ]] || fail "The v7 connected platform backend tests are missing."
[[ -f "$SOURCE_DIR/tests/connected-research-platform-contract-test.php" ]] || fail "The v7 connected platform contract test is missing."
[[ -f "$SOURCE_DIR/tests/connected-research-platform-functional-test.php" ]] || fail "The v7 connected platform functional test is missing."
[[ -f "$SOURCE_DIR/data/research_librarian_connected_platform_manifest_v7.0.0.json" ]] || fail "The v7 connected platform manifest is missing."
[[ -f "$SOURCE_DIR/docs/V700_CONNECTED_RESEARCH_INTELLIGENCE_PLATFORM.md" ]] || fail "The v7 release documentation is missing."
[[ -f "$SOURCE_DIR/pytest.ini" ]] || fail "The package does not contain repository-root pytest configuration."
grep -q 'Version: 7.0.0' "$SOURCE_DIR/sustainable-catalyst-research-librarian-ai.php" || fail "The package version marker is not 7.0.0."
grep -q 'data-workspace-version="2.0"' "$SOURCE_DIR/sustainable-catalyst-research-librarian-ai.php" || fail "The public workspace marker is missing."
grep -q 'Build Research Workspace' "$SOURCE_DIR/sustainable-catalyst-research-librarian-ai.php" || fail "The public workspace submit action is missing."
grep -q 'research_mode: str = Field' "$SOURCE_DIR/backend/app/models.py" || fail "The research-mode request contract is missing."
grep -q '@app.post("/v1/session/reset"' "$SOURCE_DIR/backend/app/main.py" || fail "The session reset endpoint is missing."
grep -q 'sc-research-librarian-public-workspace/2.0' "$SOURCE_DIR/backend/app/main.py" || fail "The public workspace response schema is missing."
grep -q 'function workspaceMarkdown' "$SOURCE_DIR/assets/sc-research-librarian-ai.js" || fail "The Markdown workspace export is missing."
grep -q 'data-sc-rl-download-markdown' "$SOURCE_DIR/sustainable-catalyst-research-librarian-ai.php" || fail "The Markdown download control is missing."
grep -q 'sc-rl-ai--workspace' "$SOURCE_DIR/assets/sc-research-librarian-ai.css" || fail "The responsive workspace styles are missing."
grep -q 'role="combobox"' "$SOURCE_DIR/sustainable-catalyst-research-librarian-ai.php" || fail "The accessible title combobox is missing."
grep -q 'data-sc-rl-feedback-dialog' "$SOURCE_DIR/sustainable-catalyst-research-librarian-ai.php" || fail "The accessible feedback dialog is missing."
grep -q 'SCResearchLibrarianRuntime' "$SOURCE_DIR/assets/sc-research-librarian-ai.js" || fail "The shared request cache is missing."
grep -q 'prefers-reduced-motion: reduce' "$SOURCE_DIR/assets/sc-research-librarian-ai.css" || fail "Reduced-motion support is missing."
grep -q 'GZipMiddleware' "$SOURCE_DIR/backend/app/main.py" || fail "FastAPI gzip middleware is missing."
grep -q 'SCHEMA_VERSION = 10' "$SOURCE_DIR/backend/app/store.py" || fail "The package does not declare SQLite schema version 10."
grep -q 'sc-research-librarian-knowledge-index/10.0' "$SOURCE_DIR/backend/app/store.py" || fail "The schema-10 index contract is missing."
grep -q 'CREATE TABLE IF NOT EXISTS research_projects' "$SOURCE_DIR/backend/app/store.py" || fail "Persistent research projects are missing."
grep -q 'CREATE TABLE IF NOT EXISTS research_investigations' "$SOURCE_DIR/backend/app/store.py" || fail "Persistent investigations are missing."
grep -q 'CREATE TABLE IF NOT EXISTS research_project_entities' "$SOURCE_DIR/backend/app/store.py" || fail "Project entities are missing."
grep -q 'CREATE TABLE IF NOT EXISTS connected_platform_backups' "$SOURCE_DIR/backend/app/store.py" || fail "Connected platform backups are missing."
grep -q '@app.get("/v1/platform/api"' "$SOURCE_DIR/backend/app/main.py" || fail "The stable v7 API manifest endpoint is missing."
grep -q '@app.post("/v1/projects"' "$SOURCE_DIR/backend/app/main.py" || fail "The project endpoint is missing."
grep -q '@app.post("/v1/investigations"' "$SOURCE_DIR/backend/app/main.py" || fail "The investigation endpoint is missing."
grep -q '@app.post("/v1/research/contradictions"' "$SOURCE_DIR/backend/app/main.py" || fail "Contradiction analysis is missing."
grep -q '@app.post("/v1/research/uncertainties"' "$SOURCE_DIR/backend/app/main.py" || fail "Uncertainty registers are missing."
grep -q '@app.post("/v1/platform/backups/import"' "$SOURCE_DIR/backend/app/main.py" || fail "Backup import validation is missing."
grep -q 'sc-generation-adapter/1.0' "$SOURCE_DIR/backend/app/generation_adapter.py" || fail "The generation adapter contract is missing."
grep -q 'class-sc-rl-v700-connected-platform.php' "$SOURCE_DIR/sustainable-catalyst-research-librarian-ai.php" || fail "The WordPress connected platform module is not loaded."
grep -q 'sc_connected_research_workspace' "$SOURCE_DIR/includes/class-sc-rl-v700-connected-platform.php" || fail "The connected workspace shortcode is missing."
grep -q 'sc-research-governance-policy/1.0' "$SOURCE_DIR/backend/app/governance.py" || fail "The governance policy contract is missing."
grep -q '@app.post("/v1/governance/release-gate"' "$SOURCE_DIR/backend/app/main.py" || fail "The release-gate endpoint is missing."
grep -q 'class-sc-rl-v670-governance-center.php' "$SOURCE_DIR/sustainable-catalyst-research-librarian-ai.php" || fail "The WordPress governance center is not loaded."
grep -q 'def evidence_gate' "$SOURCE_DIR/backend/app/calibration.py" || fail "The inherited minimum-evidence gate is missing."
grep -q 'def verify_citations' "$SOURCE_DIR/backend/app/provider.py" || fail "The inherited citation verifier is missing."
grep -q 'sc-research-handoff/2.0' "$SOURCE_DIR/backend/app/platform_handoffs.py" || fail "The handoff contract is missing."
grep -q 'sc-research-route/2.0' "$SOURCE_DIR/backend/app/platform_handoffs.py" || fail "The route contract is missing."
grep -q 'sc-research-artifact-return/1.0' "$SOURCE_DIR/backend/app/platform_handoffs.py" || fail "The artifact return contract is missing."
grep -q '@app.get("/v1/platform/capabilities"' "$SOURCE_DIR/backend/app/main.py" || fail "The capability endpoint is missing."
grep -q '@app.post("/v1/handoffs/prepare"' "$SOURCE_DIR/backend/app/main.py" || fail "The handoff preparation endpoint is missing."
grep -q '@app.get("/v1/platform/compatibility"' "$SOURCE_DIR/backend/app/main.py" || fail "The platform compatibility endpoint is missing."
grep -q '@app.post("/v1/handoffs/retry"' "$SOURCE_DIR/backend/app/main.py" || fail "The bounded retry endpoint is missing."
grep -q '@app.post("/v1/handoffs/token/refresh"' "$SOURCE_DIR/backend/app/main.py" || fail "The token refresh endpoint is missing."
grep -q '@app.post("/v1/handoffs/receipts"' "$SOURCE_DIR/backend/app/main.py" || fail "The receipt endpoint is missing."
grep -q 'CREATE TABLE IF NOT EXISTS platform_handoff_receipts' "$SOURCE_DIR/backend/app/store.py" || fail "The receipt ledger is missing."
grep -q 'CREATE TABLE IF NOT EXISTS cross_product_events' "$SOURCE_DIR/backend/app/store.py" || fail "The idempotency event ledger is missing."
grep -q 'sc-research-handoff-delivery/1.0' "$SOURCE_DIR/backend/app/platform_handoffs.py" || fail "The delivery contract is missing."
grep -q 'data-platform-handoff-retry-endpoint' "$SOURCE_DIR/sustainable-catalyst-research-librarian-ai.php" || fail "The public retry endpoint is missing."
grep -q 'class-sc-rl-v660-platform-handoffs.php' "$SOURCE_DIR/sustainable-catalyst-research-librarian-ai.php" || fail "The WordPress platform handoff bridge is not loaded."
grep -q 'data-platform-handoff-endpoint' "$SOURCE_DIR/sustainable-catalyst-research-librarian-ai.php" || fail "The public workspace handoff endpoint is missing."

if [[ -d "$REPO_DIR/.git" ]]; then
  echo "Using the existing local repository: $REPO_DIR"
else
  [[ ! -e "$REPO_DIR" ]] || fail "$REPO_DIR exists but is not a Git repository."
  echo "Cloning the repository..."
  git clone "$REPO_URL" "$REPO_DIR"
fi

cd "$REPO_DIR"
git remote get-url origin >/dev/null 2>&1 || fail "The repository has no origin remote."
git fetch origin --tags --prune
git switch main
git pull --ff-only origin main

if ! git diff --quiet || ! git diff --cached --quiet; then
  fail "The repository has uncommitted changes. Use a new clean directory or commit/stash them first."
fi
if git rev-parse -q --verify "refs/tags/$RELEASE_TAG" >/dev/null; then
  fail "Local tag $RELEASE_TAG already exists."
fi
if git ls-remote --exit-code --tags origin "refs/tags/$RELEASE_TAG" >/dev/null 2>&1; then
  fail "Remote tag $RELEASE_TAG already exists."
fi

echo "Replacing repository contents with Research Librarian v${RELEASE_VERSION}..."
rsync -a --delete \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude '.pytest_cache/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '*.sqlite3' \
  --exclude '*.sqlite3-wal' \
  --exclude '*.sqlite3-shm' \
  "$SOURCE_DIR/" "$REPO_DIR/"

printf '\nValidating PHP syntax...\n'
PHP_COUNT=0
while IFS= read -r -d '' file; do
  php -l "$file" >/dev/null
  PHP_COUNT=$((PHP_COUNT + 1))
done < <(find . -type f -name '*.php' -print0)
printf 'PHP syntax passed: %d files.\n' "$PHP_COUNT"

printf 'Validating JavaScript syntax...\n'
JS_COUNT=0
while IFS= read -r -d '' file; do
  node --check "$file"
  JS_COUNT=$((JS_COUNT + 1))
done < <(find assets -type f -name '*.js' -print0)
printf 'JavaScript syntax passed: %d files.\n' "$JS_COUNT"

printf 'Validating JSON files...\n'
run_clean "$PYTHON_BIN" - <<'PY'
import json
from pathlib import Path
paths = sorted(Path('.').rglob('*.json'))
for path in paths:
    json.loads(path.read_text())
print(f'JSON validation passed: {len(paths)} files.')
PY

printf 'Running WordPress release contract tests...\n'
WP_TEST_COUNT=0
for test_file in tests/*.php; do
  php "$test_file"
  WP_TEST_COUNT=$((WP_TEST_COUNT + 1))
done
printf 'WordPress contract suites passed: %d.\n' "$WP_TEST_COUNT"

printf 'Creating isolated Python 3.12 test environment...\n'
run_clean "$PYTHON_BIN" -m venv --copies "$TMP_DIR/venv"
VENV_PY="$TMP_DIR/venv/bin/python"
[[ -x "$VENV_PY" ]] || fail "The Python virtual environment was not created."
VENV_MINOR="$(run_clean "$VENV_PY" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
VENV_VERSION="$(run_clean "$VENV_PY" --version 2>&1)"
VENV_EXECUTABLE="$(run_clean "$VENV_PY" -c 'import os,sys; print(os.path.realpath(sys.executable))')"
printf 'Verified test environment: %s\nVenv executable: %s\n' "$VENV_VERSION" "$VENV_EXECUTABLE"
if [[ "$VENV_MINOR" != "3.12" ]]; then
  cat "$TMP_DIR/venv/pyvenv.cfg" >&2 || true
  fail "The temporary environment resolved to Python $VENV_MINOR instead of 3.12."
fi

run_clean "$VENV_PY" -m pip install --quiet --upgrade pip
run_clean "$VENV_PY" -m pip install --quiet --only-binary=:all: -r backend/requirements.txt
printf 'Running backend tests from the repository root...\n'
SC_RL_BACKEND_API_KEY=test-key SC_RL_DATA_DIR="$TMP_DIR/test-data-root" run_clean "$VENV_PY" -m pytest -q backend/tests
printf 'Running backend tests from backend/ to validate deployment imports...\n'
(
  cd backend
  SC_RL_BACKEND_API_KEY=test-key SC_RL_DATA_DIR="$TMP_DIR/test-data-backend" run_clean "$VENV_PY" -m pytest -q tests
)

printf 'Running Python compile validation...\n'
run_clean "$VENV_PY" -m compileall -q backend/app backend/tests

printf 'Running push-safe secret scan...\n'
if grep -RInE \
  --exclude-dir=.git --exclude-dir=.venv --exclude-dir=.pytest_cache --exclude-dir=__pycache__ \
  --exclude='*.pyc' --exclude='PUSH_RESEARCH_LIBRARIAN_*.sh' \
  '(BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{30,}|AIza[0-9A-Za-z_-]{30,})' .; then
  fail "Potential secret material was detected. Review the matches before pushing."
fi

printf 'Committing and tagging v%s...\n' "$RELEASE_VERSION"
git add -A
if git diff --cached --quiet; then
  fail "No release changes were detected after extraction."
fi
git commit -m "Build Research Librarian v${RELEASE_VERSION}"
git tag -a "$RELEASE_TAG" -m "Research Librarian v${RELEASE_VERSION} — Connected Research Intelligence Platform"

echo "Pushing main and $RELEASE_TAG..."
git push origin main
git push origin "$RELEASE_TAG"

printf '\nResearch Librarian v%s was validated and pushed successfully.\n' "$RELEASE_VERSION"

