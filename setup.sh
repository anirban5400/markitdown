#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() {
  echo -e "${GREEN}[markitdown]${NC} $1"
}

warn() {
  echo -e "${YELLOW}[markitdown]${NC} $1"
}

fail() {
  echo -e "${RED}[markitdown]${NC} $1" >&2
  exit 1
}

require_linux() {
  if [[ "$(uname -s)" != "Linux" ]]; then
    fail "Run this script on the Ubuntu DigitalOcean droplet."
  fi
}

install_docker() {
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    log "Docker and Docker Compose are already installed."
    return
  fi

  log "Installing Docker and Docker Compose plugin..."
  sudo apt-get update
  sudo apt-get install -y ca-certificates curl gnupg
  sudo install -m 0755 -d /etc/apt/keyrings

  if [[ ! -f /etc/apt/keyrings/docker.gpg ]]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
  fi

  source /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null

  sudo apt-get update
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  sudo systemctl enable --now docker
}

prompt_config() {
  local detected_ip
  detected_ip="$(curl -fsS --max-time 5 https://api.ipify.org || true)"

  read -r -p "Server public IP [${detected_ip:-required if no domain}]: " SERVER_IP
  SERVER_IP="${SERVER_IP:-$detected_ip}"

  read -r -p "Domain name, leave blank to use IP:port: " DOMAIN
  DOMAIN="${DOMAIN:-}"

  if [[ -n "$DOMAIN" ]]; then
    read -r -p "Email for HTTPS certificate notices: " ACME_EMAIL
    [[ -n "$ACME_EMAIL" ]] || fail "Email is required when domain mode is enabled."
    PUBLIC_PORT=80
  else
    [[ -n "$SERVER_IP" ]] || fail "Server IP is required when no domain is provided."
    read -r -p "Public port [8080]: " PUBLIC_PORT
    PUBLIC_PORT="${PUBLIC_PORT:-8080}"
  fi

  read -r -p "Max upload size in MB [50]: " MAX_UPLOAD_MB
  MAX_UPLOAD_MB="${MAX_UPLOAD_MB:-50}"

}

write_env() {
  umask 077
  {
    echo "PUBLIC_PORT=${PUBLIC_PORT}"
    echo "MAX_UPLOAD_MB=${MAX_UPLOAD_MB}"
  } > .env
}

write_caddyfile() {
  cat > Caddyfile <<EOF
{
    email ${ACME_EMAIL}
}

${DOMAIN} {
    reverse_proxy markitdown:8000
}
EOF
}

deploy() {
  if [[ -n "$DOMAIN" ]]; then
    write_caddyfile
    log "Starting domain deployment for https://${DOMAIN}"
    sudo docker compose -f docker-compose.port.yml down --remove-orphans || true
    sudo docker compose -f docker-compose.domain.yml up -d --build
    log "Deployed: https://${DOMAIN}"
  else
    log "Starting IP and port deployment for http://${SERVER_IP}:${PUBLIC_PORT}"
    sudo docker compose -f docker-compose.domain.yml down --remove-orphans || true
    sudo docker compose -f docker-compose.port.yml up -d --build
    log "Deployed: http://${SERVER_IP}:${PUBLIC_PORT}"
  fi
}

main() {
  require_linux
  install_docker
  prompt_config
  write_env
  deploy

  warn "If you use a firewall, allow ports 80/443 for domain mode or ${PUBLIC_PORT} for port mode."
  log "Health check path: /health"
  log "Convert path: POST /convert with multipart field name 'file'"
}

main "$@"
