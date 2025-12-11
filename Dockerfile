# Base image leggera con Python e strumenti di rete
FROM python:3.11-slim

# Installazione strumenti necessari
RUN apt-get update && apt-get install -y \
    nftables \
    iproute2 \
    net-tools \
    tshark \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Installazione dipendenze Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia del codice
COPY . /app
WORKDIR /app

# Comando di avvio
CMD ["python", "firewall_ai.py"]
