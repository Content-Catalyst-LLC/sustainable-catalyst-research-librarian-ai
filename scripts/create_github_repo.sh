#!/usr/bin/env bash
set -euo pipefail

# Optional GitHub repo creation script for the Sustainable Catalyst Research Librarian AI plugin.
# Requirements: git, GitHub CLI (`gh`), authenticated `gh auth login` session.
# Run from the root of this plugin project.

ORG="${GITHUB_ORG:-Content-Catalyst-LLC}"
REPO="${GITHUB_REPO:-sustainable-catalyst-research-librarian-ai}"
VISIBILITY="${GITHUB_VISIBILITY:-public}" # public or private
REMOTE_URL="git@github.com:${ORG}/${REPO}.git"

if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI is required. Install gh and run gh auth login." >&2
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  echo "git is required." >&2
  exit 1
fi

if [[ ! -f "sustainable-catalyst-research-librarian-ai.php" ]]; then
  echo "Run this script from the plugin root directory." >&2
  exit 1
fi

if [[ ! -d .git ]]; then
  git init
fi

git add .
git commit -m "Initial Sustainable Catalyst Research Librarian AI plugin" || true

git branch -M main

if gh repo view "${ORG}/${REPO}" >/dev/null 2>&1; then
  echo "Repository already exists: ${ORG}/${REPO}"
else
  if [[ "${VISIBILITY}" == "private" ]]; then
    gh repo create "${ORG}/${REPO}" --private --description "AI-enabled Sustainable Catalyst Research Librarian WordPress plugin" --source=. --remote=origin --push
  else
    gh repo create "${ORG}/${REPO}" --public --description "AI-enabled Sustainable Catalyst Research Librarian WordPress plugin" --source=. --remote=origin --push
  fi
  exit 0
fi

if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "${REMOTE_URL}"
else
  git remote add origin "${REMOTE_URL}"
fi

git push -u origin main
