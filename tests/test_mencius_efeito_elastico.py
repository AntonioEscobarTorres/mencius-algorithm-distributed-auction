from support import (
    NODES,
    broadcast_with_log,
    create_atomic_cluster,
    get_unique_skip_slots,
    print_delivered_messages,
)


def main():
    atomic_broadcasts, delivered_messages, network_packets = create_atomic_cluster()

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

    skip_seq_ids = get_unique_skip_slots(network_packets)

    print("\nSKIPs criados pelos donos dos slots:")
    print(skip_seq_ids)
    print_delivered_messages(delivered_messages)

    assert skip_seq_ids == [1, 2, 4, 5]
    for node_id in NODES:
        assert delivered_messages[node_id] == burst_messages

    print("\nOK: node 0 enviou a rajada e os nodes ociosos destravaram a ordem com SKIP.")


if __name__ == "__main__":
    main()
