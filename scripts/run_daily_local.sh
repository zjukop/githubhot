#!/bin/bash

set -uo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOCK_DIR="${REPO_DIR}/.local/githubhot-daily.lock"

export PATH="${GITHUBHOT_BIN_DIR:+${GITHUBHOT_BIN_DIR}:}/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

log() {
  printf '%s [githubhot] %s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')" "$*"
}

retry() {
  local description="$1"
  shift
  local attempts="${GITHUBHOT_RETRY_ATTEMPTS:-3}"
  local delay="${GITHUBHOT_RETRY_DELAY_SECONDS:-60}"
  local attempt=1
  while (( attempt <= attempts )); do
    log "${description}: attempt ${attempt}/${attempts}"
    if "$@"; then
      return 0
    fi
    if (( attempt < attempts )); then
      log "${description}: failed; retrying in ${delay}s"
      sleep "${delay}"
      delay=$((delay * 2))
    fi
    attempt=$((attempt + 1))
  done
  log "${description}: failed after ${attempts} attempts"
  return 1
}

git_network() {
  local timeout_seconds="$1"
  shift
  if python3 "${REPO_DIR}/scripts/run_with_timeout.py" "${timeout_seconds}" git "$@"; then
    return 0
  fi

  local fallback_ip="${GITHUBHOT_GITHUB_FALLBACK_IP-140.82.112.4}"
  if [[ -z "${fallback_ip}" ]]; then
    return 1
  fi
  log "git $1: default GitHub route failed; trying verified HTTPS fallback ${fallback_ip}"
  python3 "${REPO_DIR}/scripts/run_with_timeout.py" "${timeout_seconds}" \
    git -c "http.curloptResolve=github.com:443:${fallback_ip}" "$@"
}

mkdir -p "${REPO_DIR}/.local"
if ! mkdir "${LOCK_DIR}" 2>/dev/null; then
  echo "Another GitHubHot daily run is already active."
  exit 0
fi
trap 'rmdir "${LOCK_DIR}"' EXIT

cd "${REPO_DIR}"
log "run started"

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Refusing to run with tracked local changes."
  exit 1
fi

GITHUB_TOKEN="$(gh auth token -h github.com)" || {
  log "GitHub CLI token is unavailable"
  exit 1
}
export GITHUB_TOKEN

DEEPSEEK_API_KEY="$(security find-generic-password -s githubhot -a DEEPSEEK_API_KEY -w)" || {
  log "DeepSeek key is unavailable"
  exit 1
}
export DEEPSEEK_API_KEY

git config user.name "githubhot-local[bot]"
git config user.email "zjukop@users.noreply.github.com"

GIT_TIMEOUT_SECONDS="${GITHUBHOT_GIT_TIMEOUT_SECONDS:-90}"
if ! retry "git pull" git_network "${GIT_TIMEOUT_SECONDS}" pull --ff-only origin main; then
  log "git pull unavailable; continuing with the clean local checkout"
fi

TODAY="$(date +%F)"
BACKFILL_LIMIT="${GITHUBHOT_BACKFILL_LIMIT:-7}"
PENDING_OUTPUT="$(python3 -m githubhot pending --date "${TODAY}" --limit "${BACKFILL_LIMIT}")" || {
  log "failed to calculate pending publication dates"
  exit 1
}
PENDING_DATES=()
while IFS= read -r PUBLISH_DATE; do
  [[ -n "${PUBLISH_DATE}" ]] && PENDING_DATES+=("${PUBLISH_DATE}")
done <<< "${PENDING_OUTPUT}"

if (( ${#PENDING_DATES[@]} == 0 )); then
  log "no missing daily publications"
fi

for PUBLISH_DATE in "${PENDING_DATES[@]}"; do
  log "${PUBLISH_DATE}: generation started"
  if ! retry "${PUBLISH_DATE}: scan" python3 -m githubhot scan \
    --date "${PUBLISH_DATE}" --days 30 --min-stars 100 --limit 50 --enrich 10 --analyze 10; then
    log "${PUBLISH_DATE}: scan failed; leaving the date pending"
    continue
  fi
  if ! python3 -m githubhot digest --date "${PUBLISH_DATE}" --top 10; then
    log "${PUBLISH_DATE}: digest failed; leaving the date pending"
    continue
  fi
  DAILY_PATH="daily/${PUBLISH_DATE:0:4}/${PUBLISH_DATE:5:2}/${PUBLISH_DATE}.md"
  if rg -n "TODO" "${DAILY_PATH}"; then
    log "${PUBLISH_DATE}: digest contains unfinished TODO markers"
    continue
  fi
  if ! python3 -m unittest discover -s tests -v; then
    log "${PUBLISH_DATE}: tests failed; refusing to commit"
    continue
  fi

  git add README.md daily deep-dives data/snapshots
  if git diff --cached --quiet; then
    log "${PUBLISH_DATE}: no Git changes to commit"
  elif git commit -m "daily: publish GitHubHot ${PUBLISH_DATE}"; then
    log "${PUBLISH_DATE}: local commit created"
  else
    log "${PUBLISH_DATE}: commit failed"
    git reset >/dev/null
    continue
  fi

  for SOCIAL_SECRET in WECHAT_APP_ID WECHAT_APP_SECRET; do
    if security find-generic-password -s githubhot-social -a "${SOCIAL_SECRET}" >/dev/null 2>&1; then
      SOCIAL_VALUE="$(security find-generic-password -s githubhot-social -a "${SOCIAL_SECRET}" -w)"
      export "${SOCIAL_SECRET}=${SOCIAL_VALUE}"
    fi
  done
  if ! python3 -m githubhot syndicate --date "${PUBLISH_DATE}" --publish-wechat-if-configured; then
    log "${PUBLISH_DATE}: social draft generation failed; Git publication is isolated"
  elif ! "${REPO_DIR}/scripts/run_social_browser_drafts.sh" "${PUBLISH_DATE}"; then
    log "${PUBLISH_DATE}: browser draft delivery failed; generated drafts remain local"
  fi

  if ! retry "${PUBLISH_DATE}: git push" git_network "${GIT_TIMEOUT_SECONDS}" push origin main; then
    log "${PUBLISH_DATE}: push remains pending; later dates and social drafts will continue"
  fi
done

if ! retry "final git push" git_network "${GIT_TIMEOUT_SECONDS}" push origin main; then
  log "run completed with Git commits still pending"
  exit 1
fi
log "run completed successfully"
