#!/usr/bin/env bash
#
# Copyright 2025 Google LLC All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# One-step setup for the Google Analytics MCP server on Claude Desktop (macOS).
#
# This installs every prerequisite, signs you in to Google, and wires the
# server into Claude Desktop's config — no manual JSON editing required.
#
# Usage:
#   bash scripts/setup-claude-desktop.sh
#   GA_MCP_PROJECT=my-gcp-project bash scripts/setup-claude-desktop.sh   # skip the project prompt

set -euo pipefail

# --- pretty logging -----------------------------------------------------------
if [ -t 1 ]; then
  C_BLUE=$'\033[0;34m'; C_GREEN=$'\033[0;32m'; C_YELLOW=$'\033[0;33m'
  C_RED=$'\033[0;31m'; C_BOLD=$'\033[1m'; C_OFF=$'\033[0m'
else
  C_BLUE=''; C_GREEN=''; C_YELLOW=''; C_RED=''; C_BOLD=''; C_OFF=''
fi
info() { printf '%s▶%s %s\n' "$C_BLUE" "$C_OFF" "$1"; }
ok()   { printf '%s✓%s %s\n' "$C_GREEN" "$C_OFF" "$1"; }
warn() { printf '%s!%s %s\n' "$C_YELLOW" "$C_OFF" "$1"; }
err()  { printf '%s✗%s %s\n' "$C_RED" "$C_OFF" "$1" >&2; }
step() { printf '\n%s%s%s\n' "$C_BOLD" "$1" "$C_OFF"; }

# Read user input from the terminal even when the script is piped in.
ask() {
  local __var="$1" __prompt="$2" __reply
  if [ -r /dev/tty ]; then
    read -r -p "$__prompt" __reply </dev/tty
  else
    read -r -p "$__prompt" __reply
  fi
  printf -v "$__var" '%s' "$__reply"
}

ANALYTICS_SCOPES="https://www.googleapis.com/auth/analytics.readonly,https://www.googleapis.com/auth/cloud-platform"
CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
ADC_PATH="$HOME/.config/gcloud/application_default_credentials.json"

printf '%s%s%s\n' "$C_BOLD" "Google Analytics MCP · Claude Desktop 설치" "$C_OFF"
echo "이 스크립트는 필요한 도구 설치 → Google 로그인 → Claude Desktop 연결까지 자동으로 진행합니다."

# --- 0. platform check --------------------------------------------------------
if [ "$(uname)" != "Darwin" ]; then
  err "이 스크립트는 macOS 전용입니다. (현재: $(uname))"
  exit 1
fi

# --- 1. Homebrew --------------------------------------------------------------
step "1/6 · 필수 도구 확인"
if ! command -v brew >/dev/null 2>&1; then
  err "Homebrew가 필요합니다. https://brew.sh 의 안내로 먼저 설치한 뒤 다시 실행하세요."
  exit 1
fi
ok "Homebrew 확인"

# --- 2. pipx ------------------------------------------------------------------
if ! command -v pipx >/dev/null 2>&1; then
  info "pipx 설치 중..."
  brew install pipx
  pipx ensurepath >/dev/null 2>&1 || true
fi
ok "pipx 확인"

# --- 3. Google Cloud SDK ------------------------------------------------------
if ! command -v gcloud >/dev/null 2>&1; then
  info "Google Cloud SDK 설치 중... (수 분 걸릴 수 있어요)"
  brew install --cask google-cloud-sdk
fi
command -v gcloud >/dev/null 2>&1 || {
  err "gcloud 설치 후에도 명령을 찾을 수 없습니다. 터미널을 새로 열고 다시 실행하세요."
  exit 1
}
ok "Google Cloud SDK 확인"

# --- 4. analytics-mcp server --------------------------------------------------
step "2/6 · Analytics MCP 서버 설치"
info "analytics-mcp 설치/업데이트 중..."
pipx install analytics-mcp >/dev/null 2>&1 || pipx upgrade analytics-mcp >/dev/null 2>&1 || true
BIN_DIR="$(pipx environment --value PIPX_BIN_DIR 2>/dev/null || echo "$HOME/.local/bin")"
MCP_BIN="$BIN_DIR/analytics-mcp"
if [ ! -x "$MCP_BIN" ]; then
  err "analytics-mcp 실행 파일을 찾을 수 없습니다: $MCP_BIN"
  err "'pipx install analytics-mcp' 를 직접 실행해 오류를 확인하세요."
  exit 1
fi
ok "서버 설치 완료 ($MCP_BIN)"

# --- 5. Google sign-in & project ---------------------------------------------
step "3/6 · Google 로그인"
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | grep -q .; then
  info "브라우저에서 Google 계정으로 로그인하세요 (GA 속성에 접근 권한이 있는 계정)."
  gcloud auth login
fi
ACTIVE_ACCOUNT="$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | head -1)"
ok "로그인됨: ${ACTIVE_ACCOUNT:-알 수 없음}"

