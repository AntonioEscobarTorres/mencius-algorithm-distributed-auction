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


def create_atomic_cluster(verbose=True):
    atomic_broadcasts = {}
    delivered_messages = {node_id: [] for node_id in NODES}
    network_packets = []

    def make_send_callback(sender_id):
        def send(receiver_id, packet_json):
            packet = json.loads(packet_json)
            network_packets.append((sender_id, receiver_id, packet))
            receiver = atomic_broadcasts[receiver_id]

            if verbose:
                print_network_step(sender_id, receiver_id, packet_json, packet, receiver)

            receiver._on_receive_from_network(packet_json)

            if verbose:
                print_receiver_state(receiver_id, receiver)

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


def print_network_step(sender_id, receiver_id, packet_json, packet, receiver):
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


def print_receiver_state(receiver_id, receiver):
    current_buffer = sorted(receiver.waiting_messages.keys())

    print_teste(f"[teste] node {receiver_id} agora espera seq_id={receiver.next_to_deliver}")
    if current_buffer:
        print_teste(f"[teste] buffer do node {receiver_id} guarda slots: {current_buffer}")
    else:
        print_teste(f"[teste] buffer do node {receiver_id} ficou vazio")


def broadcast_with_log(atomic_broadcasts, node_id, message):
    atomic = atomic_broadcasts[node_id]
    print_teste(f"\n[teste] node {node_id} vai usar seu proximo slot: {atomic.next_seq_id}")
    print_teste(f"[teste] node {node_id} broadcast: {message}")
    atomic.broadcast(message)


def get_skip_packets(network_packets):
    return [
        packet for _, _, packet in network_packets
        if packet["type"] == "skip"
    ]


def get_unique_skip_slots(network_packets):
    return [
        packet["seq_id"]
        for _, receiver_id, packet in network_packets
        if packet["type"] == "skip" and receiver_id == packet["sender_id"]
    ]


def get_skip_slots_by_owner(network_packets):
    skips_by_owner = {}
    for packet in get_skip_packets(network_packets):
        owner = packet["sender_id"]
        skips_by_owner.setdefault(owner, set()).add(packet["seq_id"])

    return {
        node_id: sorted(skips_by_owner.get(node_id, set()))
        for node_id in NODES
    }


def print_delivered_messages(delivered_messages):
    print("\nMensagens entregues para a aplicacao:\n")
    for node_id in NODES:
        print(f"node {node_id}: {delivered_messages[node_id]}")


def print_indexed_events(title, events):
    print(f"\n{title}:")
    for index, event in enumerate(events):
        print(f"  {index}: {event}")


def print_skipped_slots(network_packets):
    skip_packets = get_skip_packets(network_packets)
    skipped_slots = get_skip_slots_by_owner(network_packets)

    print("\nSlots pulados pelo AtomicBroadcast:")
    if not skip_packets:
        print("  nenhum slot precisou de SKIP")
        return skip_packets

    for node_id in NODES:
        if skipped_slots[node_id]:
            print(f"  node {node_id} deu SKIP nos slots {skipped_slots[node_id]}")
        else:
            print(f"  node {node_id} nao deu SKIP")

    return skip_packets
