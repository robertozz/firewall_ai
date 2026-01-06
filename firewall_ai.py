#!/usr/bin/env python3
"""
Entrypoint minimale: delega a cli.run_cli()
Mantieni questo file piccolo: tutta la logica è nei moduli.
"""
import os, sys, atexit, logging
from pathlib import Path
from cli import run_cli
import errno

def _default_lock_path():
    # se siamo root, usa /var/run
    if os.geteuid() == 0:
        return "/var/run/firewall_ai.lock"
    # prova XDG_RUNTIME_DIR
    xdg = os.environ.get("XDG_RUNTIME_DIR")
    if xdg:
        return os.path.join(xdg, "firewall_ai.lock")
    # prova /run/user/<uid>
    run_user = f"/run/user/{os.geteuid()}"
    if os.path.isdir(run_user):
        return os.path.join(run_user, "firewall_ai.lock")
    # fallback su /tmp
    return os.path.join("/tmp", f"firewall_ai-{os.geteuid()}.lock")

# --- Lockfile per evitare esecuzioni concorrenti ---
LOCKFILE = _default_lock_path()


def acquire_lock():
    # crea la directory se necessario (solo per percorsi sotto home/runtime)
    lock_dir = os.path.dirname(LOCKFILE)
    try:
        Path(lock_dir).mkdir(parents=True, exist_ok=True)
    except Exception:
        # se non possiamo creare la dir, continueremo e tenteremo la creazione atomica del file
        pass

    pid = str(os.getpid()).encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        fd = os.open(LOCKFILE, flags, 0o644)
        with os.fdopen(fd, "wb") as f:
            f.write(pid)
    except OSError as e:
        if e.errno == errno.EEXIST:
            # lock già presente: leggi pid e verifica se il processo esiste
            try:
                existing = Path(LOCKFILE).read_text().strip()
                if existing.isdigit():
                    existing_pid = int(existing)
                    # se il processo non esiste, rimuovi il lock e riprova
                    try:
                        os.kill(existing_pid, 0)
                        print("Lockfile presente, un'altra istanza è attiva. Esco.")
                        sys.exit(1)
                    except OSError:
                        # processo non esistente: rimuovi lock e ricrea
                        try:
                            Path(LOCKFILE).unlink()
                            # riprova a creare
                            fd = os.open(LOCKFILE, flags, 0o644)
                            with os.fdopen(fd, "wb") as f:
                                f.write(pid)
                        except Exception:
                            print("Impossibile acquisire il lockfile. Esco.")
                            sys.exit(1)
                else:
                    print("Lockfile presente ma non valido. Esco.")
                    sys.exit(1)
            except Exception:
                print("Impossibile leggere il lockfile. Esco.")
                sys.exit(1)
        else:
            print(f"Errore creazione lockfile {LOCKFILE}: {e}. Esco.")
            sys.exit(1)

    # rimuovi lockfile all'uscita
    atexit.register(release_lock)

def release_lock():
    try:
        if os.path.exists(LOCKFILE):
            os.remove(LOCKFILE)
    except Exception:
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

