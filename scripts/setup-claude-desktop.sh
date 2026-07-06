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
# One-step setup for the Google Analytics MCP server on macOS, targeting
# Claude Desktop and/or the Claude Code CLI, with an optional Google Ads MCP
# server (read-only, official googleads/google-ads-mcp).
#
# No Homebrew required. Uses `uv` (which also manages Python) to install and run
# the server, installs the Google Cloud SDK if missing, signs you in to Google,
# enables the required APIs, and wires the server into your chosen clients.
#
# Usage:
#   bash scripts/setup-claude-desktop.sh
#   GA_MCP_PROJECT=my-gcp-project bash scripts/setup-claude-desktop.sh   # skip the project prompt
#   GA_MCP_TARGETS=desktop,cli bash scripts/setup-claude-desktop.sh
#     # skip the target picker (values: desktop, cli — comma-separated)
#   GA_MCP_WITH_ADS=1 GA_MCP_ADS_DEV_TOKEN=xxx bash scripts/setup-claude-desktop.sh
#     # also set up Google Ads MCP without prompts
#     # (optional: GA_MCP_ADS_LOGIN_CUSTOMER_ID for access via a manager/MCC account)

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

# Interactive checkbox selector driven from /dev/tty.
# Caller sets CHECK_ITEMS (labels) and CHECK_STATE (0/1 defaults), same length.
# ↑/↓ (or k/j) move, space toggles, Enter confirms. Updates CHECK_STATE in place.
choose_checkbox() {
  local prompt="$1" n=${#CHECK_ITEMS[@]} cur=0 key rest i mark pointer first=1
  printf '%s\n' "$prompt" >/dev/tty
  printf '  (↑/↓ 이동, space 토글, Enter 확정)\n' >/dev/tty
  while true; do
    if [ "$first" = "1" ]; then first=0; else printf '\033[%dA' "$n" >/dev/tty; fi
    for i in $(seq 0 $((n - 1))); do
      mark=' '; [ "${CHECK_STATE[$i]}" = "1" ] && mark='x'
      pointer='  '; [ "$i" = "$cur" ] && pointer='> '
      printf '\r\033[K%s[%s] %s\n' "$pointer" "$mark" "${CHECK_ITEMS[$i]}" >/dev/tty
    done
    IFS= read -rsn1 key </dev/tty
    case "$key" in
      '') break ;;
      ' ') CHECK_STATE[cur]=$([ "${CHECK_STATE[cur]}" = "1" ] && echo 0 || echo 1) ;;
      $'\033')
        IFS= read -rsn2 -t 0.01 rest </dev/tty || true
        case "$rest" in
          '[A') cur=$(((cur - 1 + n) % n)) ;;
          '[B') cur=$(((cur + 1) % n)) ;;
        esac
        ;;
      k|K) cur=$(((cur - 1 + n) % n)) ;;
      j|J) cur=$(((cur + 1) % n)) ;;
    esac
  done
}

ANALYTICS_SCOPES="https://www.googleapis.com/auth/analytics.readonly,https://www.googleapis.com/auth/cloud-platform"
ADWORDS_SCOPE="https://www.googleapis.com/auth/adwords"
CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
ADC_PATH="$HOME/.config/gcloud/application_default_credentials.json"

printf '%s%s%s\n' "$C_BOLD" "Google Analytics MCP · Claude Desktop 설치" "$C_OFF"
echo "필요한 도구 설치 → Google 로그인 → Claude Desktop 연결까지 자동으로 진행합니다."
echo "(Homebrew 없이 동작합니다)"

# --- 0. platform check --------------------------------------------------------
if [ "$(uname)" != "Darwin" ]; then
  err "이 스크립트는 macOS 전용입니다. (현재: $(uname))"
  exit 1
fi

# --- target selection ---------------------------------------------------------
# Where to install the MCP server(s): Claude Desktop, the Claude Code CLI, or both.
TARGET_DESKTOP=0
TARGET_CLI=0
if [ -n "${GA_MCP_TARGETS:-}" ]; then
  case ",$GA_MCP_TARGETS," in *,desktop,*) TARGET_DESKTOP=1 ;; esac
  case ",$GA_MCP_TARGETS," in *,cli,*) TARGET_CLI=1 ;; esac
