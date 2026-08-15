#!/bin/bash

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOCK_DIR="${REPO_DIR}/.local/githubhot-daily.lock"

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

mkdir -p "${REPO_DIR}/.local"
if ! mkdir "${LOCK_DIR}" 2>/dev/null; then
  echo "Another GitHubHot daily run is already active."
  exit 0
fi
trap 'rmdir "${LOCK_DIR}"' EXIT

cd "${REPO_DIR}"

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Refusing to run with tracked local changes."
  exit 1
fi

GITHUB_TOKEN="$(gh auth token -h github.com)"
export GITHUB_TOKEN

DEEPSEEK_API_KEY="$(security find-generic-password -s githubhot -a DEEPSEEK_API_KEY -w)"
export DEEPSEEK_API_KEY

git pull --ff-only origin main
python3 -m githubhot scan --days 30 --min-stars 100 --limit 50 --enrich 10 --analyze 10
python3 -m githubhot digest --top 10
python3 -m unittest discover -s tests -v

TODAY="$(date +%F)"
if rg -n "TODO" "daily/$(date +%Y)/$(date +%m)/${TODAY}.md"; then
  echo "Generated digest contains unfinished TODO markers."
  exit 1
fi

git config user.name "githubhot-local[bot]"
git config user.email "zjukop@users.noreply.github.com"
git add README.md daily deep-dives data/snapshots

if git diff --cached --quiet; then
  echo "No daily changes to publish."
  exit 0
fi

git commit -m "daily: publish GitHubHot ${TODAY}"
git push origin main

for SOCIAL_SECRET in WECHAT_APP_ID WECHAT_APP_SECRET; do
  if security find-generic-password -s githubhot-social -a "${SOCIAL_SECRET}" >/dev/null 2>&1; then
    SOCIAL_VALUE="$(security find-generic-password -s githubhot-social -a "${SOCIAL_SECRET}" -w)"
    export "${SOCIAL_SECRET}=${SOCIAL_VALUE}"
  fi
done

if ! python3 -m githubhot syndicate --date "${TODAY}" --publish-wechat-if-configured; then
  echo "Social draft syndication failed; GitHubHot daily publication remains successful." >&2
fi

if ! "${REPO_DIR}/scripts/run_social_browser_drafts.sh" "${TODAY}"; then
  echo "Browser draft delivery failed; local social drafts remain available for review." >&2
fi
