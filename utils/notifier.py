"""
notifier.py – Logging JSON locale per eventi firewall

Scrive eventi in logs/firewall.log in formato compatibile con log_to_html.py.
Separato dalle notifiche Telegram per modularità.
"""

import json
from datetime import datetime

LOG_PATH = "logs/firewall.log"

def log(level, message):
    entry = {
        "timestamp": datetime.now().isoformat(timespec='seconds'),
        "level": level,
        "message": message
    }
    try:
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"Errore nel logging: {e}")