elif [ -r /dev/tty ]; then
  echo ""
  CHECK_ITEMS=("Claude Desktop" "Claude Code CLI")
  CHECK_STATE=(1 0)
  choose_checkbox "설치할 대상을 선택하세요:"
  TARGET_DESKTOP="${CHECK_STATE[0]}"
  TARGET_CLI="${CHECK_STATE[1]}"
else
  TARGET_DESKTOP=1
fi
if [ "$TARGET_DESKTOP" = "0" ] && [ "$TARGET_CLI" = "0" ]; then
  err "설치 대상이 선택되지 않았습니다."
  exit 1
fi

# Claude Code CLI needs the `claude` binary. Skip that target if it's missing.
CLAUDE_BIN=""
if [ "$TARGET_CLI" = "1" ]; then
  CLAUDE_BIN="$(command -v claude || true)"
  if [ -z "$CLAUDE_BIN" ]; then
    warn "'claude' CLI를 찾을 수 없어 Claude Code CLI 설정을 건너뜁니다."
    warn "설치: https://claude.ai/download  또는  npm i -g @anthropic-ai/claude-code"
    TARGET_CLI=0
  fi
fi
if [ "$TARGET_DESKTOP" = "0" ] && [ "$TARGET_CLI" = "0" ]; then
  err "설정할 대상이 없습니다."
  exit 1
fi

# --- optional: Google Ads MCP ---------------------------------------------------
# The official google-ads-mcp server is read-only. It needs a developer token,
# which can only be issued manually in the Google Ads API Center — so we ask.
WITH_ADS=0
ADS_DEV_TOKEN="${GA_MCP_ADS_DEV_TOKEN:-}"
ADS_LOGIN_CUSTOMER_ID="${GA_MCP_ADS_LOGIN_CUSTOMER_ID:-}"
if [ "${GA_MCP_WITH_ADS:-}" = "1" ]; then
  WITH_ADS=1
else
  echo ""
  ask ADS_REPLY "Google Ads MCP도 함께 연결할까요? (읽기 전용, developer token 필요) [y/N]: "
  case "$ADS_REPLY" in
    [yY]*) WITH_ADS=1 ;;
  esac
fi
if [ "$WITH_ADS" = "1" ] && [ -z "$ADS_DEV_TOKEN" ]; then
  echo ""
  info "Google Ads developer token이 필요합니다."
  echo "  발급 위치: Google Ads 관리자 계정(MCC) → API 센터"
  echo "  https://ads.google.com/aw/apicenter"
  echo "  (Explorer access 수준이면 대부분 즉시 자동 승인됩니다)"
  ask ADS_DEV_TOKEN "developer token을 붙여넣으세요 (건너뛰려면 Enter): "
  if [ -z "$ADS_DEV_TOKEN" ]; then
    warn "developer token이 없어 Google Ads 설정을 건너뜁니다. 발급 후 스크립트를 다시 실행하세요."
    WITH_ADS=0
  fi
fi
if [ "$WITH_ADS" = "1" ] && [ -z "$ADS_LOGIN_CUSTOMER_ID" ]; then
  ask ADS_LOGIN_CUSTOMER_ID "MCC(관리자 계정)를 통해 접근한다면 관리자 고객 ID를 입력하세요 (직접 접근이면 Enter): "
fi
ADS_LOGIN_CUSTOMER_ID="${ADS_LOGIN_CUSTOMER_ID//-/}"

# --- 1. uv (also provides Python) --------------------------------------------
step "1/6 · 실행 도구 준비 (uv)"
if ! command -v uv >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/uv" ]; then
  info "uv 설치 중... (관리자 암호 불필요)"
  curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1 || true
fi
UV="$(command -v uv 2>/dev/null || true)"
[ -n "$UV" ] || UV="$HOME/.local/bin/uv"
if [ ! -x "$UV" ]; then
  err "uv 설치에 실패했습니다. 인터넷 연결을 확인하고 다시 실행하세요."
  exit 1
fi
ok "uv 준비 완료 ($UV)"

# --- 2. Google Cloud SDK ------------------------------------------------------
step "2/6 · Google Cloud SDK 준비"
if command -v gcloud >/dev/null 2>&1; then
  GCLOUD="$(command -v gcloud)"
