#!/usr/bin/env bash
set -Eeuo pipefail

export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"

RELEASE_VERSION="7.2.0"
RELEASE_TAG="v${RELEASE_VERSION}"
REPO_URL="git@github.com:Content-Catalyst-LLC/sustainable-catalyst-research-librarian-ai.git"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CANONICAL_ZIP_NAME="sustainable-catalyst-research-librarian-ai-v7.2.0-repository.zip"
ZIP_PATH="${1:-$SCRIPT_DIR/$CANONICAL_ZIP_NAME}"
REPO_DIR="${2:-$HOME/Downloads/sustainable-catalyst-research-librarian-ai-repo-v720-clean}"
EXPECTED_RELEASE_SHA256="${SC_RL_EXPECTED_RELEASE_SHA256:-}"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
run_clean() {
  env -u VIRTUAL_ENV -u PYTHONHOME -u PYTHONPATH -u PYTHONEXECUTABLE \
    -u __PYVENV_LAUNCHER__ -u CONDA_PREFIX -u CONDA_DEFAULT_ENV -u PYENV_VERSION "$@"
}

for command_name in git unzip rsync php node ssh shasum awk grep find; do
  command -v "$command_name" >/dev/null 2>&1 || fail "$command_name is required."
done
[[ -f "$ZIP_PATH" ]] || fail "Release ZIP not found: $ZIP_PATH"

ACTUAL_RELEASE_SHA256="$(shasum -a 256 "$ZIP_PATH" | awk '{print $1}')"
if [[ -n "$EXPECTED_RELEASE_SHA256" && "$ACTUAL_RELEASE_SHA256" != "$EXPECTED_RELEASE_SHA256" ]]; then
  fail "Release ZIP checksum mismatch. Expected $EXPECTED_RELEASE_SHA256 but found $ACTUAL_RELEASE_SHA256."
fi
printf 'Release archive: %s\nSHA-256: %s\n' "$ZIP_PATH" "$ACTUAL_RELEASE_SHA256"

