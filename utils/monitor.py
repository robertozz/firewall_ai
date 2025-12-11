import psutil

def get_active_ports():
    connections = psutil.net_connections()
    active = set()
    for conn in connections:
        if conn.status == "LISTEN":
            active.add((conn.laddr.port, conn.type))
    return active
