"""
Logica per sincronizzare i servizi con i set nft.
- add_service_element: aggiunge elemento al set se mancante
- apply_rule: high-level, chiama ensure_table_chains_sets e add_service_element
"""
import subprocess
from nft_utils import ensure_table_chains_sets
from telegram_utils import notify_markdown
from typing import Dict

def element_in_set(set_name: str, port: int) -> bool:
    try:
        out = subprocess.run(["nft", "list", "set", "inet", "filter", set_name], check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        return str(port) in out.stdout
    except subprocess.CalledProcessError:
        return False

def add_service_element(proto: str, port: int) -> bool:
    set_name = "tcp_services" if proto == "tcp" else "udp_services"
    if element_in_set(set_name, port):
        return False
    subprocess.run(["nft", "add", "element", "inet", "filter", set_name, "{", str(port), "}"], check=True)
    return True

def apply_rule(service: Dict, dry_run: bool = False):
    port = service["port"]
    proto = service["protocol"]
    name = service["name"]

    ensure_table_chains_sets()

    if dry_run:
        print(f"[DRY RUN] add element {port}/{proto} to set")
        return

    try:
        added = add_service_element(proto, port)
        if added:
            notify_markdown(f"✅ Aggiunto {name} ({port}/{proto}) a @{'tcp_services' if proto=='tcp' else 'udp_services'}")
        else:
            # non inviamo notifica per skip per evitare flood
            pass
    except subprocess.CalledProcessError as e:
        notify_markdown(f"❌ Errore aggiunta elemento {name} ({port}/{proto}): {e}")
