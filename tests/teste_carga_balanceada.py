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
            print_teste(f"[teste] node {receiver_id} espera seq_id={expected_seq_id}")
            if packet_seq_id == expected_seq_id:
                print_teste("[teste] esta mensagem e exatamente a proxima da ordem global")
            elif packet_seq_id > expected_seq_id:
                print_teste(
                    f"[teste] mensagem chegou adiantada; faltam os slots "
                    f"{list(range(expected_seq_id, packet_seq_id))}"
                )
            else:
                print_teste("[teste] esse slot ja foi processado por este node")

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

    print("\nTeste: Carga 100% Balanceada (O Cenario Ideal)")
    print("Cada node envia exatamente uma mensagem na sua vez natural: 0, 1, 2.")
    print("Resultado esperado: nenhum SKIP e todos entregam as 3 mensagens.\n")

    messages = [
        {"op": "bid", "user": "Node0", "value": 100},
        {"op": "bid", "user": "Node1", "value": 200},
        {"op": "bid", "user": "Node2", "value": 300},
    ]

    broadcast_with_log(atomic_broadcasts, 0, messages[0])
    broadcast_with_log(atomic_broadcasts, 1, messages[1])
    broadcast_with_log(atomic_broadcasts, 2, messages[2])

    skip_packets = [
        packet for _, _, packet in network_packets
        if packet["type"] == "skip"
    ]

    print("\nMensagens entregues para a aplicacao:\n")
    for node_id in NODES:
        print(f"node {node_id}: {delivered_messages[node_id]}")

    assert skip_packets == []
    for node_id in NODES:
        assert delivered_messages[node_id] == messages

    print("\nOK: carga balanceada entregou tudo em ordem sem SKIP.")


if __name__ == "__main__":
    main()