find_release_python() {
  local candidate resolved minor brew_prefix
  local -a candidates=()
  [[ -n "${SC_RL_PYTHON:-}" ]] && candidates+=("$SC_RL_PYTHON")
  if command -v brew >/dev/null 2>&1; then
    brew_prefix="$(brew --prefix python@3.12 2>/dev/null || true)"
    [[ -n "$brew_prefix" ]] && candidates+=("$brew_prefix/bin/python3.12")
    brew_prefix="$(brew --prefix python@3.13 2>/dev/null || true)"
    [[ -n "$brew_prefix" ]] && candidates+=("$brew_prefix/bin/python3.13")
  fi
  candidates+=(
    "/opt/homebrew/opt/python@3.12/bin/python3.12"
    "/usr/local/opt/python@3.12/bin/python3.12"
    "/opt/homebrew/opt/python@3.13/bin/python3.13"
    "/usr/local/opt/python@3.13/bin/python3.13"
    "python3.12" "python3.13" "python3"
  )
  for candidate in "${candidates[@]}"; do
    if [[ "$candidate" == */* ]]; then
      [[ -x "$candidate" ]] || continue
      resolved="$candidate"
    else
      resolved="$(command -v "$candidate" 2>/dev/null || true)"
      [[ -n "$resolved" ]] || continue
    fi
    minor="$(run_clean "$resolved" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
    if [[ "$minor" == "3.12" || "$minor" == "3.13" ]]; then
      printf '%s\n' "$resolved"
      return 0
    fi
  done
  return 1
}

PYTHON_BIN="$(find_release_python || true)"
[[ -n "$PYTHON_BIN" ]] || fail "Python 3.12 or 3.13 is required for local validation. Install with: brew install python@3.12"
printf 'Using validation Python: %s\n' "$(run_clean "$PYTHON_BIN" --version 2>&1)"

echo "Checking GitHub SSH authentication..."
SSH_OUTPUT="$(ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -T git@github.com 2>&1 || true)"
grep -qi "successfully authenticated" <<<"$SSH_OUTPUT" || fail "GitHub SSH authentication is not ready. Run: ssh -T git@github.com"

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/sc-rl-v720.XXXXXX")"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

unzip -q "$ZIP_PATH" -d "$TMP_DIR/release"
SOURCE_DIR="$TMP_DIR/release/sustainable-catalyst-research-librarian-ai"
[[ -f "$SOURCE_DIR/sustainable-catalyst-research-librarian-ai.php" ]] || fail "The ZIP does not contain the expected plugin/repository folder."
[[ -f "$SOURCE_DIR/backend/app/library_context.py" ]] || fail "The v7.2.0 Library context backend module is missing."
[[ -f "$SOURCE_DIR/docs/V720_LIBRARY_OBJECT_MODEL_RESEARCH_CONTEXT_ALIGNMENT.md" ]] || fail "The v7.2.0 release documentation is missing."
[[ -f "$SOURCE_DIR/data/research_librarian_library_context_manifest_v7.2.0.json" ]] || fail "The v7.2.0 Library context manifest is missing."
[[ -f "$SOURCE_DIR/tests/v720-library-object-context-alignment-contract-test.php" ]] || fail "The v7.2.0 WordPress contract test is missing."
[[ -f "$SOURCE_DIR/backend/tests/test_v720_library_context.py" ]] || fail "The v7.2.0 backend test suite is missing."
grep -q 'Version: 7.2.0' "$SOURCE_DIR/sustainable-catalyst-research-librarian-ai.php" || fail "The plugin version marker is not 7.2.0."
grep -q '__version__ = "7.2.0"' "$SOURCE_DIR/backend/app/__init__.py" || fail "The backend version marker is not 7.2.0."
grep -q 'SCHEMA_VERSION = 13' "$SOURCE_DIR/backend/app/store.py" || fail "SQLite schema 13 is missing."
grep -q 'sc-research-library-object-model/1.0' "$SOURCE_DIR/backend/app/library_context.py" || fail "The Library object model contract is missing."
grep -q 'sc-connected-research-api/1.1' "$SOURCE_DIR/backend/app/platform_v7.py" || fail "Connected Research API 1.1 is missing."
grep -q 'research_context_id' "$SOURCE_DIR/assets/sc-research-librarian-ai.js" || fail "The public assistant context handoff is missing."

if [[ -d "$REPO_DIR/.git" ]]; then
  echo "Using existing clean repository: $REPO_DIR"
else
  [[ ! -e "$REPO_DIR" ]] || fail "$REPO_DIR exists but is not a Git repository."
  git clone "$REPO_URL" "$REPO_DIR"
fi

cd "$REPO_DIR"
git remote get-url origin >/dev/null 2>&1 || fail "The repository has no origin remote."
git fetch origin --tags --prune
git switch main
git pull --ff-only origin main
if ! git diff --quiet || ! git diff --cached --quiet; then
  fail "The repository has uncommitted changes. Use a different clean directory or commit/stash them first."
fi
if git rev-parse -q --verify "refs/tags/$RELEASE_TAG" >/dev/null; then fail "Local tag $RELEASE_TAG already exists."; fi
if git ls-remote --exit-code --tags origin "refs/tags/$RELEASE_TAG" >/dev/null 2>&1; then fail "Remote tag $RELEASE_TAG already exists."; fi

rsync -a --delete \
  --exclude '.git/' --exclude '.venv/' --exclude '.pytest_cache/' \
  --exclude '__pycache__/' --exclude '*.pyc' --exclude '*.sqlite3*' \
  "$SOURCE_DIR/" "$REPO_DIR/"

printf '\nValidating PHP syntax...\n'
PHP_COUNT=0
while IFS= read -r -d '' file; do php -l "$file" >/dev/null; PHP_COUNT=$((PHP_COUNT + 1)); done < <(find . -type f -name '*.php' -print0)
printf 'PHP syntax passed: %d files.\n' "$PHP_COUNT"

printf 'Validating JavaScript syntax...\n'
JS_COUNT=0
while IFS= read -r -d '' file; do node --check "$file" >/dev/null; JS_COUNT=$((JS_COUNT + 1)); done < <(find assets -type f -name '*.js' -print0)
printf 'JavaScript syntax passed: %d files.\n' "$JS_COUNT"

run_clean "$PYTHON_BIN" - <<'PY'
import json
from pathlib import Path
paths = sorted(Path('.').rglob('*.json'))
for path in paths:
    json.loads(path.read_text())
print(f'JSON validation passed: {len(paths)} files.')
PY

printf 'Running WordPress contract and functional tests...\n'
WP_TEST_COUNT=0
for test_file in tests/*.php; do TERM=dumb php "$test_file" >/dev/null; WP_TEST_COUNT=$((WP_TEST_COUNT + 1)); done
printf 'WordPress test files passed: %d.\n' "$WP_TEST_COUNT"

printf 'Creating isolated Python test environment...\n'
run_clean "$PYTHON_BIN" -m venv --copies "$TMP_DIR/venv"
VENV_PY="$TMP_DIR/venv/bin/python"
[[ -x "$VENV_PY" ]] || fail "The Python virtual environment was not created."
run_clean "$VENV_PY" -m pip install --quiet --upgrade pip
run_clean "$VENV_PY" -m pip install --quiet -r backend/requirements.txt
SC_RL_BACKEND_API_KEY=test-key SC_RL_DATA_DIR="$TMP_DIR/test-data-root" run_clean "$VENV_PY" -m pytest -q backend/tests
(
  cd backend
  SC_RL_BACKEND_API_KEY=test-key SC_RL_DATA_DIR="$TMP_DIR/test-data-backend" run_clean "$VENV_PY" -m pytest -q tests
)
run_clean "$VENV_PY" -m compileall -q backend/app backend/tests

printf 'Scanning for accidentally packaged secrets...\n'
if grep -RInE \
  --exclude-dir=.git --exclude-dir=.venv --exclude-dir=.pytest_cache --exclude-dir=__pycache__ \
  --exclude='*.pyc' --exclude='PUSH_RESEARCH_LIBRARIAN_*.sh' \
  '(BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{30,}|AIza[0-9A-Za-z_-]{30,})' .; then
  fail "Potential secret material was detected. Review the matches before pushing."
fi

bash -n PUSH_RESEARCH_LIBRARIAN_V720_PY312.sh
git add -A
if git diff --cached --quiet; then fail "No v7.2.0 changes were detected after extraction."; fi
git commit -m "Build Research Librarian v${RELEASE_VERSION}"
git tag -a "$RELEASE_TAG" -m "Research Librarian v${RELEASE_VERSION} — Library Object Model & Research Context Alignment"
git push origin main
git push origin "$RELEASE_TAG"

printf '\nResearch Librarian v%s validated and pushed successfully.\n' "$RELEASE_VERSION"
printf 'Render should auto-deploy main. Then update WordPress with the v7.2.0 WordPress package and verify a saved research context.\n'
