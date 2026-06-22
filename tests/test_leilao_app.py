import json

from support import NODES, print_indexed_events, print_skipped_slots

from AtomicBroadcast import AtomicBroadcast
from LeilaoApp import LeilaoApp


def create_leilao_cluster():
    atomic_broadcasts = {}
    apps = {}
    network_packets = []

    def make_send_callback(sender_id):
        def send(receiver_id, packet_json):
            packet = json.loads(packet_json)
            network_packets.append((sender_id, receiver_id, packet))

            receiver = atomic_broadcasts[receiver_id]
            receiver._on_receive_from_network(packet_json)

        return send

    for node_id in NODES:
        atomic = AtomicBroadcast(id=node_id, nodes=NODES)
        app = LeilaoApp(
            node_id=node_id,
            atomic_broadcast=atomic,
            auction_id="A1",
            item="Notebook",
        )

        atomic.register_send_callback(make_send_callback(node_id))

        atomic_broadcasts[node_id] = atomic
        apps[node_id] = app

    return apps, network_packets


def get_snapshots(apps):
    snapshots = {}
    for node_id in NODES:
        snapshots[node_id] = apps[node_id].snapshot()

    return snapshots


def get_delivered_events(apps):
    delivered_events = {}
    for node_id in NODES:
        events = []
        for record in apps[node_id].history:
            events.append(record["event"])

        delivered_events[node_id] = events

    return delivered_events


def main():
    apps, network_packets = create_leilao_cluster()

    print("\nDemo: LeilaoApp sobre Atomic Broadcast")
    print("Tres nodes enviam eventos; todos devem terminar com o mesmo vencedor.\n")

    apps[1].bid("Alice", 1000)
    apps[2].bid("Bob", 1200)
    apps[0].bid("Carol", 1100)
    apps[1].close()
    apps[2].bid("Daniel", 1300)
    apps[1].bid("Eva", 1400)

    snapshots = get_snapshots(apps)

    print("\nEstado final por node:\n")
    for node_id in NODES:
        print(f"node {node_id}: {snapshots[node_id]}")

    first_snapshot = snapshots[0]
    for node_id in NODES:
        assert snapshots[node_id] == first_snapshot

    assert first_snapshot["winner"] == "Bob"
    assert first_snapshot["highest_bid"] == 1200
    assert first_snapshot["closed"] is True

    delivered_events = get_delivered_events(apps)

    for node_id in NODES:
        assert delivered_events[node_id] == delivered_events[0]

    print_indexed_events("Eventos aplicados por todos os nodes", delivered_events[0])
    skip_packets = print_skipped_slots(network_packets)

    print(f"\nSKIPs usados pelo AtomicBroadcast: {len(skip_packets)}")
    print("OK: todas as replicas do leilao chegaram ao mesmo estado final.")


if __name__ == "__main__":
    main()
