#!/usr/bin/env python3
import requests
import sys
import os
import json
import logging
from datetime import datetime, timedelta
import html

# ===========================
# Libreria + CLI + Logger + Digest HTML# -------------------------------------------
# CLI:
#   python telegram_utils.py <MESSAGGIO> [CONF_FILE] [--html|--raw]
#
# Modulo:
#   from telegram_utils import (
#       notify_html, notify_markdown, notify_raw,
#       log_and_notify, send_log_digest_html,
#       build_html_digest_from_log
#   )
# ===========================

# === Percorsi base ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
LOG_DIR = os.path.join(BASE_DIR, "log")

CONFIG_FILE = os.path.join(CONFIG_DIR, "telegram.json")
LOG_FILE = os.path.join(LOG_DIR, "system.log")

# === Assicurati che le cartelle esistano ===
for d in [CONFIG_DIR, LOG_DIR]:
    os.makedirs(d, exist_ok=True)

# === Logger plain-text su file ===
logger = logging.getLogger("central_logger")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    fh = logging.FileHandler(LOG_FILE)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    fh.setFormatter(formatter)
    logger.addHandler(fh)

# === Lettura configurazione ===
def read_config(filename):
    with open(filename, "r") as f:
        data = json.load(f)
    return data["token"], data["chat_id"]

# === Escape per MarkdownV2 ===
def escape_markdown_v2(text):
    escape_chars = r"_*[]()~`>#+-=|{}.!<>"
    for char in escape_chars:
        text = text.replace(char, f"\\{char}")
    return text

# === Invio messaggio Telegram ===
def send_telegram_message(token, chat_id, message, mode="MarkdownV2"):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    if mode == "MarkdownV2":
        message = escape_markdown_v2(message)
    payload = {"chat_id": chat_id, "text": message}
    if mode != "raw":
        payload["parse_mode"] = mode
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        logger.debug("Messaggio Telegram inviato con successo.")
    else:
        logger.error(f"Errore Telegram: {response.text}")
    print(f"[DEBUG] Telegram response: {response.status_code} {response.text}") # === DEBUG ===

# === Wrapper notifica ===
def notify_markdown(message, conf_file=CONFIG_FILE):
    token, chat_id = read_config(conf_file)
    send_telegram_message(token, chat_id, message, mode="MarkdownV2")

def notify_html(message, conf_file=CONFIG_FILE):
    token, chat_id = read_config(conf_file)
    send_telegram_message(token, chat_id, message, mode="HTML")

def notify_raw(message, conf_file=CONFIG_FILE):
    token, chat_id = read_config(conf_file)
    send_telegram_message(token, chat_id, message, mode="raw")

# === Log + notifica combinati ===
def log_and_notify(message, level="INFO", mode="HTML", conf_file=CONFIG_FILE):
    if level == "INFO":
        logger.info(message)
    elif level == "WARNING":
        logger.warning(message)
    elif level == "ERROR":
        logger.error(message)
    elif level == "DEBUG":
        logger.debug(message)
    else:
        logger.info(message)
    token, chat_id = read_config(conf_file)
    send_telegram_message(token, chat_id, message, mode=mode)

# === Utilità: parsing log file ===
def _parse_log_line(line):
    # Formato atteso: "YYYY-MM-DD HH:MM:SS,mmm [LEVEL] message"
    try:
        ts_str, rest = line.split(" [", 1)
        level, msg = rest.split("] ", 1)
        ts = datetime.strptime(ts_str.strip(), "%Y-%m-%d %H:%M:%S,%f")
        return {"time": ts, "level": level.strip(), "message": msg.rstrip("\n")}
    except Exception:
        return None

def _read_log_records(path, since=None, max_lines=None):
    records = []
    if not os.path.exists(path):
        return records
    # Lettura efficiente: tail-like se max_lines è settato
    with open(path, "r") as f:
        lines = f.readlines()
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[-max_lines:]
    for line in lines:
        rec = _parse_log_line(line)
        if rec is None:
            continue
        if since and rec["time"] < since:
            continue
        records.append(rec)
    return records