elif [ -x "$HOME/google-cloud-sdk/bin/gcloud" ]; then
  GCLOUD="$HOME/google-cloud-sdk/bin/gcloud"
else
  info "Google Cloud SDK 설치 중... (수 분 걸릴 수 있어요, 관리자 암호 불필요)"
  curl -fsSL https://sdk.cloud.google.com -o /tmp/ga-mcp-gcloud-install.sh
  bash /tmp/ga-mcp-gcloud-install.sh --disable-prompts --install-dir="$HOME" >/dev/null 2>&1 || true
  GCLOUD="$HOME/google-cloud-sdk/bin/gcloud"
fi
if [ ! -x "$GCLOUD" ] && ! command -v gcloud >/dev/null 2>&1; then
  err "Google Cloud SDK 설치에 실패했습니다."
  err "https://cloud.google.com/sdk/docs/install 의 안내로 설치 후 다시 실행하세요."
  exit 1
fi
ok "Google Cloud SDK 준비 완료 ($GCLOUD)"

# gcloud는 Python 3.10–3.14가 필요한데 시스템 python3가 더 낮으면 실패한다.
# 현재 gcloud가 못 도는 경우에만 uv로 호환 Python을 확보해 지정한다.
if ! CLOUDSDK_CORE_DISABLE_PROMPTS=1 "$GCLOUD" version >/dev/null 2>&1; then
  info "gcloud 실행용 Python 준비 중... (uv가 자동 설치)"
  "$UV" python install 3.12 >/dev/null 2>&1 || true
  CLOUDSDK_PYTHON="$("$UV" python find 3.12 2>/dev/null || true)"
  export CLOUDSDK_PYTHON
  [ -n "$CLOUDSDK_PYTHON" ] && ok "gcloud Python: $CLOUDSDK_PYTHON"
fi

# --- 3. MCP servers (via uv) ---------------------------------------------------
step "3/6 · MCP 서버 설치"
info "analytics-mcp 설치/업데이트 중... (uv가 Python까지 자동 준비)"
"$UV" tool install analytics-mcp --quiet 2>/dev/null \
  || "$UV" tool upgrade analytics-mcp --quiet 2>/dev/null || true
MCP_BIN="$HOME/.local/bin/analytics-mcp"
if [ ! -x "$MCP_BIN" ]; then
  MCP_BIN="$(command -v analytics-mcp 2>/dev/null || true)"
fi
if [ -z "$MCP_BIN" ] || [ ! -x "$MCP_BIN" ]; then
  err "analytics-mcp 실행 파일을 찾을 수 없습니다."
  err "'$UV tool install analytics-mcp' 를 직접 실행해 오류를 확인하세요."
  exit 1
fi
ok "Analytics 서버 설치 완료 ($MCP_BIN)"

ADS_MCP_BIN=""
if [ "$WITH_ADS" = "1" ]; then
  info "google-ads-mcp 설치/업데이트 중..."
  "$UV" tool install google-ads-mcp --quiet 2>/dev/null \
    || "$UV" tool upgrade google-ads-mcp --quiet 2>/dev/null || true
  ADS_MCP_BIN="$HOME/.local/bin/google-ads-mcp"
  if [ ! -x "$ADS_MCP_BIN" ]; then
    ADS_MCP_BIN="$(command -v google-ads-mcp 2>/dev/null || true)"
  fi
  if [ -z "$ADS_MCP_BIN" ] || [ ! -x "$ADS_MCP_BIN" ]; then
    err "google-ads-mcp 실행 파일을 찾을 수 없습니다."
    err "'$UV tool install google-ads-mcp' 를 직접 실행해 오류를 확인하세요."
    exit 1
  fi
  ok "Ads 서버 설치 완료 ($ADS_MCP_BIN)"
fi

# --- 4. Google sign-in & project ---------------------------------------------
step "4/6 · Google 로그인 & 프로젝트"
if ! "$GCLOUD" auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | grep -q .; then
  info "브라우저에서 Google 계정으로 로그인하세요 (GA 속성에 접근 권한이 있는 계정)."
  "$GCLOUD" auth login
