import json
import threading


class AtomicBroadcast():

    def __init__(self, id : int, nodes, send_callback=None):
        self.id = id
        self.nodes = list(nodes)
        self.send_callback = send_callback

        self.next_to_deliver = 0
        self.waiting_messages = {}
        self.proposed_slots = set()
        self.deliver_callback = None
        self.lock = threading.Lock()
        self.cluster_size = len(self.nodes)

        if self.id not in self.nodes:
            raise ValueError("id do nó precisa existir na lista de nodes")
        
        # define o primeiro slot do nó
        self.next_seq_id = self.nodes.index(self.id)

    def register_send_callback(self, callback):
        """
        Registra a função que realmente envia a mensagem pela rede.
        """
        self.send_callback = callback

    def register_deliver_callback(self, callback):
        """
        Registra função da camada de aplicação que vai ser acordada pelo Building Block. 
        Permite que a aplicação fique esperando passivamente enquanto o Atomic Broadcast resolve a ordenação das mensagens.
        """
        self.deliver_callback = callback

    def broadcast(self, message_content):

        seq_id = self._get_next_owned_seq_id()
        self._send_to_all(seq_id, message_content)

    def _on_receive_from_network(self, packet):
        """
        Método chamado sempre que o Socket recebe um dado
        """
        data = json.loads(packet)

        if data['type'] not in ('deliver', 'skip'):
            return

        seq_id = data['seq_id']
        message = data.get('data')

        with self.lock:
            # Se chegou é duplicada
            if seq_id in self.waiting_messages:
                return

            # Coloca no buffer
            self.waiting_messages[seq_id] = {
                'type': data['type'],
                'data': message
            }

        self._send_missing_skips_until(seq_id)

        self._try_deliver()

    def _send_to_all(self, seq_id, message):
        """
        Manda a mensagem já com ordem para todos nodos
        """

        packet = json.dumps({
            'type': 'deliver',
            'seq_id': seq_id,
            'data': message
        })
        for node in self.nodes:
            self._send(node, packet)


    def _send_skip_to_all(self, seq_id):
        """Ocupa um slot ocioso deste nó sem entregar nada para a aplicação."""
        packet = json.dumps({
            'type': 'skip',
            'seq_id': seq_id,
            'sender_id': self.id,
        })
        for node in self.nodes:
            self._send(node, packet)

    def _send(self, node, packet):
        if self.send_callback is None:
            raise RuntimeError("send_callback não foi registrado")
        self.send_callback(node, packet)

    def _get_next_owned_seq_id(self):
        # Thread safe para caso duas queiram pegar seq_id juntas
        with self.lock:
            seq_id = self.next_seq_id
            self.proposed_slots.add(seq_id)
            self.next_seq_id += self.cluster_size
            return seq_id

    def _send_missing_skips_until(self, seq_id):
        slots_to_skip = []

        with self.lock:
            slot = self.next_seq_id

            while slot < seq_id:
                if slot not in self.proposed_slots and slot not in self.waiting_messages:
                    self.proposed_slots.add(slot)
                    slots_to_skip.append(slot)

                slot += self.cluster_size

            if self.next_seq_id < seq_id:
                self.next_seq_id = slot

        for slot in slots_to_skip:
            self._send_skip_to_all(slot)

    def _try_deliver(self):
        while True:
            with self.lock:
                if self.next_to_deliver not in self.waiting_messages:
                    return

                entry = self.waiting_messages.pop(self.next_to_deliver)

                self.next_to_deliver += 1

            if entry['type'] == 'deliver' and self.deliver_callback:
                self.deliver_callback(entry['data'])