# === Costruzione digest HTML ===
def build_html_digest(records, title="🔍 Digest di sistema"):
    # Stile minimo inline per compatibilità Telegram
    style = (
        "border-collapse:collapse;width:100%;"
    )
    th_style = (
        "text-align:left;padding:6px;border-bottom:1px solid #ccc;"
        "background:#f6f8fa;font-weight:bold;font-family:monospace;"
        "font-size:12px;"
    )
    td_style = (
        "padding:6px;border-bottom:1px solid #eee;font-family:monospace;"
        "font-size:12px;vertical-align:top;"
    )
    level_colors = {
        "DEBUG": "#6a737d",
        "INFO": "#0366d6",
        "WARNING": "#b08800",
        "ERROR": "#d73a49",
    }

    html_parts = [f"<b>{html.escape(title)}</b><br><br>"]
    if not records:
        html_parts.append("<i>Nessun record disponibile.</i>")
        return "".join(html_parts)

    html_parts.append(f"<table style=\"{style}\">")
    html_parts.append(
        f"<tr>"
        f"<th style=\"{th_style}\">Timestamp</th>"
        f"<th style=\"{th_style}\">Livello</th>"
        f"<th style=\"{th_style}\">Messaggio</th>"
        f"</tr>"
    )

    for rec in records:
        ts = rec["time"].strftime("%Y-%m-%d %H:%M:%S")
        lvl = rec["level"]
        color = level_colors.get(lvl, "#444")
        msg = html.escape(rec["message"])
        html_parts.append(
            f"<tr>"
            f"<td style=\"{td_style}\">{html.escape(ts)}</td>"
            f"<td style=\"{td_style};color:{color}\"><b>{html.escape(lvl)}</b></td>"
            f"<td style=\"{td_style}\"><code>{msg}</code></td>"
            f"</tr>"
        )
    html_parts.append("</table>")
    return "".join(html_parts)

def build_html_digest_from_log(path=LOG_FILE, period="day", max_lines=None, title=None):
    # period: "day" (da mezzanotte), "24h" (ultime 24 ore), "all"
    now = datetime.now()
    if period == "day":
        since = datetime(now.year, now.month, now.day)
        ttl = title or "📅 Digest giornaliero (da mezzanotte)"
    elif period == "24h":
        since = now - timedelta(hours=24)
        ttl = title or "⏱️ Digest ultime 24 ore"
    elif period == "all":
        since = None
        ttl = title or "🗂️ Digest completo"
    else:
        since = None
        ttl = title or f"Digest (periodo: {period})"

    records = _read_log_records(path, since=since, max_lines=max_lines)
    return build_html_digest(records, title=ttl)

# === Invio digest HTML ===
def send_log_digest_html(period="day", max_lines=None, conf_file=CONFIG_FILE):
    html_msg = build_html_digest_from_log(LOG_FILE, period=period, max_lines=max_lines)
    token, chat_id = read_config(conf_file)
    send_telegram_message(token, chat_id, html_msg, mode="HTML")

# === CLI: invio messaggi plain o digest ===
if __name__ == "__main__":
    # Se nessun argomento → help completo
    if len(sys.argv) < 2:
        print("""
===========================
Libreria + CLI + Logger + Digest HTML per Telegram
---------------------------
Uso messaggio:
  python telegram_utils.py <MESSAGGIO> [CONF_FILE] [--html|--raw]

Uso digest:
  python telegram_utils.py --digest [day|24h|all] [CONF_FILE]
  Opzioni:
    day  → record da mezzanotte a ora
    24h  → ultimi 1440 minuti
    all  → tutti i record (filtrati da max_lines se specificato)

Esempi:
  python telegram_utils.py "Servizio avviato" --html
  python telegram_utils.py --digest day
  python telegram_utils.py --digest 24h config/telegram.json
===========================
""")
        sys.exit(1)

    # Modalità digest
    if sys.argv[1] == "--digest":
        period = "day"
        conf_file = CONFIG_FILE
        # Argomenti successivi: period, conf_file
        if len(sys.argv) >= 3 and sys.argv[2] in ("day", "24h", "all"):
            period = sys.argv[2]
            idx = 3
        else:
            idx = 2
        # Config file (opzionale)
        if len(sys.argv) > idx and sys.argv[idx].endswith(".json"):
            conf_file = sys.argv[idx]
        send_log_digest_html(period=period, conf_file=conf_file)
        # Logga anche localmente l’invio del digest
        logger.info(f"Digest inviato (period={period})")
        sys.exit(0)

    # Modalità messaggio semplice
    message = sys.argv[1]
    conf_file = CONFIG_FILE
    mode = "MarkdownV2"
    for arg in sys.argv[2:]:
        if arg.endswith(".json"):
            conf_file = arg
        elif arg == "--html":
            mode = "HTML"
        elif arg == "--raw":
            mode = "raw"
    token, chat_id = read_config(conf_file)
    send_telegram_message(token, chat_id, message, mode)
    logger.info(f"CLI: {message}")
