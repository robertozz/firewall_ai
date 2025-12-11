import subprocess
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
