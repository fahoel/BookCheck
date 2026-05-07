#!/usr/bin/env bash
# sync.sh – Termux helper: commit and push all changes to the remote repo.
# Usage: bash sync.sh [commit message]
set -e
MSG="${1:-Add new book}"
git add .
git commit -m "$MSG"
git push
