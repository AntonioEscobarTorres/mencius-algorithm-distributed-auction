from support import (
    NODES,
    broadcast_with_log,
    create_atomic_cluster,
    get_skip_packets,
    print_delivered_messages,
)


def main():
    atomic_broadcasts, delivered_messages, network_packets = create_atomic_cluster()

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

    print_delivered_messages(delivered_messages)

    assert get_skip_packets(network_packets) == []
    for node_id in NODES:
        assert delivered_messages[node_id] == messages

    print("\nOK: carga balanceada entregou tudo em ordem sem SKIP.")


if __name__ == "__main__":
    main()
