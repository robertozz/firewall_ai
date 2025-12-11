"""
nft_utils.py

Utility per lavorare con nftables in modo idempotente e sicuro.

Funzioni principali:
- check_nft_available(): verifica che il comando `nft` sia presente
- check_net_admin(): verifica permessi di esecuzione su nft
- ensure_table_chains_sets(): crea table/chain/sets e le regole che usano i set (se mancanti)
- ensure_set(): crea un set usando un file temporaneo e `nft -f`
- ensure_chain(): crea una chain usando un file temporaneo e `nft -f`
- rule_exists(): controllo non fallibile per regole singole
- flush_rules(): flush dell'intero ruleset

Note:
- Per definizioni complesse (graffe, punti e virgola) usiamo file temporanei e `nft -f`
  per evitare problemi di escaping/quoting tra shell/versioni.
- Le funzioni sono idempotenti: possono essere chiamate ripetutamente senza effetti collaterali.
"""

import subprocess
import tempfile
from pathlib import Path
import time
from typing import Optional


def check_nft_available() -> None:
    """
    Verifica che il comando `nft` sia disponibile.
    Solleva RuntimeError in caso di problemi.
    """
    try:
        subprocess.run(["nft", "--version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        raise RuntimeError("Comando 'nft' non trovato. Assicurati che nftables sia installato.")
    except subprocess.CalledProcessError:
        raise RuntimeError("Errore nell'esecuzione di 'nft'.")


def check_net_admin() -> None:
    """
    Verifica che il processo abbia i permessi necessari per interrogare/applicare nft.
    Solleva RuntimeError se la chiamata fallisce.
    """
    try:
        subprocess.run(["nft", "list", "tables"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        raise RuntimeError("Il processo non ha permessi NET_ADMIN o nft non risponde correttamente.")


def _write_and_apply_nft(content: str) -> None:
    """
    Scrive content su file temporaneo e lo applica con `nft -f`.
    Rimuove il file temporaneo alla fine.
    """
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile("w", delete=False, prefix="nft_tmp_", suffix=".nft") as fh:
            tmp_path = Path(fh.name)
            fh.write(content)
        subprocess.run(["nft", "-f", str(tmp_path)], check=True)
    finally:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass

def ensure_set(set_name: str, elements: list = None) -> None:
    """
    Crea il set `set_name` in table inet filter se non esiste.
    Se elements è None o vuoto, crea il set senza la riga `elements = { }`
    (alcune versioni di nft non accettano elementi vuoti).
    """
    try:
        subprocess.run(["nft", "list", "set", "inet", "filter", set_name],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    except subprocess.CalledProcessError:
        pass

    elems = elements or []
    if elems:
        elems_str = ", ".join(str(int(e)) for e in elems)
        content = (
            "table inet filter {\n"
            f"  set {set_name} {{\n"
            "    type inet_service;\n"
            "    flags interval;\n"
            f"    elements = {{ {elems_str} }}\n"
            "  }\n"
            "}\n"
        )
    else:
        # crea il set vuoto senza la linea `elements = { }`
        content = (
            "table inet filter {\n"
            f"  set {set_name} {{\n"
            "    type inet_service;\n"
            "    flags interval;\n"
            "  }\n"
            "}\n"
        )

    _write_and_apply_nft(content)

def ensure_chain(name: str, definition_body: str) -> None:
    """
    Crea la chain `name` nella table inet filter se non esiste.
    definition_body è il corpo della chain, ad esempio:
      'type filter hook input priority 0; policy drop;'
    La funzione costruisce un file .nft con la definizione completa e lo applica.
    """
    try:
        subprocess.run(["nft", "list", "chain", "inet", "filter", name],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    except subprocess.CalledProcessError:
        pass

    # costruiamo il file nft con la chain completa (body già include i ';' se necessari)
    content = (
        "table inet filter {\n"
        f"  chain {name} {{ {definition_body} }}\n"
        "}\n"
    )
    _write_and_apply_nft(content)


def ensure_table_chains_sets(policy: str = "drop") -> None:
    """
    Assicura che esistano:
      - table inet filter
      - chain input/forward/output con hook e policy
      - set tcp_services e udp_services
      - regole che usano i set (@tcp_services, @udp_services) nella chain input

    La funzione è idempotente e può essere chiamata più volte.
    """
    # 1) table
    try:
        subprocess.run(["nft", "list", "table", "inet", "filter"],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        subprocess.run(["nft", "add", "table", "inet", "filter"], check=True)

    # 2) chains (usiamo file temporanei per definizioni complesse)
    ensure_chain("input", f"type filter hook input priority 0; policy {policy};")
    ensure_chain("forward", "type filter hook forward priority 0; policy accept;")
    ensure_chain("output", "type filter hook output priority 0; policy accept;")

    # 3) sets
    ensure_set("tcp_services")
    ensure_set("udp_services")

    # 4) regole che usano i set (aggiungile solo se mancano)
    try:
        out = subprocess.run(["nft", "list", "chain", "inet", "filter", "input"],
                             check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        stdout = out.stdout or ""
        if "tcp dport @tcp_services accept" not in stdout:
            subprocess.run(["nft", "add", "rule", "inet", "filter", "input", "tcp", "dport", "@tcp_services", "accept"], check=True)
        if "udp dport @udp_services accept" not in stdout:
            subprocess.run(["nft", "add", "rule", "inet", "filter", "input", "udp", "dport", "@udp_services", "accept"], check=True)
    except subprocess.CalledProcessError:
        # se list chain fallisce, ignoriamo: le chain dovrebbero essere state create sopra
        pass


def rule_exists(proto: str, port: int) -> bool:
    """
    Controlla se esiste una regola esplicita 'proto dport port accept' nella chain input.
    Non solleva eccezioni se la chain/table non esistono; ritorna False in quel caso.
    """
    try:
        p = subprocess.run(["nft", "list", "chain", "inet", "filter", "input"],
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        needle = f"{proto} dport {port} accept"
        return needle in (p.stdout or "")
    except subprocess.CalledProcessError:
        return False


def flush_rules() -> None:
    """
    Flush dell'intero ruleset. Operazione distruttiva: usala con cautela.
    """
    subprocess.run(["nft", "flush", "ruleset"], check=True)


def _retry_cmd(cmd, retries=3, delay=1, shell=False):
    """
    Esegue un comando con retry semplice. cmd può essere lista (shell=False) o stringa (shell=True).
    Restituisce l'oggetto CompletedProcess dell'ultima esecuzione o solleva l'eccezione finale.
    """
    last_exc: Optional[Exception] = None
    for attempt in range(retries):
        try:
            if shell:
                return subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            else:
                return subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except Exception as e:
            last_exc = e
            time.sleep(delay)
    raise last_exc
