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
