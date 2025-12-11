import os

def write_file(path, content):
    if os.path.exists(path):
        print(f"❌ {path} già esiste, salto.")
        return
    with open(path, "w") as f:
        f.write(content)
    print(f"✅ Creato: {path}")

# Directory setup
os.makedirs("config", exist_ok=True)
os.makedirs("utils", exist_ok=True)
os.makedirs("logs", exist_ok=True)

# services.yaml
write_file("config/services.yaml", """allowed_services:
  - name: ssh
    port: 22
    protocol: tcp
  - name: http
    port: 80
    protocol: tcp
  - name: mqtt
    port: 1883
    protocol: tcp
""")

# nft.py
write_file("utils/nft.py", """import subprocess

def apply_rule(port, protocol, action="accept"):
    cmd = f"nft add rule inet filter input {protocol} dport {port} {action}"
    subprocess.run(cmd, shell=True)

def drop_rule(port, protocol):
    cmd = f"nft add rule inet filter input {protocol} dport {port} drop"
    subprocess.run(cmd, shell=True)

def flush_rules():
    subprocess.run("nft flush ruleset", shell=True)
""")

# monitor.py
write_file("utils/monitor.py", """import psutil

def get_active_ports():
    connections = psutil.net_connections()
    active = set()
    for conn in connections:
        if conn.status == "LISTEN":
            active.add((conn.laddr.port, conn.type))
    return active
""")

# notifier.py (riutilizzabile come telegram_utils.py)
write_file("utils/notifier.py", """import requests

def notify(message):
    token = "YOUR_TELEGRAM_BOT_TOKEN"
    chat_id = "YOUR_CHAT_ID"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": message})
""")

# health.py
write_file("utils/health.py", """import subprocess
import socket

def check_adguard(port=3000):
    try:
        sock = socket.create_connection(("127.0.0.1", port), timeout=2)
        sock.close()
        return True
    except Exception:
        return False

def check_nftables_rule(port, protocol):
    cmd = f"nft list ruleset"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return f"{protocol} dport {port}" in result.stdout

def check_dns(domain="example.com"):
    try:
        resolved = socket.gethostbyname(domain)
        return resolved != ""
    except Exception:
        return False
""")

# firewall_ai.py
write_file("firewall_ai.py", """import time
import yaml
from utils import nft, monitor, notifier, health

def load_config():
    with open("config/services.yaml") as f:
        return yaml.safe_load(f)["allowed_services"]

def health_check():
    if not health.check_adguard():
        notifier.notify("⚠️ AdGuard non risponde sulla porta 3000")
    if not health.check_dns():
        notifier.notify("⚠️ DNS non risolto tramite AdGuard/Unbound")
    for s in load_config():
        if not health.check_nftables_rule(s["port"], s["protocol"]):
            notifier.notify(f"⚠️ Regola nftables mancante per {s['name']} ({s['port']}/{s['protocol']})")

def main():
    allowed = {(s["port"], s["protocol"]) for s in load_config()}
    nft.flush_rules()
    counter = 0

    while True:
        active = monitor.get_active_ports()
        for port, proto in active:
            proto_str = "tcp" if proto == 1 else "udp"
            if (port, proto_str) in allowed:
                nft.apply_rule(port, proto_str)
            else:
                nft.drop_rule(port, proto_str)
                notifier.notify(f"Bloccato servizio non autorizzato su porta {port}/{proto_str}")

        if counter % 6 == 0:
            health_check()

        counter += 1
        time.sleep(10)

if __name__ == "__main__":
    main()
""")
