#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/roberto/docker-stacks/firewall_ai"
UNIT_SRC="$(dirname "$0")/../systemd/firewall-ai.service"
UNIT_DST="/etc/systemd/system/firewall-ai.service"

echo "Copying unit file to ${UNIT_DST}"
sudo cp "${UNIT_SRC}" "${UNIT_DST}"
sudo chown root:root "${UNIT_DST}"
sudo chmod 644 "${UNIT_DST}"

echo "Reloading systemd and enabling service"
sudo systemctl daemon-reload
sudo systemctl enable --now firewall-ai.service

echo "Done. Check status with: sudo systemctl status firewall-ai.service"
