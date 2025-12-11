#!/usr/bin/env python3
import os, sys, yaml, psutil

CONFIG_PATH = "config/services.yaml"

"""
update_services.py – Gestione interattiva di config/services.yaml

UTILIZZO:
  python utils/update_services.py --list
      Mostra le porte attive e i processi che le usano.
      ⚠️ Nota: per vedere i nomi dei processi è necessario eseguire come root
      (es. sudo python utils/update_services.py --list).

  python utils/update_services.py --add <name> <port> <protocol>
      Aggiunge un nuovo servizio a services.yaml.
      Esempio: python utils/update_services.py --add dns 53 udp

  python utils/update_services.py --remove <port> <protocol>
      Rimuove un servizio da services.yaml.
      Esempio: python utils/update_services.py --remove 53 udp

  python utils/update_services.py --sync
      Sincronizza automaticamente services.yaml:
        - aggiunge i servizi attivi mancanti
        - rimuove quelli non più in ascolto

  python utils/update_services.py
      Avvia la modalità interattiva:
        - mostra le porte attive
        - evidenzia in verde quelle già presenti in services.yaml
        - evidenzia in rosso quelle attive ma non autorizzate
        - evidenzia in giallo quelle presenti in YAML ma non più attive
        - permette di aggiungere o rimuovere servizi con prompt a scelta

NOTE:
- Il file di configurazione è: config/services.yaml
- Ogni servizio è definito come:
    - name: nome descrittivo
      port: numero porta
      protocol: tcp|udp
"""

# ANSI colori
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def load_services():
    if not os.path.exists(CONFIG_PATH):
        return []
    with open(CONFIG_PATH) as f:
        data = yaml.safe_load(f) or {}
    return data.get("allowed_services", [])

def save_services(services):
    with open(CONFIG_PATH, "w") as f:
        yaml.safe_dump({"allowed_services": services}, f, sort_keys=False)

def list_active_ports():
    conns = psutil.net_connections(kind="inet")
    active = {}
    for c in conns:
        if c.status == "LISTEN":
            port = c.laddr.port
            proto = "tcp" if c.type == 1 else "udp"
            pid = c.pid
            proc = "?"
            if pid:
                try:
                    proc = psutil.Process(pid).name()
                except Exception:
                    pass
            active[(port, proto)] = proc
    return active

def interactive():
    services = load_services()
    allowed = {(s["port"], s["protocol"]) for s in services}
    active = list_active_ports()

    print("\n🔍 Stato porte e servizi:\n")
    for (port, proto), proc in active.items():
        if (port, proto) in allowed:
            print(f"{GREEN}{port}/{proto}{RESET} → {proc} (già in services.yaml)")
        else:
            print(f"{RED}{port}/{proto}{RESET} → {proc} (NON autorizzato)")

    for s in services:
        if (s["port"], s["protocol"]) not in active:
            print(f"{YELLOW}{s['port']}/{s['protocol']}{RESET} → {s['name']} (in YAML ma non attivo)")

    print("\nOpzioni:")
    print("  [a] Aggiungi servizi mancanti")
    print("  [r] Rimuovi servizi inutilizzati")
    print("  [q] Esci senza modifiche")

    choice = input("\nSeleziona opzione: ").strip().lower()
    if choice == "a":
        for (port, proto), proc in active.items():
            if (port, proto) not in allowed:
                ans = input(f"Aggiungere {port}/{proto} ({proc})? [y/N] ").strip().lower()
                if ans == "y":
                    name = input("  Nome servizio: ").strip() or proc
                    services.append({"name": name, "port": port, "protocol": proto})
    elif choice == "r":
        for s in services[:]:
            if (s["port"], s["protocol"]) not in active:
                ans = input(f"Rimuovere {s['port']}/{s['protocol']} ({s['name']})? [y/N] ").strip().lower()
                if ans == "y":
                    services.remove(s)
    else:
        print("❌ Nessuna modifica.")
        return

    save_services(services)
    print("✅ services.yaml aggiornato.")

def sync_services():
    services = load_services()
    allowed = {(s["port"], s["protocol"]) for s in services}
    active = list_active_ports()

    # Aggiungi mancanti
    for (port, proto), proc in active.items():
        if (port, proto) not in allowed:
            services.append({"name": proc or f"svc_{port}", "port": port, "protocol": proto})
            print(f"➕ Aggiunto {port}/{proto} ({proc})")

    # Rimuovi non più attivi
    for s in services[:]:
        if (s["port"], s["protocol"]) not in active:
            services.remove(s)
            print(f"➖ Rimosso {s['port']}/{s['protocol']} ({s['name']})")

    save_services(services)
    print("✅ services.yaml sincronizzato.")


if __name__ == "__main__":
    if "--list" in sys.argv:
        for (port, proto), proc in list_active_ports().items():
            print(f"{port}/{proto} → {proc}")
    elif "--add" in sys.argv and len(sys.argv) == 5:
        _, _, name, port, proto = sys.argv
        services = load_services()
        services.append({"name": name, "port": int(port), "protocol": proto})
        save_services(services)
        print(f"✅ Aggiunto {name} ({port}/{proto})")
    elif "--remove" in sys.argv and len(sys.argv) == 4:
        _, _, port, proto = sys.argv
        services = load_services()
        services = [s for s in services if not (s["port"] == int(port) and s["protocol"] == proto)]
        save_services(services)
        print(f"✅ Rimosso servizio {port}/{proto}")
    elif "--sync" in sys.argv:
        sync_services()
    else:
        interactive()
