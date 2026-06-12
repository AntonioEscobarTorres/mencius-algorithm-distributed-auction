import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from AtomicBroadcast import AtomicBroadcast
from SocketNode import SocketNode


SOCKET_NODES = {
    0: ("127.0.0.1", 5000),
    1: ("127.0.0.1", 5001),
    2: ("127.0.0.1", 5002),
}


def main():
    atomic_broadcasts = {}
    socket_nodes = {}
    delivered_messages = {node_id: [] for node_id in SOCKET_NODES}

    for node_id in SOCKET_NODES:
        atomic = AtomicBroadcast(
            id=node_id,
            nodes=list(SOCKET_NODES.keys())
        )

        socket_node = SocketNode(node_id, SOCKET_NODES, atomic)

        atomic.register_send_callback(socket_node.send)
        atomic.register_deliver_callback(
            lambda message, node_id=node_id: delivered_messages[node_id].append(message)
        )

        atomic_broadcasts[node_id] = atomic
        socket_nodes[node_id] = socket_node

    messages = [
        (1, {"op": "bid", "user": "Alice", "value": 1000}),
        (2, {"op": "bid", "user": "Bob", "value": 1200}),
        (0, {"op": "bid", "user": "Carol", "value": 1100}),
    ]

    try:
        for socket_node in socket_nodes.values():
            socket_node.start()

        time.sleep(1)

        print("\nEnviando lances do leilão...\n")
        for node_id, message in messages:
            atomic_broadcasts[node_id].broadcast(message)

        time.sleep(2)

        print("\nLances entregues por cada node:\n")
        for node_id in delivered_messages:
            print(f"node {node_id}:")
            for index, message in enumerate(delivered_messages[node_id]):
                print(f"  {index}: {message}")
            print()

        expected_order = delivered_messages[0]
        for node_id in delivered_messages:
            assert delivered_messages[node_id] == expected_order

        print("OK: todos os nodes entregaram os lances na mesma ordem.")
    finally:
        for socket_node in socket_nodes.values():
            socket_node.stop()


if __name__ == "__main__":
    main()
