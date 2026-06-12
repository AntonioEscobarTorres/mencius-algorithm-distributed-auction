import threading


class LeilaoApp:
    """
    Aplicacao de leilao replicada sobre AtomicBroadcast.

    Todas as mudancas de estado entram como eventos ordenados pelo building block.
    Assim, replicas diferentes aplicam os mesmos eventos na mesma ordem.
    """

    def __init__(self, node_id, atomic_broadcast, auction_id="A1", item="Notebook"):
        self.node_id = node_id
        self.atomic_broadcast = atomic_broadcast
        self.auction_id = auction_id
        self.item = item

        self.highest_bid = None
        self.winner = None
        self.closed = False
        self.history = []
        self.lock = threading.Lock()

        self.atomic_broadcast.register_deliver_callback(self.apply_event)

    def bid(self, user, value):
        """Publica um lance para todos os processos."""
        event = {
            "op": "bid",
            "auction_id": self.auction_id,
            "user": user,
            "value": int(value),
            "origin_node": self.node_id,
        }
        self.atomic_broadcast.broadcast(event)

    def close(self):
        """Publica o fechamento do leilao."""
        event = {
            "op": "close",
            "auction_id": self.auction_id,
            "origin_node": self.node_id,
        }
        self.atomic_broadcast.broadcast(event)

    def apply_event(self, event):
        """Aplica um evento ja entregue em ordem total pelo AtomicBroadcast."""
        if event.get("auction_id") != self.auction_id:
            return

        op = event.get("op")

        with self.lock:
            if op == "bid":
                result = self._apply_bid(event)
            elif op == "close":
                result = self._apply_close(event)
            else:
                result = "ignored"

            record = {
                "event": event,
                "result": result,
                "state": self.snapshot(),
            }
            self.history.append(record)

        self._print_event_result(event, result)

    def _apply_bid(self, event):
        user = event.get("user")
        value = int(event.get("value", 0))

        if self.closed:
            return "rejected_closed"

        if self.highest_bid is None or value > self.highest_bid:
            self.highest_bid = value
            self.winner = user
            return "accepted"

        return "rejected_low_bid"

    def _apply_close(self, event):
        if self.closed:
            return "already_closed"

        self.closed = True
        return "closed"

    def snapshot(self):
        return {
            "auction_id": self.auction_id,
            "item": self.item,
            "highest_bid": self.highest_bid,
            "winner": self.winner,
            "closed": self.closed,
        }

    def print_status(self):
        state = self.snapshot()
        print(
            f"[leilao node {self.node_id}] estado: "
            f"item={state['item']} "
            f"maior_lance={state['highest_bid']} "
            f"vencedor={state['winner']} "
            f"fechado={state['closed']}"
        )

    def _print_event_result(self, event, result):
        if event.get("op") == "bid":
            print(
                f"[leilao node {self.node_id}] lance "
                f"{event.get('user')}={event.get('value')} -> {result}; "
                f"vencedor_atual={self.winner}, maior_lance={self.highest_bid}"
            )
        elif event.get("op") == "close":
            print(
                f"[leilao node {self.node_id}] fechamento -> {result}; "
                f"vencedor={self.winner}, maior_lance={self.highest_bid}"
            )
