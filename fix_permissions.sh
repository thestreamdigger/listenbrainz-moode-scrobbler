#!/bin/bash

# Output colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Adjusting ListenBrainz moOde Scrobbler permissions...${NC}\n"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}This script must be run as root (sudo)${NC}"
    exit 1
fi

# Define user and group (usually pi:pi on Raspberry)
USER="pi"
GROUP="pi"

# Project base directory
BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${YELLOW}Configuring base directory: ${BASE_DIR}${NC}"

# Adjust main directory permissions
chown -R $USER:$GROUP "$BASE_DIR"
chmod 755 "$BASE_DIR"

# Adjust specific permissions for src/
echo -e "${YELLOW}Configuring src/ directory${NC}"
chmod 755 "$BASE_DIR/src"
chmod 644 "$BASE_DIR/src"/*.py
chmod 644 "$BASE_DIR/src"/*.json
chmod 755 "$BASE_DIR/src/main.py"  # Main executable file

# Ensure cache directory exists and has correct permissions
echo -e "${YELLOW}Configuring cache directory${NC}"
CACHE_DIR="$BASE_DIR/src/cache/listenbrainz-moode-scrobbler"
mkdir -p "$CACHE_DIR"
chown -R $USER:$GROUP "$CACHE_DIR"
chmod 755 "$CACHE_DIR"
chmod 644 "$CACHE_DIR"/*.json 2>/dev/null || true

# Adjust configuration file permissions
echo -e "${YELLOW}Configuring settings files${NC}"
chmod 644 "$BASE_DIR/src/settings.example.json"
chmod 600 "$BASE_DIR/src/settings.json"  # More restrictive due to token

# Adjust project file permissions
echo -e "${YELLOW}Configuring project files${NC}"
chmod 644 "$BASE_DIR/README.md"
chmod 644 "$BASE_DIR/LICENSE"
chmod 644 "$BASE_DIR/requirements.txt"
chmod 644 "$BASE_DIR/setup.py"
chmod 644 "$BASE_DIR/.gitignore"
chmod 644 "$BASE_DIR/lbms.service.example"

# Check currentsong.txt access
echo -e "${YELLOW}Checking currentsong.txt access${NC}"
if [ -f "/var/local/www/currentsong.txt" ]; then
    if getfacl "/var/local/www/currentsong.txt" 2>/dev/null | grep -q "^user:$USER:r"; then
        echo -e "${GREEN}currentsong.txt access OK${NC}"
    else
        echo -e "${RED}Warning: $USER might not have permission to read currentsong.txt${NC}"
        echo -e "${YELLOW}Run: sudo setfacl -m u:$USER:r /var/local/www/currentsong.txt${NC}"
    fi
else
    echo -e "${RED}Warning: currentsong.txt not found in /var/local/www/${NC}"
fi

# Check venv permissions if it exists
if [ -d "$BASE_DIR/venv" ]; then
    echo -e "${YELLOW}Configuring virtualenv permissions${NC}"
    chown -R $USER:$GROUP "$BASE_DIR/venv"
    chmod -R 755 "$BASE_DIR/venv"
fi

echo -e "\n${GREEN}Permissions successfully adjusted!${NC}"
echo -e "${YELLOW}Remember to verify if the systemd service is properly configured.${NC}" 