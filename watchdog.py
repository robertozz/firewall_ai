"""
Watchdog minimale: esegue flush_queue e può essere esteso per controllare rete/docker.
Pensato per essere chiamato da systemd timer ogni N minuti.
"""
from telegram_utils import flush_queue

def run_watchdog():
    # qui puoi aggiungere controlli di rete, DNS, stato container e ripristino rules
    flush_queue()

if __name__ == "__main__":
    run_watchdog()
