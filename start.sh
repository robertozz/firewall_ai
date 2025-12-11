#!/bin/bash

echo "🔧 Avvio agente firewall AI..."

# Controllo file essenziali
REQUIRED_FILES=(
  "firewall_ai.py"
  "config/services.yaml"
  "config/telegram.json"
  "utils/nft.py"
  "utils/monitor.py"
  "utils/notifier.py"
  "utils/health.py"
  "utils/log_to_html.py"
  "utils/telegram_utils.py"
)

for file in "${REQUIRED_FILES[@]}"; do
  if [ ! -f "$file" ]; then
    echo "❌ File mancante: $file"
    exit 1
  fi
done

# Avvio agente
python3 firewall_ai.py &

# Monitoraggio log
sleep 2
echo "📄 Log in tempo reale:"
tail -f logs/firewall.log
