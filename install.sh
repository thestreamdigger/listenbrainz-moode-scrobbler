#!/bin/bash

# =============================================================================
# ListenBrainz moOde Scrobbler - Installation Script
# Automated setup with token configuration
# =============================================================================

set -e

PROJECT_NAME="LBMS"
PYTHON_CMD="python3"
MIN_PYTHON="3.10"
BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$BASE_DIR/venv"
REQUIREMENTS_FILE="$BASE_DIR/requirements.txt"
DEFAULT_USER="pi"

SERVICE_EXAMPLE="$BASE_DIR/examples/lbms.service.example"
SERVICE_FILE="/etc/systemd/system/lbms.service"
SERVICE_NAME="lbms"

ENV_FILE="$BASE_DIR/.env"
SETTINGS_FILE="$BASE_DIR/src/settings.json"
CACHE_DIR="$BASE_DIR/src/cache"

QUIET_MODE=false
SKIP_SERVICE=false
SKIP_TOKEN=false

while [[ $# -gt 0 ]]; do
  case $1 in
    -q|--quiet)     QUIET_MODE=true; shift ;;
    --skip-service) SKIP_SERVICE=true; shift ;;
    --skip-token)   SKIP_TOKEN=true; shift ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo "Options:"
      echo "  -q, --quiet        Quiet mode (no prompts; keeps .env or skips token)"
      echo "  --skip-service     Skip systemd service setup"
      echo "  --skip-token       Skip token configuration"
      echo "  -h, --help         Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

log_info() { if [ "$QUIET_MODE" != "true" ]; then echo "[INFO] $1"; fi; }
log_warn() { echo "[WARN] $1"; }
log_error(){ echo "[ERROR] $1"; exit 1; }
log_ok()   { if [ "$QUIET_MODE" != "true" ]; then echo "[OK] $1"; fi; }

run() {
  local desc=$1; shift
  log_info "$desc"
  if [ "$QUIET_MODE" = "true" ]; then
    "$@" &> /dev/null || log_error "$desc failed"
  else
    "$@" || log_error "$desc failed"
  fi
}

TARGET_USER=${SUDO_USER:-$DEFAULT_USER}
if [ "$TARGET_USER" = "root" ]; then TARGET_USER=$DEFAULT_USER; fi

check_root() {
  if [ "$EUID" -ne 0 ]; then
    echo "[ERROR] run as root (sudo)"
    echo "usage: sudo $0 [OPTIONS]"
    exit 1
  fi
}

check_system() {
  log_info "System check"

  command -v "$PYTHON_CMD" &> /dev/null || log_error "$PYTHON_CMD not found"
  "$PYTHON_CMD" -c "import sys; sys.exit(sys.version_info < tuple(map(int, '$MIN_PYTHON'.split('.'))))" \
    || log_error "Python $MIN_PYTHON+ required, found $("$PYTHON_CMD" -V 2>&1)"
  "$PYTHON_CMD" -c "import venv, ensurepip" &> /dev/null \
    || log_error "venv missing: apt install python3-venv"
  id "$TARGET_USER" &> /dev/null || log_error "user not found: $TARGET_USER"

  local current
  current=$("$PYTHON_CMD" -c "import json, sys; print(json.load(open(sys.argv[1])).get('currentsong_file', ''))" \
    "$SETTINGS_FILE" 2>/dev/null || true)
  if [ -n "$current" ] && [ ! -f "$current" ]; then
    log_warn "currentsong_file not found: $current (moOde: Audio Config > Metadata file)"
  fi

  log_ok "System ready"
}

setup_python_env() {
  log_info "Venv init"
  if [ -d "$VENV_DIR" ]; then
    log_info "Venv exists, recreating"
    rm -rf "$VENV_DIR"
  fi
  run "Venv create" "$PYTHON_CMD" -m venv "$VENV_DIR"
  run "Deps install" "$VENV_DIR/bin/pip" install -r "$REQUIREMENTS_FILE"
  log_ok "Venv ready"
}

