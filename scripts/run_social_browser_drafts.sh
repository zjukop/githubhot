#!/bin/bash

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SOCIAL_DATE="${1:-$(date +%F)}"
DEBUG_ENDPOINT="${CHROME_DEBUG_ENDPOINT:-http://[::1]:9222}"
PROFILE_DIR="${GITHUBHOT_SOCIAL_PROFILE:-${HOME}/.local/share/githubhot-social-browser}"
CHROME_APP="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

if ! curl --noproxy '*' -g -fsS "${DEBUG_ENDPOINT}/json/version" >/dev/null 2>&1; then
  if [[ ! -x "${CHROME_APP}" ]]; then
    echo "Google Chrome was not found at ${CHROME_APP}." >&2
    exit 1
  fi
  mkdir -p "${PROFILE_DIR}"
  "${CHROME_APP}" \
    --remote-debugging-port=9222 \
    --user-data-dir="${PROFILE_DIR}" \
    --no-first-run \
    --no-default-browser-check \
    "about:blank" >/dev/null 2>&1 &
  for _ in {1..30}; do
    curl --noproxy '*' -g -fsS "${DEBUG_ENDPOINT}/json/version" >/dev/null 2>&1 && break
    sleep 1
  done
fi

curl --noproxy '*' -g -fsS "${DEBUG_ENDPOINT}/json/version" >/dev/null
cd "${REPO_DIR}"
CHROME_DEBUG_ENDPOINT="${DEBUG_ENDPOINT}" node "scripts/save_browser_drafts.mjs" ".local/social-drafts" "${SOCIAL_DATE}"
