import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from AtomicBroadcast import AtomicBroadcast
from SocketNode import SocketNode


NODES = {
    0: ("127.0.0.1", 5000),
    1: ("127.0.0.1", 5001),
    2: ("127.0.0.1", 5002),
}

def main():
    atomic_broadcasts = {}
    socket_nodes = {}
    delivered_messages = {
        0: [],
        1: [],
        2: [],
    }

    for node_id in NODES:
        atomic = AtomicBroadcast(
            id=node_id,
            nodes=list(NODES.keys())
        )

        socket_node = SocketNode(node_id, NODES, atomic)

        atomic.register_send_callback(socket_node.send)
        atomic.register_deliver_callback(
            lambda message, node_id=node_id: delivered_messages[node_id].append(message)
        )

        atomic_broadcasts[node_id] = atomic
        socket_nodes[node_id] = socket_node

    for socket_node in socket_nodes.values():
        socket_node.start()

    time.sleep(1)

    print("\nEnviando lances do leilão...\n")

    atomic_broadcasts[1].broadcast({
        "op": "bid",
        "user": "Alice",
        "value": 1000
    })

    atomic_broadcasts[2].broadcast({
        "op": "bid",
        "user": "Bob",
        "value": 1200
    })

    atomic_broadcasts[0].broadcast({
        "op": "bid",
        "user": "Carol",
        "value": 1100
    })

    time.sleep(2)

    print("\nLances entregues por cada node:\n")

    for node_id in delivered_messages:
        print(f"node {node_id}:")
        for index, message in enumerate(delivered_messages[node_id]):
            print(f"  {index}: {message}")
        print()

    first_order = delivered_messages[0]
    same_order = True

    for node_id in delivered_messages:
        if delivered_messages[node_id] != first_order:
            same_order = False

    if same_order:
        print("OK: todos os nodes entregaram os lances na mesma ordem.")
    else:
        print("ERRO: os nodes entregaram lances em ordens diferentes.")

    for socket_node in socket_nodes.values():
        socket_node.stop()


if __name__ == "__main__":
    main()
