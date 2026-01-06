#!/usr/bin/env bash
set -euo pipefail

# Simple installer for firewall_ai (user-level by default)
# Usage:
#   ./scripts/install.sh            # install user-level helpers
#   sudo ./scripts/install.sh --systemd   # install and enable systemd unit (requires sudo)
#   sudo ./scripts/install.sh --system  # install system-wide profile in /etc/profile.d (requires sudo)
#   sudo ./scripts/install.sh --systemd --system

# -------------------------
# Configurazione iniziale
# -------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR_DEFAULT="$HOME/docker-stacks/firewall_ai"
SYSTEMD_SRC="$SCRIPT_DIR/../systemd/firewall-ai.service"
SYSTEMD_DST="/etc/systemd/system/firewall-ai.service"
PROFILE_REPO_SRC="$SCRIPT_DIR/firewall_ai_profile.sh"
PROFILE_USER_DST=".firewall_ai_profile"
MOTD_USER_DST=".firewall_ai_motd"
LOG_DIR_DEFAULT="$HOME/docker-stacks/firewall_ai/log"

# Flags
INSTALL_SYSTEMD=false
INSTALL_SYSTEM_WIDE=false
GROUP_NAME="firewalladmins"

# Parse args
for arg in "$@"; do
  case "$arg" in
    --systemd) INSTALL_SYSTEMD=true ;;
    --system) INSTALL_SYSTEM_WIDE=true ;;
    *) ;;
  esac
done

# -------------------------
# Determine target user/home (works with or without sudo)
# -------------------------
if [ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != "root" ]; then
  TARGET_USER="$SUDO_USER"
else
  TARGET_USER="${USER:-$(id -un)}"
fi

TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"
if [ -z "$TARGET_HOME" ]; then
  echo "Impossibile determinare la home di $TARGET_USER" >&2
  exit 1
fi

PROJECT_DIR="${PROJECT_DIR_DEFAULT/#$HOME/$TARGET_HOME}"
LOG_DIR="${LOG_DIR_DEFAULT/#$HOME/$TARGET_HOME}"

echo "Installer running for user: $TARGET_USER"
echo "Project dir: $PROJECT_DIR"
echo "Log dir: $LOG_DIR"

# -------------------------
# Ensure project layout exists (when running from repo)
# -------------------------
mkdir -p "$PROJECT_DIR"
mkdir -p "$LOG_DIR"
chown -R "$TARGET_USER":"$TARGET_USER" "$PROJECT_DIR" || true

