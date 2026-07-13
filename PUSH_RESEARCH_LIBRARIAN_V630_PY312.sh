#!/usr/bin/env bash
set -Eeuo pipefail

RELEASE_VERSION="6.3.0"
RELEASE_TAG="v${RELEASE_VERSION}"
SCRIPT_REVISION="v630-py312-sqlite-r1"
REPO_URL="git@github.com:Content-Catalyst-LLC/sustainable-catalyst-research-librarian-ai.git"
ZIP_PATH="${1:-$HOME/Downloads/sustainable-catalyst-research-librarian-ai-v6.3.0.zip}"
REPO_DIR="${2:-$HOME/Downloads/sustainable-catalyst-research-librarian-ai-repo-v630-clean}"

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

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/sc-rl-v630.XXXXXX")"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

unzip -q "$ZIP_PATH" -d "$TMP_DIR/release"
SOURCE_DIR="$TMP_DIR/release/sustainable-catalyst-research-librarian-ai"
[[ -f "$SOURCE_DIR/sustainable-catalyst-research-librarian-ai.php" ]] || fail "The ZIP does not contain the expected plugin folder."
[[ -f "$SOURCE_DIR/backend/app/store.py" ]] || fail "The package does not contain the durable SQLite backend."
[[ -f "$SOURCE_DIR/pytest.ini" ]] || fail "The package does not contain repository-root pytest configuration."
grep -q 'Version: 6.3.0' "$SOURCE_DIR/sustainable-catalyst-research-librarian-ai.php" || fail "The package version marker is not 6.3.0."
grep -q 'SCHEMA_VERSION = 3' "$SOURCE_DIR/backend/app/store.py" || fail "The package does not declare SQLite schema version 3."

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
run_clean "$VENV_PY" -m pytest -q
printf 'Running backend tests from backend/ to validate deployment imports...\n'
(
  cd backend
  run_clean "$VENV_PY" -m pytest -q tests
)

printf 'Running Python compile validation...\n'
run_clean "$VENV_PY" -m compileall -q backend/app backend/tests

printf 'Running push-safe secret scan...\n'
if grep -RInE \
  --exclude-dir=.git --exclude-dir=.venv --exclude-dir=.pytest_cache --exclude-dir=__pycache__ \
  --exclude='*.pyc' --exclude='PUSH_RESEARCH_LIBRARIAN_V630_PY312.sh' \
  '(BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{30,}|AIza[0-9A-Za-z_-]{30,})' .; then
  fail "Potential secret material was detected. Review the matches before pushing."
fi

printf 'Committing and tagging v%s...\n' "$RELEASE_VERSION"
git add -A
if git diff --cached --quiet; then
  fail "No release changes were detected after extraction."
fi
git commit -m "Build Research Librarian v${RELEASE_VERSION}"
git tag -a "$RELEASE_TAG" -m "Research Librarian v${RELEASE_VERSION} — Durable Knowledge Index, Sync Ledger, and Recovery"

echo "Pushing main and $RELEASE_TAG..."
git push origin main
git push origin "$RELEASE_TAG"

printf '\nResearch Librarian v%s was validated and pushed successfully.\n' "$RELEASE_VERSION"
