import subprocess

def apply_rule(port, protocol, action="accept"):
    cmd = f"nft add rule inet filter input {protocol} dport {port} {action}"
    subprocess.run(cmd, shell=True)

def drop_rule(port, protocol):
    cmd = f"nft add rule inet filter input {protocol} dport {port} drop"
    subprocess.run(cmd, shell=True)

def flush_rules():
    subprocess.run("nft flush ruleset", shell=True)
