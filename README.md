# firewall_ai (modular)

Script per generare e mantenere regole nftables basate su `config/services.yaml`.
Questa versione è modularizzata per migliorare manutenibilità e testabilità.

## Struttura
- `firewall_ai.py` — entrypoint minimale
- `cli.py` — orchestrazione e CLI
- `config.py` — parsing `config/services.yaml`
- `rules_generator.py` — genera `rules/firewall.rules` (usa set @tcp_services/@udp_services)
- `nft_utils.py` — helper per table/chain/sets e controlli idempotenti
- `apply_rules.py` — sincronizza servizi con i set (aggiunge elementi mancanti)
- `telegram_utils.py` — notifiche resilienti (queue + flush)
- `watchdog.py` — watchdog eseguibile periodicamente
- `config/services.yaml` — file di input (vedi esempio sotto)

## Esempio config/services.yaml
```yaml
allowed_services:
  - name: ssh
    port: 22
    protocol: tcp
  - name: mqtt
    port: 1883
    protocol: tcp
  - name: HomeAssistant
    port: 8123
    protocol: tcp
  - name: Immich
    port: 2283
    protocol: tcp

## Requisiti
- Python 3.x
- nftables
- Permessi NET_ADMIN (eseguire come root o tramite systemd)

## Test
Eseguire in dry-run:
python3 firewall_ai.py --dry-run

## Installazione systemd
sudo ./scripts/install.sh


