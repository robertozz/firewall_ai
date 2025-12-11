"""
Generazione atomica del file rules/firewall.rules.
- Legge config/services.yaml (tramite config.load_services)
- Deduplica e ordina le porte
- Scrive il file in modo atomico (tmp -> replace)
- Il file generato usa set @tcp_services e @udp_services e una regola che li usa
"""
from pathlib import Path
import stat, sys
from config import load_services, DEFAULT_BASE_DIR

DEFAULT_RULES = {
    "lan_cidr": "192.168.1.0/24",
    "policy": "drop",
    "allow_icmp": True
}

def render_nft_rules(lan_cidr, tcp_ports, udp_ports, policy="drop", allow_icmp=True):
    """
    Restituisce il contenuto testuale del file nftables basato sui parametri.
    Usa doppie graffe {{ }} nelle f-string per produrre parentesi graffe letterali.
    """
    tcp_set = sorted({int(p) for p in tcp_ports})
    udp_set = sorted({int(p) for p in udp_ports})

    tcp_elements = ", ".join(str(p) for p in tcp_set)
    udp_elements = ", ".join(str(p) for p in udp_set)

    # se non ci sono elementi, scriviamo un set vuoto senza spazi inutili
    tcp_elements_field = tcp_elements if tcp_elements else ""
    udp_elements_field = udp_elements if udp_elements else ""

    content = "#!/usr/sbin/nft -f\n"
    content += "table inet filter {\n"

    # tcp set
    if tcp_elements_field:
        content += "  set tcp_services {\n"
        content += "    type inet_service\n"
        content += "    flags interval\n"
        content += f"    elements = {{ {tcp_elements_field} }}\n"
        content += "  }\n\n"
    else:
        # crea comunque il set vuoto (utile per idempotenza)
        content += "  set tcp_services {\n"
        content += "    type inet_service\n"
        content += "    flags interval\n"
        content += "    elements = { }\n"
        content += "  }\n\n"

    # udp set
    if udp_elements_field:
        content += "  set udp_services {\n"
        content += "    type inet_service\n"
        content += "    flags interval\n"
        content += f"    elements = {{ {udp_elements_field} }}\n"
        content += "  }\n\n"
    else:
        content += "  set udp_services {\n"
        content += "    type inet_service\n"
        content += "    flags interval\n"
        content += "    elements = { }\n"
        content += "  }\n\n"

    # chain input
    content += f"  chain input {{\n    type filter hook input priority 0; policy {policy};\n"
    content += "    ct state established,related accept\n"
    content += '    iif "lo" accept\n'
    content += f"    ip saddr {lan_cidr} accept\n\n"
    content += "    tcp dport @tcp_services accept\n"
    content += "    udp dport @udp_services accept\n"
    if allow_icmp:
        content += "    icmp type echo-request accept\n"
    content += "  }\n\n"
    content += "  chain forward { type filter hook forward priority 0; policy accept; }\n"
    content += "  chain output  { type filter hook output priority 0; policy accept; }\n"
    content += "}\n"
    return content

def ensure_rules_file_from_services(base_dir: str = DEFAULT_BASE_DIR, cfg: dict = None, services_cfg_path: str = "config/services.yaml", extra_dirs=None) -> bool:
    cfg = cfg or DEFAULT_RULES
    base = Path(base_dir).expanduser().resolve()
    try:
        dirs = ["rules", "logs", "data"]
        if extra_dirs:
            dirs += list(extra_dirs)
        for d in dirs:
            (base / d).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"ERROR: cannot create directories under {base}: {e}", file=sys.stderr)
        return False

    services = load_services(base_dir)
    tcp_ports = {s["port"] for s in services if s["protocol"] == "tcp"}
    udp_ports = {s["port"] for s in services if s["protocol"] == "udp"}

    content = render_nft_rules(
        lan_cidr=cfg.get("lan_cidr", DEFAULT_RULES["lan_cidr"]),
        tcp_ports=tcp_ports,
        udp_ports=udp_ports,
        policy=cfg.get("policy", DEFAULT_RULES["policy"]),
        allow_icmp=cfg.get("allow_icmp", DEFAULT_RULES["allow_icmp"])
    )

    rules_file = base / "rules" / "firewall.rules"
    try:
        tmp = rules_file.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(content)
        tmp.chmod(0o644)
        tmp.replace(rules_file)
        rules_file.chmod(rules_file.stat().st_mode | stat.S_IXUSR)
        return True
    except Exception as e:
        print(f"ERROR writing rules file {rules_file}: {e}", file=sys.stderr)
        return False
