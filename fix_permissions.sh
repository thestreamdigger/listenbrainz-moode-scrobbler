#!/bin/bash

# Define color codes for better visual feedback
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'  # No Color

echo -e "${GREEN}Adjusting ListenBrainz moOde Scrobbler permissions...${NC}\n"

# Ensure script is run with root privileges to modify permissions
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}This script must be run as root (sudo)${NC}"
    exit 1
fi

# Default user and group for Raspberry Pi
# These are the standard credentials used by moOde audio player
USER="pi"
GROUP="pi"

# Get the absolute path to the script's directory
# This ensures the script works regardless of where it's called from
BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${YELLOW}Configuring base directory: ${BASE_DIR}${NC}"

# Set ownership of all project files to pi:pi
# This ensures the service can access all necessary files
chown -R $USER:$GROUP "$BASE_DIR"
chmod 755 "$BASE_DIR"  # Directory needs execute permission to be accessed

# Configure source code directory permissions
# Python files need to be readable, main.py needs to be executable
echo -e "${YELLOW}Configuring src/ directory${NC}"
chmod 755 "$BASE_DIR/src"  # Directory needs to be accessible
chmod 644 "$BASE_DIR/src"/*.py  # Python files should be readable
chmod 644 "$BASE_DIR/src"/*.json  # JSON files should be readable
chmod 755 "$BASE_DIR/src/main.py"  # Main script needs execute permission

# Set up cache directory for offline scrobbles
# This directory stores failed submissions for later retry
echo -e "${YELLOW}Configuring cache directory${NC}"
CACHE_DIR="$BASE_DIR/src/cache/listenbrainz-moode-scrobbler"
mkdir -p "$CACHE_DIR"  # Create directory if it doesn't exist
chown -R $USER:$GROUP "$CACHE_DIR"  # Set ownership
chmod 755 "$CACHE_DIR"  # Directory needs to be accessible
chmod 644 "$CACHE_DIR"/*.json 2>/dev/null || true  # Cache files should be readable

# Configure settings files
# settings.json is more restrictive as it contains the API token
echo -e "${YELLOW}Configuring settings files${NC}"
chmod 644 "$BASE_DIR/src/settings.example.json"  # Example is public
chmod 600 "$BASE_DIR/src/settings.json"  # Restrict access to user only (contains token)

# Set permissions for project documentation and configuration files
# These files should be readable by anyone
echo -e "${YELLOW}Configuring project files${NC}"
chmod 644 "$BASE_DIR/README.md"      # Documentation
chmod 644 "$BASE_DIR/LICENSE"        # License information
chmod 644 "$BASE_DIR/requirements.txt"  # Python dependencies
chmod 644 "$BASE_DIR/setup.py"       # Installation script
chmod 644 "$BASE_DIR/.gitignore"     # Git configuration
chmod 644 "$BASE_DIR/lbms.service.example"  # Systemd service template

# Configure Python virtual environment if it exists
# This is where project dependencies are installed
if [ -d "$BASE_DIR/venv" ]; then
    echo -e "${YELLOW}Configuring virtualenv permissions${NC}"
    chown -R $USER:$GROUP "$BASE_DIR/venv"  # Set ownership
    chmod -R 755 "$BASE_DIR/venv"  # Make executable for python
fi

echo -e "\n${GREEN}Permissions successfully adjusted!${NC}"
echo -e "${YELLOW}Remember to verify if the systemd service is properly configured.${NC}" 