fi
ACTIVE_ACCOUNT="$("$GCLOUD" auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | head -1)"
ok "로그인됨: ${ACTIVE_ACCOUNT:-알 수 없음}"

PROJECT="${GA_MCP_PROJECT:-}"
if [ -z "$PROJECT" ]; then
  PROJECT="$("$GCLOUD" config get-value project 2>/dev/null || true)"
  [ "$PROJECT" = "(unset)" ] && PROJECT=""
fi
if [ -z "$PROJECT" ]; then
  echo "사용 가능한 프로젝트:"
  "$GCLOUD" projects list --format="table(projectId, name)" 2>/dev/null || true
  echo ""
  ask PROJECT "사용할 프로젝트 ID를 입력하세요 (없으면 비워두고 Enter → 새로 생성): "
fi
if [ -z "$PROJECT" ]; then
  PROJECT="ga-mcp-$(date +%s)"
  info "새 프로젝트를 생성합니다: $PROJECT"
  "$GCLOUD" projects create "$PROJECT" --name="GA MCP" 1>/dev/null
  warn "새 프로젝트에는 결제 계정 연결이 필요할 수 있습니다 (Data API 무료 할당량 범위 내라면 불필요)."
fi
"$GCLOUD" config set project "$PROJECT" 1>/dev/null 2>&1 || true
ok "프로젝트: $PROJECT"

# --- 5. enable APIs (skip when already active) -------------------------------
# Only the project owner/editor can enable APIs. For a shared project, an admin
# enables them once; everyone else just needs them already on. So we check
# first and skip the enable call when they're active — letting users without
# the enable permission pass this step.
step "5/6 · 필요한 API 확인"
REQUIRED_APIS="analyticsadmin.googleapis.com analyticsdata.googleapis.com"
[ "$WITH_ADS" = "1" ] && REQUIRED_APIS="$REQUIRED_APIS googleads.googleapis.com"
ENABLED_APIS="$("$GCLOUD" services list --enabled --project "$PROJECT" \
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
  if "$GCLOUD" services enable $MISSING_APIS --project "$PROJECT" 2>/dev/null; then
    ok "API 활성화 완료"
  else
    warn "이 계정에는 '$PROJECT' 프로젝트의 API를 활성화할 권한이 없습니다."
    warn "관리자에게 아래 API 활성화를 한 번만 요청하세요:${MISSING_APIS}"
    warn "관리자가 켜두면 이 단계는 자동으로 통과합니다. 일단 계속 진행합니다."
  fi
fi

# --- 6. application default credentials + wire into the selected clients ------
step "6/6 · 인증 & MCP 연결"
info "앱용 인증(ADC) 설정 — 브라우저에서 한 번 더 로그인하세요."
# ADC login overwrites the credentials file, so both servers share one ADC —
# request the union of scopes in a single login.
ADC_SCOPES="$ANALYTICS_SCOPES"
[ "$WITH_ADS" = "1" ] && ADC_SCOPES="$ADC_SCOPES,$ADWORDS_SCOPE"
"$GCLOUD" auth application-default login --scopes="$ADC_SCOPES"
"$GCLOUD" auth application-default set-quota-project "$PROJECT" >/dev/null 2>&1 || \
  warn "quota project 설정을 건너뜁니다 ($PROJECT). 권한을 확인하세요."
if [ ! -f "$ADC_PATH" ]; then
  err "인증 정보 파일을 찾을 수 없습니다: $ADC_PATH"
  exit 1
fi
ok "인증 설정 완료"

# Build the server definitions once; every selected client reuses them.
SERVERS_JSON="$(mktemp)"
trap 'rm -f "$SERVERS_JSON"' EXIT
MCP_BIN="$MCP_BIN" ADC_PATH="$ADC_PATH" PROJECT="$PROJECT" \
WITH_ADS="$WITH_ADS" ADS_MCP_BIN="$ADS_MCP_BIN" ADS_DEV_TOKEN="$ADS_DEV_TOKEN" \
ADS_LOGIN_CUSTOMER_ID="$ADS_LOGIN_CUSTOMER_ID" SERVERS_JSON="$SERVERS_JSON" \
"$UV" run --no-project python - <<'PY'
import json, os

