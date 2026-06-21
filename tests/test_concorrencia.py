import threading

from support import NODES, print_indexed_events

from test_leilao_app import (
    create_leilao_cluster,
    get_snapshots,
    get_delivered_events,
)


def main():
    apps, _ = create_leilao_cluster()

    print("\nTeste: concorrência de lances")

    barrier = threading.Barrier(2)

    def lance_alice():
        barrier.wait()
        print("\nDisparando lance de Alice")
        apps[1].bid("Alice", 1000)

    def lance_bob():
        barrier.wait()
        print("\nDisparando lance de Bob")
        apps[2].bid("Bob", 1000)

    t1 = threading.Thread(target=lance_alice)
    t2 = threading.Thread(target=lance_bob)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    snapshots = get_snapshots(apps)

    print("\nEstado final:")
    for node_id in NODES:
        print(f"node {node_id}: {snapshots[node_id]}")

    first_snapshot = snapshots[0]

    for node_id in NODES:
        assert snapshots[node_id]["winner"] == first_snapshot["winner"]
        assert snapshots[node_id]["highest_bid"] == first_snapshot["highest_bid"]
        assert snapshots[node_id]["closed"] == first_snapshot["closed"]

    delivered_events = get_delivered_events(apps)

    print_indexed_events("Eventos aplicados por todos os nodes", delivered_events[0])

    for node_id in NODES:
        assert delivered_events[node_id] == delivered_events[0]

    bid_events = [
        event
        for event in delivered_events[0]
        if event["op"] == "bid"
    ]

    assert len(bid_events) == 2

    users = {e["user"] for e in bid_events}
    assert users == {"Alice", "Bob"}

    print("\nOK: concorrência validada com ordenação total consistente.")


if __name__ == "__main__":
    main()
