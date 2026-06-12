import sys
import time

from AtomicBroadcast import AtomicBroadcast
from LeilaoApp import LeilaoApp
from SocketNode import SocketNode


NODES = {
    0: ("127.0.0.1", 5000),
    1: ("127.0.0.1", 5001),
    2: ("127.0.0.1", 5002),
}


def print_help():
    print("Comandos:")
    print("  bid <usuario> <valor>")
    print("  close")
    print("  status")
    print("  help")
    print("  quit")


def main():
    if len(sys.argv) != 2:
        print("Uso: python3 auction_node.py <node_id>")
        print(f"Nodes disponiveis: {sorted(NODES.keys())}")
        return 1

    node_id = int(sys.argv[1])
    if node_id not in NODES:
        print(f"node_id invalido: {node_id}")
        return 1

    atomic = AtomicBroadcast(id=node_id, nodes=list(NODES.keys()))
    socket_node = SocketNode(node_id, NODES, atomic)
    app = LeilaoApp(node_id, atomic, auction_id="A1", item="Notebook")

    atomic.register_send_callback(socket_node.send)
    socket_node.start()

    print(f"[node {node_id}] LeilaoApp iniciado.")
    print_help()

    try:
        while True:
            command = input(f"node {node_id}> ").strip()

            if not command:
                continue

            parts = command.split()
            action = parts[0].lower()

            if action == "bid" and len(parts) == 3:
                user = parts[1]
                value = int(parts[2])
                app.bid(user, value)
            elif action == "close" and len(parts) == 1:
                app.close()
            elif action == "status" and len(parts) == 1:
                app.print_status()
            elif action == "help" and len(parts) == 1:
                print_help()
            elif action in ("quit", "exit") and len(parts) == 1:
                break
            else:
                print("Comando invalido.")
                print_help()

            time.sleep(0.1)
    except KeyboardInterrupt:
        print()
    finally:
        socket_node.stop()
        print(f"[node {node_id}] encerrado.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
