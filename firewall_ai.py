#!/usr/bin/env python3
"""
Entrypoint minimale: delega a cli.run_cli()
Mantieni questo file piccolo: tutta la logica è nei moduli.
"""
import os, sys, atexit, logging
from pathlib import Path
from cli import run_cli

# --- Lockfile per evitare esecuzioni concorrenti ---
LOCKFILE = "/var/run/firewall_ai.lock"

def acquire_lock():
    if os.path.exists(LOCKFILE):
        print("Lockfile presente, un'altra istanza è attiva. Esco.")
        sys.exit(1)
    Path(LOCKFILE).write_text(str(os.getpid()))
    # rimuovi lockfile alla fine
    atexit.register(release_lock)

def release_lock():
    try:
        os.remove(LOCKFILE)
    except FileNotFoundError:
        pass

# --- Logging resiliente ---
DEFAULT_LOG_DIR = os.environ.get("FIREWALL_AI_LOG_DIR", "/home/roberto/docker-stacks/firewall_ai/log")
Path(DEFAULT_LOG_DIR).mkdir(parents=True, exist_ok=True)
LOG_FILE = os.path.join(DEFAULT_LOG_DIR, "system.log")

logger = logging.getLogger("firewall_ai")
logger.setLevel(logging.INFO)

try:
    fh = logging.FileHandler(LOG_FILE)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(fh)
except Exception:
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(sh)

# --- Acquisizione lock all'avvio ---
acquire_lock()

if __name__ == "__main__":
    run_cli()

