#!/bin/bash

set -euo pipefail

read -r -p "WeChat Official Account AppID: " WECHAT_APP_ID
read -r -s -p "WeChat Official Account AppSecret: " WECHAT_APP_SECRET
echo

security add-generic-password -U -s githubhot-social -a WECHAT_APP_ID -w "${WECHAT_APP_ID}" >/dev/null
security add-generic-password -U -s githubhot-social -a WECHAT_APP_SECRET -w "${WECHAT_APP_SECRET}" >/dev/null

echo "WeChat credentials saved. The V3 cyber-carpenter cover will be uploaded automatically on the first draft run."
