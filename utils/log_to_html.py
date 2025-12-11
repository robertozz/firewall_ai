import json
from datetime import datetime

def convert_log_to_html(log_path, html_path):
    try:
        with open(log_path, "r") as f:
            lines = f.readlines()
            entries = [json.loads(line) for line in lines if line.strip()]
    except Exception as e:
        print(f"Errore nella lettura del log: {e}")
        return

    html = """<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <title>Firewall Log</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
<div class="container mt-4">
  <h2>Firewall Log</h2>
  <table class="table table-bordered table-striped">
    <thead><tr><th>Timestamp</th><th>Livello</th><th>Messaggio</th></tr></thead>
    <tbody>
"""

    for entry in entries:
        ts = entry.get("timestamp", "")
        level = entry.get("level", "INFO")
        msg = entry.get("message", "")
        html += f"<tr><td>{ts}</td><td>{level}</td><td>{msg}</td></tr>\n"

    html += """
    </tbody>
  </table>
</div>
</body>
</html>
"""

    try:
        with open(html_path, "w") as f:
            f.write(html)
        print(f"✅ HTML generato: {html_path}")
    except Exception as e:
        print(f"Errore nella scrittura HTML: {e}")
