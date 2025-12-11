"""
Parsing della configurazione e valori di default.
Espone load_services(base_dir) che ritorna lista di dict:
[{"name":..., "port":..., "protocol":...}, ...]
"""
from pathlib import Path
import sys

DEFAULT_BASE_DIR = "/home/roberto/docker-stacks/firewall_ai"

try:
    import yaml
except Exception:
    yaml = None

def load_services(base_dir=None, services_path="config/services.yaml"):
    """
    Legge config/services.yaml e ritorna lista di dict.
    Se PyYAML non è installato ritorna lista vuota e stampa istruzioni.
    """
    if base_dir:
        base = Path(base_dir).expanduser().resolve()
    else:
        try:
            base = Path(__file__).parent.resolve()
        except Exception:
            base = Path.cwd()

    services_file = base / services_path
    if not services_file.exists():
        print(f"WARN: services file non trovato: {services_file}", file=sys.stderr)
        return []

    if yaml is None:
        print("ERR: PyYAML non installato. Installa con: sudo apt install python3-yaml OR pip3 install pyyaml", file=sys.stderr)
        return []

    try:
        raw = yaml.safe_load(services_file.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"ERR: parsing {services_file}: {e}", file=sys.stderr)
        return []

    if not isinstance(raw, dict):
        print(f"WARN: formato invalido in {services_file}", file=sys.stderr)
        return []

    entries = []
    services = raw.get("allowed_services") or []
    for item in services:
        try:
            name = item.get("name") or item.get("service") or "unknown"
            port = int(item.get("port"))
            proto = (item.get("protocol") or "tcp").lower()
            if proto not in ("tcp", "udp"):
                proto = "tcp"
            entries.append({"name": name, "port": port, "protocol": proto})
        except Exception:
            print(f"WARN: salto voce malformata in services.yaml: {item}", file=sys.stderr)
            continue

    return entries
