#!/bin/bash

# =============================================================================
# ListenBrainz moOde Scrobbler - Installation Script
# Automated setup with token configuration
# =============================================================================

set -e

# Configuration
PROJECT_NAME="LBMS"
PROJECT_DESC="ListenBrainz moOde Scrobbler"
VENV_DIR="venv"
REQUIREMENTS_FILE="requirements.txt"
PYTHON_CMD="python3"
BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DEFAULT_USER="pi"

# Service configuration
SERVICE_EXAMPLE="$BASE_DIR/examples/lbms.service.example"
SERVICE_FILE="/etc/systemd/system/lbms.service"
SERVICE_NAME="lbms"

# Configuration files
ENV_FILE="$BASE_DIR/.env"
SETTINGS_FILE="$BASE_DIR/src/settings.json"

# Options
QUIET_MODE=false
SKIP_SERVICE=false
SKIP_TOKEN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -q|--quiet)
      QUIET_MODE=true
      shift
      ;;
    --skip-service)
      SKIP_SERVICE=true
      shift
      ;;
    --skip-token)
      SKIP_TOKEN=true
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo "Options:"
      echo "  -q, --quiet        Quiet mode (no interactive prompts)"
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

# Logging functions
log_info() { if [ "$QUIET_MODE" != "true" ]; then echo "[INFO] $1"; fi; }
log_error(){ echo "[ERROR] $1"; exit 1; }
log_ok()   { if [ "$QUIET_MODE" != "true" ]; then echo "[OK] $1"; fi; }

# Utility functions
check_root() {
  if [ "$EUID" -ne 0 ]; then 
    echo "Error: Please run as root (sudo)"
    echo "Usage: sudo $0 [OPTIONS]"
    exit 1
  fi
}

execute_cmd() {
  local desc=$1; shift
  local cmd="$@"
  if [ "$QUIET_MODE" = "true" ]; then
    if eval "$cmd" &> /dev/null; then return 0; else log_error "Failed to $desc"; fi
  else
    log_info "Executing: $desc"
    if eval "$cmd"; then return 0; else log_error "Failed to $desc"; fi
  fi
}

# Check system requirements
check_system() {
  log_info "Checking system requirements..."
  
  # Check Python
  if ! command -v python3 &> /dev/null; then
    log_error "python3 not found. Please install Python 3."
  fi
  
  # Check pip
  if ! command -v pip3 &> /dev/null; then
    log_error "pip3 not found. Please install pip."
  fi

  # Check moOde configuration
  if [ -f "$BASE_DIR/src/settings.json" ]; then
    CURR_FILE=$(jq -r '.currentsong_file // empty' "$BASE_DIR/src/settings.json" 2>/dev/null || echo "")
    if [ -n "$CURR_FILE" ] && [ ! -f "$CURR_FILE" ]; then
      log_info "Warning: Configured currentsong_file ($CURR_FILE) does not exist. Check moOde configuration."
    fi
  fi

  log_ok "System requirements OK"
}

# Setup Python environment
setup_python_env() {
  log_info "Setting up Python virtual environment..."
  
  if [ -d "$BASE_DIR/$VENV_DIR" ]; then
    log_info "Virtual environment already exists."
    rm -rf "$BASE_DIR/$VENV_DIR"
  fi
  
  execute_cmd "create virtual environment" "$PYTHON_CMD -m venv $VENV_DIR"
  
  # Install requirements
  if [ -f "$BASE_DIR/$REQUIREMENTS_FILE" ]; then
    log_info "Installing dependencies..."
    execute_cmd "install requirements" "$BASE_DIR/$VENV_DIR/bin/pip install -r $REQUIREMENTS_FILE"
  else
    log_info "No requirements.txt found, skipping dependencies"
  fi
  
  log_ok "Python environment ready"
}

