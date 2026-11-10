#!/usr/bin/env bash
# ==========================================================================
# install-russia.sh — bootstrap PRODUCTION NODE (Russia)
# На этом узле НЕТ: LLM-ключей, AI-агентов, доступа к control-plane БД.
# Только: reverse proxy, production runtime, deploy-broker-exec, бэкапы.
# ==========================================================================
set -euo pipefail
IFS=$'\n\t'

NODE_ROLE="russia"
APP_DIR="/opt/founder-ai-os"
LOG="/var/log/install-${NODE_ROLE}.log"
exec > >(tee -a "$LOG") 2>&1

echo "=== [$(date -Is)] Bootstrap ${NODE_ROLE} node (production) ==="

[[ $EUID -eq 0 ]] || { echo "Нужен root"; exit 1; }
[[ -f /root/.config/sops/age/keys.txt ]] || {
  echo "Положите age-ключ russia в /root/.config/sops/age/keys.txt"; exit 1; }

export DEBIAN_FRONTEND=noninteractive
apt-get update && apt-get upgrade -y
apt-get install -y --no-install-recommends \
  ca-certificates curl git jq ufw fail2ban restic

if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sh
fi

if ! command -v sops >/dev/null; then
  SOPS_VER="3.9.0"
  curl -fsSLo /usr/local/bin/sops \
    "https://github.com/getsops/sops/releases/download/v${SOPS_VER}/sops-v${SOPS_VER}.linux.amd64"
  chmod +x /usr/local/bin/sops
fi

# --- Пользователи ------------------------------------------------------------
useradd -m -s /bin/bash ops 2>/dev/null || true
# deploy-ai: ОГРАНИЧЕННЫЙ пользователь для AI-инициированных деплоев.
# Shell — forced command через authorized_keys; прямого shell нет.
useradd -m -s /bin/bash deploy-ai 2>/dev/null || true
mkdir -p /home/deploy-ai/.ssh

# --- SSH hardening -------------------------------------------------------------
cat > /etc/ssh/sshd_config.d/90-founder.conf <<'EOF'
PasswordAuthentication no
PermitRootLogin prohibit-password
AllowUsers ops deploy-ai
EOF
systemctl reload ssh

# --- Firewall: 80/443 снаружи, остальное только tailnet ------------------------
ufw default deny incoming
ufw default allow outgoing
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow in on tailscale0
ufw --force enable
systemctl enable --now fail2ban

# --- Tailscale -------------------------------------------------------------------
if ! command -v tailscale >/dev/null; then
  curl -fsSL https://tailscale.com/install.sh | sh
fi
mkdir -p "$APP_DIR"
git clone git@github.com:your-org/infrastructure.git "$APP_DIR" 2>/dev/null || git -C "$APP_DIR" pull --ff-only

TS_KEY=$(sops -d --extract '["tailscale_auth_key"]' "${APP_DIR}/secrets/${NODE_ROLE}.enc.yaml")
tailscale up --auth-key="${TS_KEY}" --hostname=ru-node --advertise-tags=tag:production
unset TS_KEY

# --- deploy-broker-exec: единственное, что умеет deploy-ai ----------------------
install -m 0755 "$APP_DIR/broker/deploy-broker-exec" /usr/local/bin/deploy-broker-exec
# authorized_keys: forced command. Публичные ключи брокера — из репозитория (не секреты).
{
  while read -r pubkey; do
    echo "command=\"/usr/local/bin/deploy-broker-exec\",no-pty,no-agent-forwarding,no-X11-forwarding ${pubkey}"
  done < "$APP_DIR/broker/allowed_deployers.pub"
} > /home/deploy-ai/.ssh/authorized_keys
chmod 700 /home/deploy-ai/.ssh && chmod 600 /home/deploy-ai/.ssh/authorized_keys
chown -R deploy-ai:deploy-ai /home/deploy-ai/.ssh

# deploy-ai может управлять ТОЛЬКО своим compose-проектом через wrapper,
# права на docker — через группу, sudo не выдаётся.
usermod -aG docker deploy-ai

# --- Production compose (ВФОРУМЕ и др.) -----------------------------------------
sops -d "${APP_DIR}/secrets/${NODE_ROLE}.enc.yaml" > "${APP_DIR}/.env"
chmod 600 "${APP_DIR}/.env"
cd "$APP_DIR"
docker compose -f docker-compose.ru.yml pull
docker compose -f docker-compose.ru.yml up -d

# --- Backup cron ------------------------------------------------------------------
cat > /etc/cron.d/founder-backup <<'EOF'
47 3 * * * root /opt/founder-ai-os/scripts/backup-ru.sh >> /var/log/restic-ru.log 2>&1
EOF

echo "=== [$(date -Is)] Russia production node готов ==="
echo "Проверка из Spain: ssh deploy-ai@ru-node 'healthcheck vforume'"