setup_configuration() {
  log_info "Config init"

  [ -f "$SETTINGS_FILE" ] || log_error "settings.json not found"

  if [ "$SKIP_TOKEN" = "true" ]; then
    log_info "Token skipped"
    return 0
  fi

  if [ "$QUIET_MODE" = "true" ]; then
    if [ -f "$ENV_FILE" ]; then
      log_info ".env kept"
    else
      log_warn "quiet mode: no .env, create $ENV_FILE with LISTENBRAINZ_TOKEN"
    fi
    return 0
  fi

  if [ -f "$ENV_FILE" ]; then
    log_info ".env exists"
    echo ""
    echo -n "Reconfigure token? (y/N): "
    read -r RECONFIGURE
    if [[ ! "$RECONFIGURE" =~ ^[Yy]$ ]]; then
      log_info ".env kept"
      return 0
    fi
  fi

  echo ""
  echo "==========================================="
  echo " ListenBrainz token setup"
  echo "==========================================="
  echo ""
  echo "Get your token at:"
  echo "  https://listenbrainz.org/settings/"
  echo ""
  echo "(log in, copy 'User Token')"
  echo ""
  echo -n "Token: "
  read -rs LB_TOKEN
  echo ""
  echo ""

  [ -n "$LB_TOKEN" ] || log_error "Empty token"

  if [ ${#LB_TOKEN} -lt 30 ]; then
    log_warn "Token too short (expected ~36 chars)"
    echo -n "Continue? (y/N): "
    read -r CONTINUE
    if [[ ! "$CONTINUE" =~ ^[Yy]$ ]]; then
      log_error "Install cancelled"
    fi
  fi

  log_info ".env writing"
  ( umask 077; cat > "$ENV_FILE" << EOF
# ListenBrainz API token
# Get from: https://listenbrainz.org/settings/
LISTENBRAINZ_TOKEN=$LB_TOKEN
EOF
  )

  log_ok "Token ready"
  echo ""
}

setup_permissions() {
  log_info "Perms init"
  mkdir -p "$CACHE_DIR"
  chown -R "$TARGET_USER:$TARGET_USER" "$BASE_DIR"
  chmod 755 "$BASE_DIR/install.sh" "$BASE_DIR/src/main.py"
  if [ -f "$ENV_FILE" ]; then
    chmod 600 "$ENV_FILE"
  fi
  log_ok "Perms ready"
}

setup_service() {
  if [ "$SKIP_SERVICE" = "true" ]; then
    log_info "Service skipped"
    return 0
  fi
  if [ ! -f "$SERVICE_EXAMPLE" ]; then
    log_info "No service example, skip"
    return 0
  fi

  log_info "Service install"
  sed -e "s|\r$||" \
      -e "s|/home/pi/lbms|$BASE_DIR|g" \
      -e "s|^User=pi$|User=$TARGET_USER|" \
      -e "s|^Group=pi$|Group=$TARGET_USER|" \
      "$SERVICE_EXAMPLE" > "$SERVICE_FILE"
  chmod 644 "$SERVICE_FILE"

  run "Daemon reload" systemctl daemon-reload
  run "Service enable" systemctl enable "$SERVICE_NAME.service"
  run "Service restart" systemctl restart "$SERVICE_NAME.service"
  log_ok "Service running"
}

check_root
log_info "$PROJECT_NAME install"
check_system
setup_python_env
setup_configuration
setup_permissions
setup_service

echo ""
echo "==========================================="
echo " $PROJECT_NAME: install complete"
echo "==========================================="
echo ""
echo " dir:    $BASE_DIR"
echo " venv:   $VENV_DIR"
echo " config: $SETTINGS_FILE"
echo " token:  $ENV_FILE (mode 600)"
echo ""
if [ "$SKIP_SERVICE" != "true" ] && [ -f "$SERVICE_FILE" ]; then
  echo " service: $SERVICE_NAME.service"
  echo ""
  echo " commands:"
  echo "   sudo systemctl status $SERVICE_NAME"
  echo "   sudo systemctl restart $SERVICE_NAME"
  echo "   sudo systemctl stop $SERVICE_NAME"
  echo "   sudo journalctl -u $SERVICE_NAME -f"
  echo ""
else
  echo " run:"
  echo "   $VENV_DIR/bin/python3 $BASE_DIR/src/main.py"
  echo ""
fi
echo " edit:"
echo "   nano $SETTINGS_FILE"
echo "   nano $ENV_FILE"
echo ""
echo " docs:  $BASE_DIR/README.md"
echo ""
echo "==========================================="
echo " Ready"
echo "==========================================="
echo ""

exit 0