# Configure token and settings
setup_configuration() {
  log_info "Setting up configuration files..."

  TARGET_USER=${SUDO_USER:-$DEFAULT_USER}
  if [ "$TARGET_USER" = "root" ]; then TARGET_USER=$DEFAULT_USER; fi

  # settings.json is now committed to repository (without token)
  # Just ensure correct permissions
  if [ -f "$SETTINGS_FILE" ]; then
    chown "$TARGET_USER:$TARGET_USER" "$SETTINGS_FILE"
    chmod 600 "$SETTINGS_FILE"
    log_info "settings.json permissions configured"
  else
    log_error "settings.json not found in repository!"
  fi

  # Setup .env file
  if [ "$SKIP_TOKEN" = "true" ]; then
    log_info "Skipping token configuration..."
    return 0
  fi

  if [ -f "$ENV_FILE" ]; then
    log_info ".env file already exists"
    echo ""
    echo -n "Do you want to reconfigure your token? (y/N): "
    read -r RECONFIGURE
    if [[ ! "$RECONFIGURE" =~ ^[Yy]$ ]]; then
      log_info "Keeping existing .env file"
      return 0
    fi
  fi

  # Prompt for token
  echo ""
  echo "========================================================================="
  echo " ListenBrainz Token Configuration"
  echo "========================================================================="
  echo ""
  echo "To use this scrobbler, you need a ListenBrainz API token."
  echo ""
  echo "How to get your token:"
  echo "  1. Visit: https://listenbrainz.org/settings/"
  echo "  2. Log in or create an account"
  echo "  3. Copy your 'User Token'"
  echo ""
  echo -n "Enter your ListenBrainz token: "
  read -r LB_TOKEN
  echo ""

  # Validate token (basic check)
  if [ -z "$LB_TOKEN" ]; then
    log_error "Token cannot be empty!"
  fi

  if [ ${#LB_TOKEN} -lt 30 ]; then
    echo "Warning: Token seems too short (expected ~36 characters)"
    echo -n "Continue anyway? (y/N): "
    read -r CONTINUE
    if [[ ! "$CONTINUE" =~ ^[Yy]$ ]]; then
      log_error "Installation cancelled"
    fi
  fi

  # Create .env file
  log_info "Creating .env file..."
  cat > "$ENV_FILE" << EOF
# ListenBrainz Configuration
# Your ListenBrainz API token
# Get it from: https://listenbrainz.org/settings/
LISTENBRAINZ_TOKEN=$LB_TOKEN
EOF

  # Secure the .env file
  chown "$TARGET_USER:$TARGET_USER" "$ENV_FILE"
  chmod 600 "$ENV_FILE"

  log_ok "Token configured successfully"
  echo ""
}

# Setup permissions
setup_permissions() {
  log_info "Setting up permissions..."

  TARGET_USER=${SUDO_USER:-$DEFAULT_USER}
  if [ "$TARGET_USER" = "root" ]; then TARGET_USER=$DEFAULT_USER; fi

  # Set ownership (excluding __pycache__ directories)
  find "$BASE_DIR" -type f ! -path "*/__pycache__/*" ! -name "*.pyc" -exec chown "$TARGET_USER:$TARGET_USER" {} \; 2>/dev/null || true
  find "$BASE_DIR" -type d ! -path "*/__pycache__" -exec chown "$TARGET_USER:$TARGET_USER" {} \; 2>/dev/null || true

  # Set permissions
  find "$BASE_DIR" -type d -exec chmod 755 {} \;
  find "$BASE_DIR" -type f -name "*.py" -exec chmod 644 {} \;

  # Make scripts executable
  chmod 755 "$BASE_DIR/install.sh" 2>/dev/null || true
  chmod 755 "$BASE_DIR/src/main.py" 2>/dev/null || true

  # Protect sensitive files
  if [ -f "$SETTINGS_FILE" ]; then
    chmod 600 "$SETTINGS_FILE"
    chown "$TARGET_USER:$TARGET_USER" "$SETTINGS_FILE"
  fi

  if [ -f "$ENV_FILE" ]; then
    chmod 600 "$ENV_FILE"
    chown "$TARGET_USER:$TARGET_USER" "$ENV_FILE"
  fi

  # Ensure cache directories
  CACHE_DIR="$BASE_DIR/src/cache"
  mkdir -p "$CACHE_DIR" 2>/dev/null || true
  chmod 755 "$BASE_DIR/src" "$CACHE_DIR" 2>/dev/null || true
  chown -R "$TARGET_USER:$TARGET_USER" "$CACHE_DIR" 2>/dev/null || true

  log_ok "Permissions configured"
}

# Setup systemd service
setup_service() {
  if [ "$SKIP_SERVICE" = "true" ]; then
    log_info "Skipping systemd service setup..."
    return 0
  fi

  if [ -f "$SERVICE_EXAMPLE" ]; then
    log_info "Installing systemd service..."
    TMP_SERVICE="$(mktemp)"
    sed "s|/home/pi/lbms|$BASE_DIR|g" "$SERVICE_EXAMPLE" > "$TMP_SERVICE"
    
    execute_cmd "install service file" "sudo cp '$TMP_SERVICE' '$SERVICE_FILE'"
    execute_cmd "reload systemd daemon" "sudo systemctl daemon-reload"
    execute_cmd "enable service" "sudo systemctl enable $SERVICE_NAME.service"
    execute_cmd "start service" "sudo systemctl start $SERVICE_NAME.service"
    
    rm -f "$TMP_SERVICE"
    log_ok "Service installed and started"
  else
    log_info "No service example found, skipping systemd setup"
  fi
}

# Main execution
log_info "Starting installation of $PROJECT_NAME..."

# Check system
check_system

# Check root privileges first
check_root

# Setup Python environment
setup_python_env

# Setup configuration (token and settings)
setup_configuration

# Setup permissions
setup_permissions

# Setup service
setup_service

# Summary
echo ""
echo "==================================================================="
echo " Installation Complete: $PROJECT_NAME"
echo "==================================================================="
echo ""
echo " Installation Directory: $BASE_DIR"
echo " Python Environment: $VENV_DIR"
echo " Configuration: $SETTINGS_FILE"
echo " Token stored in: $ENV_FILE (secure)"
echo ""
if [ "$SKIP_SERVICE" != "true" ] && [ -f "$SERVICE_FILE" ]; then
  echo " Systemd Service: $SERVICE_NAME.service"
  echo ""
  echo " Service Commands:"
  echo "   sudo systemctl status $SERVICE_NAME"
  echo "   sudo systemctl restart $SERVICE_NAME"
  echo "   sudo systemctl stop $SERVICE_NAME"
  echo "   sudo journalctl -u $SERVICE_NAME -f"
  echo ""
else
  echo " Manual Execution:"
  echo "   $BASE_DIR/$VENV_DIR/bin/python3 $BASE_DIR/src/main.py"
  echo ""
fi
echo " Configuration Files:"
echo "   Edit settings: nano $SETTINGS_FILE"
echo "   Change token: nano $ENV_FILE"
echo ""
echo " Documentation:"
echo "   README: $BASE_DIR/README.md"
echo "   .env Guide: $BASE_DIR/docs/ENV_GUIDE.md"
echo ""
echo "==================================================================="
echo " Installation successful! The scrobbler is ready to use."
echo "==================================================================="
echo ""

exit 0