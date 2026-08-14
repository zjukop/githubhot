#!/bin/bash

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
AGENT_LABEL="com.zjukop.githubhot.daily"
AGENT_FILE="${HOME}/Library/LaunchAgents/${AGENT_LABEL}.plist"
LOG_DIR="${REPO_DIR}/.local/logs"

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

if ! gh auth status -h github.com >/dev/null 2>&1; then
  echo "GitHub CLI authentication is invalid. Run: gh auth login -h github.com"
  exit 1
fi

if ! security find-generic-password -s githubhot -a DEEPSEEK_API_KEY >/dev/null 2>&1; then
  read -r -s -p "DeepSeek API Key: " DEEPSEEK_KEY
  echo
  security add-generic-password -U -s githubhot -a DEEPSEEK_API_KEY -w "${DEEPSEEK_KEY}"
  unset DEEPSEEK_KEY
fi

mkdir -p "${HOME}/Library/LaunchAgents" "${LOG_DIR}"

sed \
  -e "s|__REPO_DIR__|${REPO_DIR}|g" \
  -e "s|__LOG_DIR__|${LOG_DIR}|g" \
  "${REPO_DIR}/scripts/com.zjukop.githubhot.daily.plist.template" > "${AGENT_FILE}"

launchctl bootout "gui/$(id -u)" "${AGENT_FILE}" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "${AGENT_FILE}"
launchctl enable "gui/$(id -u)/${AGENT_LABEL}"

echo "Installed ${AGENT_LABEL}; it runs every day at 10:00 local time."
echo "Logs: ${LOG_DIR}/daily.stdout.log and ${LOG_DIR}/daily.stderr.log"