step "4/6 · Google Cloud 프로젝트 선택"
PROJECT="${GA_MCP_PROJECT:-}"
if [ -z "$PROJECT" ]; then
  PROJECT="$(gcloud config get-value project 2>/dev/null || true)"
  [ "$PROJECT" = "(unset)" ] && PROJECT=""
fi
if [ -z "$PROJECT" ]; then
  echo "사용 가능한 프로젝트:"
  gcloud projects list --format="table(projectId, name)" 2>/dev/null || true
  echo ""
  ask PROJECT "사용할 프로젝트 ID를 입력하세요 (없으면 비워두고 Enter → 새로 생성): "
fi
if [ -z "$PROJECT" ]; then
  PROJECT="ga-mcp-$(date +%s)"
  info "새 프로젝트를 생성합니다: $PROJECT"
  gcloud projects create "$PROJECT" --name="GA MCP" 1>/dev/null
  warn "새 프로젝트에는 결제 계정 연결이 필요할 수 있습니다 (Data API 무료 할당량 범위 내라면 불필요)."
fi
gcloud config set project "$PROJECT" 1>/dev/null 2>&1 || true
ok "프로젝트: $PROJECT"

# --- 6. enable APIs -----------------------------------------------------------
# Only the project owner/editor can enable APIs. For a shared project, an admin
# enables them once; everyone else just needs them already on. So we check
# first and skip the enable call when they're active — letting users without
# the enable permission pass this step.
step "5/6 · 필요한 API 확인"
REQUIRED_APIS="analyticsadmin.googleapis.com analyticsdata.googleapis.com"
ENABLED_APIS="$(gcloud services list --enabled --project "$PROJECT" \
  --format="value(config.name)" 2>/dev/null || true)"
MISSING_APIS=""
for api in $REQUIRED_APIS; do
  if printf '%s\n' "$ENABLED_APIS" | grep -qx "$api"; then
    ok "$api (활성화됨)"
  else
    MISSING_APIS="$MISSING_APIS $api"
  fi
done
if [ -n "${MISSING_APIS# }" ]; then
  info "활성화 시도:${MISSING_APIS}"
  # shellcheck disable=SC2086
  if gcloud services enable $MISSING_APIS --project "$PROJECT" 2>/dev/null; then
    ok "API 활성화 완료"
  else
    warn "이 계정에는 '$PROJECT' 프로젝트의 API를 활성화할 권한이 없습니다."
    warn "관리자에게 아래 API 활성화를 한 번만 요청하세요:${MISSING_APIS}"
    warn "관리자가 켜두면 이 단계는 자동으로 통과합니다. 일단 계속 진행합니다."
  fi
fi

# --- 7. application default credentials ---------------------------------------
info "앱용 인증(ADC) 설정 — 브라우저에서 한 번 더 로그인하세요."
gcloud auth application-default login --scopes="$ANALYTICS_SCOPES"
gcloud auth application-default set-quota-project "$PROJECT" >/dev/null 2>&1 || \
  warn "quota project 설정을 건너뜁니다 ($PROJECT). 권한을 확인하세요."
if [ ! -f "$ADC_PATH" ]; then
  err "인증 정보 파일을 찾을 수 없습니다: $ADC_PATH"
  exit 1
fi
ok "인증 설정 완료"

# --- 8. wire into Claude Desktop ---------------------------------------------
step "6/6 · Claude Desktop 연결"
if [ -f "$CONFIG" ]; then
  cp "$CONFIG" "${CONFIG}.bak.$(date +%Y%m%d%H%M%S)"
  ok "기존 설정 백업 완료"
fi

MCP_BIN="$MCP_BIN" ADC_PATH="$ADC_PATH" PROJECT="$PROJECT" CONFIG="$CONFIG" \
python3 - <<'PY'
import json, os

cfg = os.environ["CONFIG"]
os.makedirs(os.path.dirname(cfg), exist_ok=True)

data = {}
if os.path.exists(cfg):
    try:
        with open(cfg, "r") as f:
            data = json.load(f)
    except Exception:
        data = {}

data.setdefault("mcpServers", {})
data["mcpServers"]["analytics-mcp"] = {
    "command": os.environ["MCP_BIN"],
    "args": [],
    "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": os.environ["ADC_PATH"],
        "GOOGLE_CLOUD_PROJECT": os.environ["PROJECT"],
    },
}

with open(cfg, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PY
ok "Claude Desktop 설정에 analytics-mcp 추가 완료"

# --- done ---------------------------------------------------------------------
printf '\n%s설치가 끝났습니다 🎉%s\n' "$C_GREEN$C_BOLD" "$C_OFF"
echo "다음 단계:"
echo "  1. Claude Desktop을 완전히 종료했다가 다시 실행하세요."
echo "  2. 새 대화에서 이렇게 물어보세요:  내 Google Analytics 속성 목록을 보여줘"
echo ""
echo "문제가 있으면 Claude Desktop 설정 파일을 확인하세요:"
echo "  $CONFIG"
