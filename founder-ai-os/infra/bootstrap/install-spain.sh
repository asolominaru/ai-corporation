#!/usr/bin/env bash
# ==========================================================================
# install-spain.sh — bootstrap PRIMARY AI NODE (Spain)
# Запуск: curl -sSL <repo>/install-spain.sh | bash   (от root на чистом Ubuntu 24.04)
# Секреты: только через SOPS. Скрипт не содержит и не запрашивает секреты в открытом виде.
# ==========================================================================
set -euo pipefail
IFS=$'\n\t'

NODE_ROLE="spain"
APP_DIR="/opt/founder-ai-os"
LOG="/var/log/install-${NODE_ROLE}.log"
exec > >(tee -a "$LOG") 2>&1

echo "=== [$(date -Is)] Bootstrap ${NODE_ROLE} node ==="

# --- 0. Предусловия -------------------------------------------------------
[[ $EUID -eq 0 ]] || { echo "Нужен root"; exit 1; }
[[ -f /root/.config/sops/age/keys.txt ]] || {
  echo "Положите age-ключ узла в /root/.config/sops/age/keys.txt и перезапустите"; exit 1; }

# --- 1. Базовая система ---------------------------------------------------
export DEBIAN_FRONTEND=noninteractive
apt-get update && apt-get upgrade -y
apt-get install -y --no-install-recommends \
  ca-certificates curl git jq unzip ufw fail2ban \
  python3 python3-venv python3-pip \
  unattended-upgrades apt-listchanges

# Node.js LTS
if ! command -v node >/dev/null; then
  curl -fsSL https://deb.nodesource.com/setup_lts.x | bash -
  apt-get install -y nodejs
fi

# Docker + Compose plugin
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sh
fi
docker compose version >/dev/null

# SOPS + age
if ! command -v sops >/dev/null; then
  SOPS_VER="3.9.0"
  curl -fsSLo /usr/local/bin/sops \
    "https://github.com/getsops/sops/releases/download/v${SOPS_VER}/sops-v${SOPS_VER}.linux.amd64"
  chmod +x /usr/local/bin/sops
fi
command -v age-keygen >/dev/null || apt-get install -y age || true

# --- 2. Пользователи ------------------------------------------------------
useradd -m -s /bin/bash ops 2>/dev/null || true
useradd -r -s /usr/sbin/nologin monitor 2>/dev/null || true
# deploy-ai на этом узле не нужен (он на RU); Spain сам ходит наружу через deploy-broker

# --- 3. SSH hardening -----------------------------------------------------
cat > /etc/ssh/sshd_config.d/90-founder.conf <<'EOF'
PasswordAuthentication no
PermitRootLogin prohibit-password
AllowUsers ops
EOF
systemctl reload ssh

# --- 4. Firewall: наружу только 443 (caddy) и SSH из tailnet --------------
ufw default deny incoming
ufw default allow outgoing
ufw allow in on tailscale0
ufw allow 443/tcp
ufw --force enable

# --- 5. Fail2ban + автообновления ----------------------------------------
systemctl enable --now fail2ban
dpkg-reconfigure -f noninteractive unattended-upgrades

# --- 6. Tailscale (установка; подключение — после git clone, т.к. auth key в sops-файле репо) ---
if ! command -v tailscale >/dev/null; then
  curl -fsSL https://tailscale.com/install.sh | sh
fi

# --- 7. Код и конфигурация -------------------------------------------------
mkdir -p "$APP_DIR" /srv/worktrees
git clone git@github.com:your-org/founder-ai-os.git "$APP_DIR" 2>/dev/null || git -C "$APP_DIR" pull --ff-only
cd "$APP_DIR"

# auth key берётся из sops-файла, НЕ из аргумента командной строки
TS_KEY=$(sops -d --extract '["tailscale_auth_key"]' "infra/secrets/${NODE_ROLE}.enc.yaml")
tailscale up --auth-key="${TS_KEY}" --hostname=es-node --advertise-tags=tag:control
unset TS_KEY

# Расшифровка секретов узла -> .env (0600, не коммитится)
sops -d "infra/secrets/${NODE_ROLE}.enc.yaml" > infra/.env
chmod 600 infra/.env

# --- 8. Запуск --------------------------------------------------------------
cd infra
docker compose pull
docker compose up -d

# Миграции БД
docker compose exec -T orchestrator alembic upgrade head

# --- 9. Backup cron -----------------------------------------------------------
cat > /etc/cron.d/founder-backup <<'EOF'
17 3 * * * root cd /opt/founder-ai-os/infra && docker compose run --rm restic >> /var/log/restic.log 2>&1
*/15 * * * * root /opt/founder-ai-os/scripts/wal-archive-push.sh >> /var/log/wal-archive.log 2>&1
EOF

# --- 10. Проверка ---------------------------------------------------------------
sleep 15
curl -fsS http://localhost:8000/health >/dev/null && echo "orchestrator: OK"
curl -fsS http://localhost:3000 >/dev/null && echo "grafana: OK"
echo "=== [$(date -Is)] Spain node готов. Health: https://api.${DOMAIN}/health ==="
