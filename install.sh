#!/bin/bash

# =============================================================================
# ListenBrainz moOde Scrobbler - Installer
# Inspired by ADAM3-GPIO install scripts (quiet/non-interactive, checks, service)
# =============================================================================

set -e

# ------------------------------
# CONFIG
# ------------------------------
PROJECT_NAME="LBMS"
PROJECT_DESC="ListenBrainz moOde Scrobbler"
VENV_DIR="venv"
REQUIREMENTS_FILE="requirements.txt"
PYTHON_CMD="python3"
BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ESSENTIAL_DEPS=("$PYTHON_CMD" "pip3")
SYSTEM_PKGS=("python3-venv")
QUIET_MODE=false
NON_INTERACTIVE=false

SERVICE_EXAMPLE="$BASE_DIR/examples/lbms.service.example"
SERVICE_FILE="/etc/systemd/system/lbms.service"

# ------------------------------
# ARG PARSE
# ------------------------------
while [[ $# -gt 0 ]]; do
  case $1 in
    -q|--quiet)
      QUIET_MODE=true
      shift
      ;;
    -y|--yes|--non-interactive)
      NON_INTERACTIVE=true
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  -q, --quiet             Quiet mode, minimal output"
      echo "  -y, --yes               Non-interactive mode, assume yes to all"
      echo "  -h, --help              Show this help message"
      exit 0
      ;;
    *)
      shift
      ;;
  esac
done

# ------------------------------
# LOG HELPERS
# ------------------------------
log_info() { if [ "$QUIET_MODE" != "true" ]; then echo "[INFO] $1"; fi; }
log_warn() { if [ "$QUIET_MODE" != "true" ]; then echo "[WARN] $1"; fi; }
log_error(){ echo "[ERROR] $1"; exit 1; }
log_ok()   { if [ "$QUIET_MODE" != "true" ]; then echo "[OK] $1"; fi; }

prompt_yes_no() {
  if [ "$NON_INTERACTIVE" = "true" ]; then
    return 0
  fi
  read -p "$1 (y/n): " -n 1 -r; echo
  [[ $REPLY =~ ^[Yy]$ ]] && return 0 || return 1
}

execute_cmd() {
  local desc=$1; shift
  local cmd="$@"
  if [ "$QUIET_MODE" = "true" ]; then
    if eval "$cmd" &> /dev/null; then return 0; else log_error "Failed to $desc. Command: $cmd"; fi
  else
    log_info "Executing: $desc"
    if eval "$cmd"; then return 0; else log_error "Failed to $desc. Command: $cmd"; fi
  fi
}

check_command() {
  if ! command -v "$1" &> /dev/null; then
    log_warn "$1 not found."
    [[ " ${ESSENTIAL_DEPS[*]} " =~ " $1 " ]] && log_error "Essential dependency missing: $1"
    return 1
  else
    log_ok "$1 found."
    return 0
  fi
}

# ------------------------------
# START
# ------------------------------
log_info "Starting installation of $PROJECT_DESC..."
log_info "Installation directory: $BASE_DIR"

# Check essential commands
MISSING_ESSENTIAL=false
for cmd in "${ESSENTIAL_DEPS[@]}"; do
  if ! check_command "$cmd"; then MISSING_ESSENTIAL=true; fi
done
[ "$MISSING_ESSENTIAL" = "true" ] && log_error "Essential dependencies are missing. Please install them and try again."

# Check/install system packages (if apt is available)
if command -v apt &> /dev/null; then
  log_info "Checking system packages..."
  MISSING_PACKAGES=()
  for pkg in "${SYSTEM_PKGS[@]}"; do
    if ! dpkg -s "$pkg" &> /dev/null; then
      log_warn "$pkg not installed."
      MISSING_PACKAGES+=("$pkg")
    fi
  done
  if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    execute_cmd "update package list" "sudo apt update"
    execute_cmd "install required packages" "sudo apt install -y ${MISSING_PACKAGES[*]}"
  fi
fi

# ------------------------------
# PYTHON VENV
# ------------------------------
log_info "Setting up Python virtual environment..."
if [ -d "$BASE_DIR/$VENV_DIR" ]; then
  log_info "Virtual environment already exists."
  if prompt_yes_no "Recreate the virtual environment?"; then
    rm -rf "$BASE_DIR/$VENV_DIR"
    execute_cmd "create virtual environment" "$PYTHON_CMD -m venv $VENV_DIR"
    log_ok "Virtual environment created."
  fi
