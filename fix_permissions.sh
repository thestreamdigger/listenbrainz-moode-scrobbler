#!/bin/bash

# =============================================================================
# ListenBrainz moOde Scrobbler - Permissions Setup
# =============================================================================

set -e

DEFAULT_USER="pi"
BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_NAME="LBMS"

log_info()  { echo "[INFO] $1"; }
log_warn()  { echo "[WARN] $1"; }
log_error() { echo "[ERROR] $1"; exit 1; }
log_ok()    { echo "[OK] $1"; }

check_root() {
  if [ "$EUID" -ne 0 ]; then log_error "Please run as root (sudo)"; fi
}

log_info "Setting up permissions for $PROJECT_NAME in $BASE_DIR..."
check_root

# Determine target user
TARGET_USER=${SUDO_USER:-$DEFAULT_USER}
if [ "$TARGET_USER" = "root" ]; then TARGET_USER=$DEFAULT_USER; fi
log_info "Target user: $TARGET_USER"

# Ownership
log_info "Setting ownership of project directory..."
chown -R "$TARGET_USER:$TARGET_USER" "$BASE_DIR" || log_error "Failed to set ownership"

# Directories 755
log_info "Applying directory permissions..."
find "$BASE_DIR" -type d -exec chmod 755 {} \; || log_error "Failed to set directory permissions"

# Python files 644
log_info "Applying permissions to Python files..."
find "$BASE_DIR" -type f -name "*.py" -exec chmod 644 {} \; || log_error "Failed to set Python file permissions"

# Executables 755
log_info "Marking main scripts as executable..."
for script in \
  "$BASE_DIR/fix_permissions.sh" \
  "$BASE_DIR/install.sh" \
  "$BASE_DIR/src/main.py"
do
  if [ -f "$script" ]; then
    chmod 755 "$script" || log_error "Failed to set executable: $script"
    log_ok "Executable: $(basename "$script")"
  fi
done

# Restrict sensitive config (if present)
if [ -f "$BASE_DIR/src/settings.json" ]; then
  log_info "Restricting permissions on src/settings.json (contains token)."
  chmod 600 "$BASE_DIR/src/settings.json" || log_warn "Failed to restrict settings.json"
  chown "$TARGET_USER:$TARGET_USER" "$BASE_DIR/src/settings.json" || true
fi

# Ensure cache directories
CACHE_DIR="$BASE_DIR/src/cache/listenbrainz-moode-scrobbler"
mkdir -p "$CACHE_DIR" 2>/dev/null || true
chmod 755 "$BASE_DIR/src" "$BASE_DIR/src/cache" "$CACHE_DIR" 2>/dev/null || true
chown -R "$TARGET_USER:$TARGET_USER" "$BASE_DIR/src/cache" 2>/dev/null || true

# Summary
log_ok "Permissions configured successfully!"
log_info "Summary:"
log_info "- Owner/Group: $TARGET_USER:$TARGET_USER"
log_info "- Directories: 755"
log_info "- .py: 644 (main scripts 755)"
if [ -f "$BASE_DIR/src/settings.json" ]; then
  log_info "- src/settings.json: 600"
fi

exit 0


