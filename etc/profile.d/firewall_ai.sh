# firewall_ai global helpers (opt-out with NO_FIREWALL_AI=1)
if [ -z "${NO_FIREWALL_AI:-}" ]; then
  # Detect primary admin home if installed by root; fallback to /home/roberto
  FIREWALL_AI_DIR="${FIREWALL_AI_DIR:-/home/roberto/docker-stacks/firewall_ai}"
  export FIREWALL_AI_DIR
  export FIREWALL_AI_RULES="$FIREWALL_AI_DIR/rules/firewall.rules"

  alias fw-dry="python3 \$FIREWALL_AI_DIR/firewall_ai.py --dry-run"
  alias fw-apply="sudo python3 \$FIREWALL_AI_DIR/firewall_ai.py"
  alias fw-list="sudo nft list chain inet filter input -a"
fi
