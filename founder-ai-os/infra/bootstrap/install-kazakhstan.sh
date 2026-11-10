#!/usr/bin/env bash
# ==========================================================================
# install-kazakhstan.sh — bootstrap SECONDARY AI NODE (warm standby)
# Принцип: PULL-модель. KZ сам забирает бэкапы/зеркала с внешних источников.
# Живых production-сервисов здесь нет до активации DR-сценария.
# ==========================================================================
set -euo pipefail
IFS=$'\n\t'

NODE_ROLE="kazakhstan"
APP_DIR="/opt/founder-ai-os"
LOG="/var/log/install-${NODE_ROLE}.log"
exec > >(tee -a "$LOG") 2>&1

echo "=== [$(date -Is)] Bootstrap ${NODE_ROLE} node (warm standby) ==="

[[ $EUID -eq 0 ]] || { echo "Нужен root"; exit 1; }
[[ -f /root/.config/sops/age/keys.txt ]] || {
  echo "Положите age-ключ kazakhstan в /root/.config/sops/age/keys.txt"; exit 1; }

export DEBIAN_FRONTEND=noninteractive
apt-get update && apt-get upgrade -y
apt-get install -y --no-install-recommends \
  ca-certificates curl git jq ufw fail2ban restic \
  python3 python3-venv

if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sh
fi

# SOPS
if ! command -v sops >/dev/null; then
  SOPS_VER="3.9.0"
  curl -fsSLo /usr/local/bin/sops \
    "https://github.com/getsops/sops/releases/download/v${SOPS_VER}/sops-v${SOPS_VER}.linux.amd64"
  chmod +x /usr/local/bin/sops
fi

useradd -m -s /bin/bash ops 2>/dev/null || true
cat > /etc/ssh/sshd_config.d/90-founder.conf <<'EOF'
PasswordAuthentication no
PermitRootLogin prohibit-password
AllowUsers ops
EOF
systemctl reload ssh

ufw default deny incoming
ufw default allow outgoing
ufw allow in on tailscale0
ufw --force enable

systemctl enable --now fail2ban

if ! command -v tailscale >/dev/null; then
  curl -fsSL https://tailscale.com/install.sh | sh
fi

# --- Репозитории: зеркала (сначала код — в нём лежат sops-секреты узла) -------
mkdir -p "$APP_DIR" /srv/git-mirror /srv/backups
git clone git@github.com:your-org/founder-ai-os.git "$APP_DIR" 2>/dev/null || git -C "$APP_DIR" pull --ff-only

TS_KEY=$(sops -d --extract '["tailscale_auth_key"]' "${APP_DIR}/infra/secrets/${NODE_ROLE}.enc.yaml")
tailscale up --auth-key="${TS_KEY}" --hostname=kz-node --advertise-tags=tag:standby
unset TS_KEY

for repo in founder-ai-os vforume infrastructure; do
  if [[ ! -d "/srv/git-mirror/${repo}.git" ]]; then
    git clone --mirror "git@github.com:your-org/${repo}.git" "/srv/git-mirror/${repo}.git"
  fi
done

# --- Cron: зеркала + pull бэкапов + ежемесячный restore test ----------------
cat > /etc/cron.d/founder-standby <<'EOF'
*/15 * * * * root for r in /srv/git-mirror/*.git; do git -C "$r" remote update --prune; done >> /var/log/git-mirror.log 2>&1
30 4 * * * root /opt/founder-ai-os/scripts/pull-backups.sh >> /var/log/pull-backups.log 2>&1
0 6 1 * * root /opt/founder-ai-os/scripts/restore-test.sh >> /var/log/restore-test.log 2>&1
EOF

# --- Конфигурация для активации (готова, но не запущена) ---------------------
cd "$APP_DIR"
[[ -f "infra/secrets/${NODE_ROLE}.enc.yaml" ]] && {
  sops -d "infra/secrets/${NODE_ROLE}.enc.yaml" > infra/.env.kz
  chmod 600 infra/.env.kz
}

echo "=== [$(date -Is)] Kazakhstan standby готов. Активация: docs/DISASTER_RECOVERY.md §4 ==="