# If repo files are in a different location (e.g., you cloned elsewhere), copy only if target empty
if [ -d "$SCRIPT_DIR/.." ] && [ "$(ls -A "$PROJECT_DIR" 2>/dev/null || true)" = "" ]; then
  echo "Popolamento directory progetto da repo locale"
  cp -a "$SCRIPT_DIR/.."/* "$PROJECT_DIR/" || true
  chown -R "$TARGET_USER":"$TARGET_USER" "$PROJECT_DIR"
fi

# -------------------------
# Install user profile helper
# -------------------------
PROFILE_SRC_IN_REPO="$PROJECT_DIR/scripts/firewall_ai_profile.sh"
PROFILE_DST="$TARGET_HOME/$PROFILE_USER_DST"
BASH_PROFILE="$TARGET_HOME/.bash_profile"
BASHRC="$TARGET_HOME/.bashrc"

# Ensure scripts dir exists in repo
mkdir -p "$PROJECT_DIR/scripts"
chown "$TARGET_USER":"$TARGET_USER" "$PROJECT_DIR/scripts" || true

# Create the profile helper in the repo (idempotent)
cat > "$PROFILE_SRC_IN_REPO" <<'EOF'
# firewall_ai helpers
export FIREWALL_AI_DIR="$HOME/docker-stacks/firewall_ai"
export FIREWALL_AI_RULES="$FIREWALL_AI_DIR/rules/firewall.rules"
alias fw-dry="python3 $FIREWALL_AI_DIR/firewall_ai.py --dry-run"
alias fw-apply="sudo python3 $FIREWALL_AI_DIR/firewall_ai.py"
alias fw-list="sudo nft list chain inet filter input -a"
alias fw-sets="sudo nft list set inet filter tcp_services || true; sudo nft list set inet filter udp_services || true"

fw-add-tcp() {
  [ -z "$1" ] && { echo "Uso: fw-add-tcp <porta>"; return 1; }
  sudo nft add element inet filter tcp_services { $1/tcp } 2>/dev/null || echo "Possibile duplicato o errore"
  sudo nft list set inet filter tcp_services
}
fw-rm-tcp() {
  [ -z "$1" ] && { echo "Uso: fw-rm-tcp <porta>"; return 1; }
  sudo nft delete element inet filter tcp_services { $1/tcp } 2>/dev/null || echo "Non esiste o errore"
  sudo nft list set inet filter tcp_services
}
fw-add-udp() {
  [ -z "$1" ] && { echo "Uso: fw-add-udp <porta>"; return 1; }
  sudo nft add element inet filter udp_services { $1/udp } 2>/dev/null || echo "Possibile duplicato o errore"
  sudo nft list set inet filter udp_services
}
fw-rm-udp() {
  [ -z "$1" ] && { echo "Uso: fw-rm-udp <porta>"; return 1; }
  sudo nft delete element inet filter udp_services { $1/udp } 2>/dev/null || echo "Non esiste o errore"
  sudo nft list set inet filter udp_services
}
fw-regenerate-and-apply() {
  echo "Genero rules/firewall.rules e applico"
  sudo python3 "$FIREWALL_AI_DIR/firewall_ai.py" || { echo "Errore generazione"; return 1; }
  sudo nft -f "$FIREWALL_AI_RULES" || { echo "Errore applicazione"; return 1; }
  echo "Fatto"
}
fw-readme() {
  local repo_url="https://github.com/robertozz/firewall_ai"
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$repo_url"
  else
    echo "Apri il README: $repo_url"
  fi
}
EOF

# Copy helper to user's home
cp -f "$PROFILE_SRC_IN_REPO" "$PROFILE_DST"
chown "$TARGET_USER":"$TARGET_USER" "$PROFILE_DST"
chmod 644 "$PROFILE_DST"

# Ensure .bash_profile exists and add sourcing if missing
if [ ! -f "$BASH_PROFILE" ]; then
  touch "$BASH_PROFILE"
  chown "$TARGET_USER":"$TARGET_USER" "$BASH_PROFILE"
fi

if ! grep -qxF 'source $HOME/.firewall_ai_profile' "$BASH_PROFILE" 2>/dev/null; then
  echo '' >> "$BASH_PROFILE"
  echo 'source $HOME/.firewall_ai_profile' >> "$BASH_PROFILE"
fi

# Also ensure interactive shells load it via .bashrc
if [ ! -f "$BASHRC" ]; then
  touch "$BASHRC"
  chown "$TARGET_USER":"$TARGET_USER" "$BASHRC"
fi

if ! grep -qxF 'source $HOME/.firewall_ai_profile' "$BASHRC" 2>/dev/null; then
  echo '' >> "$BASHRC"
  echo 'source $HOME/.firewall_ai_profile' >> "$BASHRC"
fi

# -------------------------
# Install SSH login summary (user-level motd)
# -------------------------
MOTD_FILE="$TARGET_HOME/$MOTD_USER_DST"

cat > "$MOTD_FILE" <<'EOF'
echo ""
echo "=== Firewall AI ==="
echo "fw-dry        → Simula le modifiche senza applicarle"
echo "fw-apply      → Applica le regole"
echo "fw-add-tcp N  → Aggiunge porta TCP N"
echo "fw-rm-tcp N   → Rimuove porta TCP N"
echo "fw-add-udp N  → Aggiunge porta UDP N"
echo "fw-rm-udp N   → Rimuove porta UDP N"
echo "fw-readme     → Apri il README del progetto"
echo ""
EOF

chown "$TARGET_USER":"$TARGET_USER" "$MOTD_FILE"
chmod 644 "$MOTD_FILE"

# Add conditional sourcing to .bash_profile for SSH sessions (idempotent)
if ! grep -q "firewall_ai_motd" "$BASH_PROFILE"; then
  {
    echo ''
    echo '# Mostra il riassunto firewall_ai solo in sessioni SSH'
    echo 'if [ -n "$SSH_CONNECTION" ] && [ -f "$HOME/.firewall_ai_motd" ]; then'
    echo '    source "$HOME/.firewall_ai_motd"'
    echo 'fi'
  } >> "$BASH_PROFILE"
fi

# -------------------------
# Create log dir and ensure permissions
# -------------------------
mkdir -p "$LOG_DIR"
chown -R "$TARGET_USER":"$TARGET_USER" "$LOG_DIR"
chmod 755 "$LOG_DIR"

# -------------------------
# Helper: create admin group and add user
# -------------------------
create_admin_group() {
  if ! getent group "$GROUP_NAME" >/dev/null 2>&1; then
    echo "Creazione gruppo $GROUP_NAME"
    # prefer system group if possible
    if command -v groupadd >/dev/null 2>&1; then
      groupadd --system "$GROUP_NAME" 2>/dev/null || groupadd "$GROUP_NAME" 2>/dev/null || true
    fi
  fi

  # Add target user to group (idempotent)
  if id -nG "$TARGET_USER" | grep -qw "$GROUP_NAME"; then
    echo "Utente $TARGET_USER già membro di $GROUP_NAME"
  else
    usermod -aG "$GROUP_NAME" "$TARGET_USER" 2>/dev/null || true
    echo "Aggiunto $TARGET_USER a $GROUP_NAME"
  fi
}

# -------------------------
# Install systemd unit (requires root)
# -------------------------
install_systemd_unit() {
  local unit_src="$PROJECT_DIR/systemd/firewall-ai.service"
  local unit_dst="/etc/systemd/system/firewall-ai.service"
  if [ ! -f "$unit_src" ]; then
    echo "Unit systemd non trovata in $unit_src"
    return 1
  fi

  # Patch ExecStart with real project path
  sed "s|/home/%i/docker-stacks/firewall_ai/firewall_ai.py|$PROJECT_DIR/firewall_ai.py|g" "$unit_src" > /tmp/firewall-ai.service
  mv /tmp/firewall-ai.service "$unit_dst"
  chown root:root "$unit_dst"
  chmod 644 "$unit_dst"
  systemctl daemon-reload
  systemctl enable --now firewall-ai.service || true
  echo "Unit systemd installata e avviata (se possibile)."
}

# -------------------------
# Install system-wide profile (requires root)
# -------------------------
install_system_profile() {
  local sys_profile="/etc/profile.d/firewall_ai.sh"
  cat > "$sys_profile" <<'EOF'
# firewall_ai global helpers (opt-out with NO_FIREWALL_AI=1)
# Default: disabled for new users (NO_FIREWALL_AI=1)
export NO_FIREWALL_AI=1
if [ -z "${NO_FIREWALL_AI:-}" ]; then
  FIREWALL_AI_DIR="${FIREWALL_AI_DIR:-/home/roberto/docker-stacks/firewall_ai}"
  export FIREWALL_AI_DIR
  export FIREWALL_AI_RULES="$FIREWALL_AI_DIR/rules/firewall.rules"
  alias fw-dry="python3 \$FIREWALL_AI_DIR/firewall_ai.py --dry-run"
  alias fw-apply="sudo python3 \$FIREWALL_AI_DIR/firewall_ai.py"
  alias fw-list="sudo nft list chain inet filter input -a"
fi
EOF
  chmod 644 "$sys_profile"
  echo "Profile system-wide installato in $sys_profile (NO_FIREWALL_AI=1 di default)."
}

# -------------------------
# Install sudoers snippet for group (requires root)
# -------------------------
install_sudoers() {
  local sudoers_file="/etc/sudoers.d/firewall_ai"
  cat > "$sudoers_file" <<EOF
# firewall_ai sudoers (generated by install.sh)
%$GROUP_NAME ALL=(root) NOPASSWD: /usr/bin/python3 $PROJECT_DIR/firewall_ai.py, /usr/sbin/nft
EOF
  chmod 440 "$sudoers_file"
  echo "Sudoers snippet installato in $sudoers_file (gruppo: $GROUP_NAME)."
}

# -------------------------
# Conditional calls for system install
# -------------------------
if [ "$INSTALL_SYSTEMD" = true ]; then
  if [ "$(id -u)" -ne 0 ]; then
    echo "--systemd richiede sudo. Rilancia con sudo." >&2
    exit 1
  fi
  create_admin_group
  install_systemd_unit
  install_sudoers
fi

if [ "$INSTALL_SYSTEM_WIDE" = true ]; then
  if [ "$(id -u)" -ne 0 ]; then
    echo "--system richiede sudo. Rilancia con sudo." >&2
    exit 1
  fi
  create_admin_group
  install_system_profile
  install_sudoers
fi

# -------------------------
# Final messages and quick checks
# -------------------------
echo "Installazione completata per $TARGET_USER."
echo "Per attivare subito gli alias nella sessione corrente esegui:"
echo "  source $PROFILE_DST"
echo "Per vedere il riepilogo al prossimo login SSH, riconnettiti via SSH."
if [ "$INSTALL_SYSTEMD" = true ]; then
  echo "Controlla lo stato del servizio: sudo systemctl status firewall-ai.service"
fi

exit 0
