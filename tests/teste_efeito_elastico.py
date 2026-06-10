import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from AtomicBroadcast import AtomicBroadcast


NODES = [0, 1, 2]
TEST_COLOR = "\033[38;5;180m"
NETWORK_COLOR = "\033[1;97m"
RESET_COLOR = "\033[0m"


def print_teste(message):
    print(f"{TEST_COLOR}{message}{RESET_COLOR}")


def print_rede(message):
    print(f"{NETWORK_COLOR}{message}{RESET_COLOR}")


def create_cluster():
    atomic_broadcasts = {}
    delivered_messages = {node_id: [] for node_id in NODES}
    network_packets = []

    def make_send_callback(sender_id):
        def send(receiver_id, packet_json):
            packet = json.loads(packet_json)
            network_packets.append((sender_id, receiver_id, packet))
            receiver = atomic_broadcasts[receiver_id]
            expected_seq_id = receiver.next_to_deliver
            packet_seq_id = packet["seq_id"]

            print_rede(f"[rede] node {sender_id} -> node {receiver_id}: {packet_json}")
            if packet["type"] == "skip":
                print_teste(f"[teste] node {sender_id} esta ocioso no slot {packet_seq_id}; enviou SKIP")
            else:
                print_teste(f"[teste] mensagem real chegou com seq_id={packet_seq_id}")

            print_teste(f"[teste] node {receiver_id} espera seq_id={expected_seq_id}")
            if packet_seq_id == expected_seq_id:
                print_teste("[teste] pacote pode destravar a proxima entrega")
            elif packet_seq_id > expected_seq_id:
                print_teste(
                    f"[teste] pacote chegou adiantado; faltam os slots "
                    f"{list(range(expected_seq_id, packet_seq_id))}"
                )
            else:
                print_teste("[teste] pacote pertence a um slot que este node ja passou")

            receiver._on_receive_from_network(packet_json)

            current_buffer = sorted(receiver.waiting_messages.keys())
            if receiver.next_to_deliver > expected_seq_id:
                print_teste(
                    f"[teste] node {receiver_id} avancou a ordem global para "
                    f"seq_id={receiver.next_to_deliver}"
                )
            else:
                print_teste(f"[teste] node {receiver_id} continua esperando seq_id={receiver.next_to_deliver}")

            if current_buffer:
                print_teste(f"[teste] buffer do node {receiver_id} guarda slots: {current_buffer}")
            else:
                print_teste(f"[teste] buffer do node {receiver_id} ficou vazio")

        return send

    def make_deliver_callback(node_id):
        def deliver(message):
            print(f"[app] node {node_id} entregou: {message}")
            delivered_messages[node_id].append(message)

        return deliver

    for node_id in NODES:
        atomic = AtomicBroadcast(id=node_id, nodes=NODES)
        atomic.register_send_callback(make_send_callback(node_id))
        atomic.register_deliver_callback(make_deliver_callback(node_id))
        atomic_broadcasts[node_id] = atomic

    return atomic_broadcasts, delivered_messages, network_packets


def broadcast_with_log(atomic_broadcasts, node_id, message):
    atomic = atomic_broadcasts[node_id]
    print_teste(f"\n[teste] node {node_id} vai usar seu proximo slot: {atomic.next_seq_id}")
    print_teste(f"[teste] node {node_id} broadcast: {message}")
    atomic.broadcast(message)


def main():
    atomic_broadcasts, delivered_messages, network_packets = create_cluster()

    print("\nTeste: O Efeito Elastico (Rajada pos-Ociosidade)")
    print("Node 0 envia varias mensagens em rajada.")
    print("Nodes 1 e 2 ficam ociosos, entao seus slots vazios viram SKIP.")
    print("A entrega acompanha a rajada do node 0 assim que os buracos sao preenchidos.\n")

    burst_messages = [
        {"op": "bid", "user": "Node0-rajada-1", "value": 301},
        {"op": "bid", "user": "Node0-rajada-2", "value": 302},
        {"op": "bid", "user": "Node0-rajada-3", "value": 303},
    ]

    for message in burst_messages:
        broadcast_with_log(atomic_broadcasts, 0, message)

    skip_seq_ids = [
        packet["seq_id"] for _, receiver_id, packet in network_packets
        if packet["type"] == "skip" and receiver_id == packet["sender_id"]
    ]

    expected_messages = burst_messages

    print("\nSKIPs criados pelos donos dos slots:")
    print(skip_seq_ids)

    print("\nMensagens entregues para a aplicacao:\n")
    for node_id in NODES:
        print(f"node {node_id}: {delivered_messages[node_id]}")

    assert skip_seq_ids == [1, 2, 4, 5]
    for node_id in NODES:
        assert delivered_messages[node_id] == expected_messages

    print("\nOK: node 0 enviou a rajada e os nodes ociosos destravaram a ordem com SKIP.")


if __name__ == "__main__":
    main()