servers = {}
servers["analytics-mcp"] = {
    "command": os.environ["MCP_BIN"],
    "args": [],
    "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": os.environ["ADC_PATH"],
        "GOOGLE_CLOUD_PROJECT": os.environ["PROJECT"],
    },
}

if os.environ.get("WITH_ADS") == "1":
    ads_env = {
        "GOOGLE_APPLICATION_CREDENTIALS": os.environ["ADC_PATH"],
        "GOOGLE_PROJECT_ID": os.environ["PROJECT"],
        "GOOGLE_ADS_DEVELOPER_TOKEN": os.environ["ADS_DEV_TOKEN"],
    }
    if os.environ.get("ADS_LOGIN_CUSTOMER_ID"):
        ads_env["GOOGLE_ADS_LOGIN_CUSTOMER_ID"] = os.environ["ADS_LOGIN_CUSTOMER_ID"]
    servers["google-ads-mcp"] = {
        "command": os.environ["ADS_MCP_BIN"],
        "args": [],
        "env": ads_env,
    }

with open(os.environ["SERVERS_JSON"], "w") as f:
    json.dump(servers, f)
PY

SERVER_NAMES="analytics-mcp"
[ "$WITH_ADS" = "1" ] && SERVER_NAMES="analytics-mcp, google-ads-mcp"

# Claude Desktop: merge the servers into its config JSON.
if [ "$TARGET_DESKTOP" = "1" ]; then
  if [ -f "$CONFIG" ]; then
    cp "$CONFIG" "${CONFIG}.bak.$(date +%Y%m%d%H%M%S)"
    ok "기존 Claude Desktop 설정 백업 완료"
  fi
  CONFIG="$CONFIG" SERVERS_JSON="$SERVERS_JSON" \
  "$UV" run --no-project python - <<'PY'
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

with open(os.environ["SERVERS_JSON"], "r") as f:
    servers = json.load(f)

data.setdefault("mcpServers", {}).update(servers)

with open(cfg, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PY
  ok "Claude Desktop 설정에 $SERVER_NAMES 추가 완료"
fi

# Claude Code CLI: register each server at user scope (remove-then-add to overwrite).
if [ "$TARGET_CLI" = "1" ]; then
  while IFS=$'\t' read -r name cfgjson; do
    [ -z "$name" ] && continue
    "$CLAUDE_BIN" mcp remove -s user "$name" >/dev/null 2>&1 || true
    if "$CLAUDE_BIN" mcp add-json -s user "$name" "$cfgjson" >/dev/null 2>&1; then
      ok "Claude Code CLI에 $name 추가 완료 (user 스코프)"
    else
      err "Claude Code CLI에 $name 추가 실패 — 'claude mcp add-json -s user $name ...'를 직접 실행해 확인하세요."
    fi
  done < <(SERVERS_JSON="$SERVERS_JSON" "$UV" run --no-project python - <<'PY'
import json, os
with open(os.environ["SERVERS_JSON"], "r") as f:
    servers = json.load(f)
for name, cfg in servers.items():
    print(name + "\t" + json.dumps(cfg))
PY
)
fi

# --- done ---------------------------------------------------------------------
printf '\n%s설치가 끝났습니다 🎉%s\n' "$C_GREEN$C_BOLD" "$C_OFF"
echo "다음 단계:"
if [ "$TARGET_DESKTOP" = "1" ]; then
  echo "  • Claude Desktop을 완전히 종료했다가 다시 실행하세요."
  echo "    새 대화에서:  내 Google Analytics 속성 목록을 보여줘"
fi
if [ "$TARGET_CLI" = "1" ]; then
  echo "  • Claude Code CLI:  claude mcp list 로 등록을 확인하세요."
  echo "    대화에서:  내 Google Analytics 속성 목록을 보여줘"
fi
if [ "$WITH_ADS" = "1" ]; then
  echo "     Google Ads도 물어보세요:      내가 접근할 수 있는 Google Ads 계정 보여줘"
  echo ""
  echo "참고: developer token은 설정 파일에 평문으로 저장됩니다."
fi
if [ "$TARGET_DESKTOP" = "1" ]; then
  echo ""
  echo "문제가 있으면 Claude Desktop 설정 파일을 확인하세요:"
  echo "  $CONFIG"
fi