else
  execute_cmd "create virtual environment" "$PYTHON_CMD -m venv $VENV_DIR"
  log_ok "Virtual environment created."
fi

# pip inside venv
PIP_CMD="$BASE_DIR/$VENV_DIR/bin/pip"
[ -f "$PIP_CMD" ] || log_error "Pip command not found in virtual environment at $PIP_CMD."

execute_cmd "upgrade pip" "$PIP_CMD install --upgrade pip"

# ------------------------------
# PYTHON DEPENDENCIES
# ------------------------------
if [ ! -f "$BASE_DIR/$REQUIREMENTS_FILE" ]; then
  log_error "$REQUIREMENTS_FILE not found."
fi
execute_cmd "install requirements" "$PIP_CMD install -r $REQUIREMENTS_FILE"

# ------------------------------
# PERMISSIONS
# ------------------------------
chmod +x "$BASE_DIR/src/main.py" 2>/dev/null || true
chmod +x "$BASE_DIR/install.sh" 2>/dev/null || true
chmod +x "$BASE_DIR/fix_permissions.sh" 2>/dev/null || true

if [ -f "$BASE_DIR/fix_permissions.sh" ]; then
  if command -v sudo &> /dev/null; then
    execute_cmd "configure permissions" "sudo $BASE_DIR/fix_permissions.sh"
  else
    execute_cmd "configure permissions" "$BASE_DIR/fix_permissions.sh"
  fi
fi

# ------------------------------
# SYSTEMD SERVICE
# ------------------------------
if [ -f "$SERVICE_EXAMPLE" ]; then
  log_info "Installing systemd service..."
  TMP_SERVICE="$(mktemp)"
  # Replace default example path with current directory
  sed "s|/home/pi/lbms|$BASE_DIR|g" "$SERVICE_EXAMPLE" > "$TMP_SERVICE"
  if command -v sudo &> /dev/null; then
    execute_cmd "install service file" "sudo cp -f '$TMP_SERVICE' '$SERVICE_FILE'"
    execute_cmd "reload systemd daemon" "sudo systemctl daemon-reload"
    # Enable and restart service by default (restart applies unit updates, starts if inactive)
    execute_cmd "enable service" "sudo systemctl enable lbms.service"
    execute_cmd "restart service" "sudo systemctl restart lbms.service"
  else
    log_warn "sudo not available. Copy $TMP_SERVICE to $SERVICE_FILE manually and run systemctl daemon-reload"
  fi
  rm -f "$TMP_SERVICE"
  log_ok "Service prepared."
else
  log_warn "Example service file not found at $SERVICE_EXAMPLE"
fi

# ------------------------------
# ADDITIONAL CHECKS
# ------------------------------
CURR_FILE_JSON="$BASE_DIR/src/settings.json"
if [ -f "$CURR_FILE_JSON" ]; then
  CUR_FILE=$(jq -r '.currentsong_file // empty' "$CURR_FILE_JSON" 2>/dev/null || echo "")
  if [ -n "$CUR_FILE" ] && [ ! -f "$CUR_FILE" ]; then
    log_warn "Configured currentsong_file ($CUR_FILE) does not exist on this system. Check moOde configuration."
  fi
fi

# ------------------------------
# SUMMARY
# ------------------------------
echo ""
echo "==================================================================="
echo " Installation complete: $PROJECT_DESC"
echo " Directory: $BASE_DIR"
echo " Python Environment: $VENV_DIR"
if [ -f "$SERVICE_FILE" ]; then
  echo " Service: $SERVICE_FILE"
  echo " Next steps:"
  echo "   sudo systemctl enable lbms.service"
  echo "   sudo systemctl start lbms.service"
  echo " Logs:"
  echo "   sudo journalctl -u lbms.service -f"
else
  echo " Systemd service not installed (example file missing or sudo unavailable)."
fi
echo " Manual run:"
echo "   $BASE_DIR/$VENV_DIR/bin/python3 $BASE_DIR/src/main.py"
echo "==================================================================="

exit 0
