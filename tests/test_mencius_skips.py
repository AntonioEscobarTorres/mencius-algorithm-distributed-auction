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


def main():
    atomic_broadcasts = {}
    delivered_messages = {node_id: [] for node_id in NODES}

    def make_send_callback(sender_id):
        def send(receiver_id, packet_json):
            packet = json.loads(packet_json)
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
        atomic = AtomicBroadcast(
            id=node_id,
            nodes=NODES
        )
        atomic.register_send_callback(make_send_callback(node_id))
        atomic.register_deliver_callback(make_deliver_callback(node_id))
        atomic_broadcasts[node_id] = atomic

    print("\nCenario: node 0 e node 1 nao enviam mensagens de aplicacao.")
    print("Apenas o node 2 faz broadcast; os slots 0 e 1 precisam virar SKIP.\n")

    print_teste(f"[teste] node 2 vai usar seu proximo slot: {atomic_broadcasts[2].next_seq_id}")
    atomic_broadcasts[2].broadcast({
        "op": "bid",
        "user": "Bob",
        "value": 1200
    })

    print("\nMensagens entregues para a aplicacao:\n")

    for node_id in NODES:
        print(f"node {node_id}: {delivered_messages[node_id]}")

    expected = [{
        "op": "bid",
        "user": "Bob",
        "value": 1200
    }]

    for node_id in NODES:
        assert delivered_messages[node_id] == expected

    print("\nOK: nodes ociosos mandaram SKIP e todos entregaram a mesma mensagem real.")


if __name__ == "__main__":
    main()
