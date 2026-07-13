#!/usr/bin/env bash
set -Eeuo pipefail

RELEASE_VERSION="6.2.1"
RELEASE_TAG="v${RELEASE_VERSION}"
REPO_URL="git@github.com:Content-Catalyst-LLC/sustainable-catalyst-research-librarian-ai.git"
ZIP_PATH="${1:-$HOME/Downloads/sustainable-catalyst-research-librarian-ai-v6.2.1.zip}"
REPO_DIR="${2:-$HOME/Downloads/sustainable-catalyst-research-librarian-ai-repo}"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

command -v git >/dev/null 2>&1 || fail "git is required."
command -v unzip >/dev/null 2>&1 || fail "unzip is required."
command -v rsync >/dev/null 2>&1 || fail "rsync is required."
command -v php >/dev/null 2>&1 || fail "PHP is required for release validation."
command -v python3 >/dev/null 2>&1 || fail "Python 3 is required for release validation."
command -v node >/dev/null 2>&1 || fail "Node.js is required for JavaScript validation."
[[ -f "$ZIP_PATH" ]] || fail "Release ZIP not found: $ZIP_PATH"

echo "Checking GitHub SSH authentication..."
SSH_OUTPUT="$(ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -T git@github.com 2>&1 || true)"
grep -qi "successfully authenticated" <<<"$SSH_OUTPUT" \
  || fail "GitHub SSH authentication is not ready. Run: ssh -T git@github.com"

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/sc-rl-v621.XXXXXX")"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

unzip -q "$ZIP_PATH" -d "$TMP_DIR/release"
SOURCE_DIR="$TMP_DIR/release/sustainable-catalyst-research-librarian-ai"
[[ -f "$SOURCE_DIR/sustainable-catalyst-research-librarian-ai.php" ]] \
  || fail "The ZIP does not contain the expected plugin folder."

grep -q 'Version: 6.2.1' "$SOURCE_DIR/sustainable-catalyst-research-librarian-ai.php" \
  || fail "The package version marker is not 6.2.1."

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
  fail "The repository has uncommitted changes. Commit or stash them before running this release script."
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
  "$SOURCE_DIR/" "$REPO_DIR/"

printf '\nValidating PHP syntax...\n'
while IFS= read -r -d '' file; do php -l "$file" >/dev/null; done < <(find . -type f -name '*.php' -print0)

printf 'Validating JavaScript syntax...\n'
while IFS= read -r -d '' file; do node --check "$file"; done < <(find assets -type f -name '*.js' -print0)

printf 'Validating JSON files...\n'
python3 - <<'PY'
import json
from pathlib import Path
for path in Path('.').rglob('*.json'):
    json.loads(path.read_text())
print('JSON validation passed.')
PY

printf 'Running WordPress release contract tests...\n'
for test_file in tests/*.php; do php "$test_file" >/dev/null; done

printf 'Creating isolated Python test environment...\n'
python3 -m venv "$TMP_DIR/venv"
"$TMP_DIR/venv/bin/python" -m pip install --quiet --upgrade pip
"$TMP_DIR/venv/bin/python" -m pip install --quiet -r backend/requirements.txt
"$TMP_DIR/venv/bin/python" -m pytest -q backend/tests

printf 'Running push-safe secret scan...\n'
if grep -RInE \
  --exclude-dir=.git --exclude-dir=.venv --exclude-dir=__pycache__ \
  --exclude='*.pyc' --exclude='PUSH_RESEARCH_LIBRARIAN_V621.sh' \
  '(BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{30,}|AIza[0-9A-Za-z_-]{30,})' .; then
  fail "Potential secret material was detected. Review the matches before pushing."
fi

printf 'Committing and tagging v%s...\n' "$RELEASE_VERSION"
git add -A
if git diff --cached --quiet; then
  fail "No release changes were detected after extraction."
fi
git commit -m "Build Research Librarian v${RELEASE_VERSION}"
git tag -a "$RELEASE_TAG" -m "Research Librarian v${RELEASE_VERSION} — WordPress Indexing and Endpoint Reliability Patch"

echo "Pushing main and $RELEASE_TAG..."
git push origin main
git push origin "$RELEASE_TAG"

printf '\nResearch Librarian v%s was validated and pushed successfully.\n' "$RELEASE_VERSION"
