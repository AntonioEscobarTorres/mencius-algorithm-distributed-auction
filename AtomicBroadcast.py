import json
import threading


class AtomicBroadcast():

    def __init__(self, id : int, nodes, is_leader : bool, leader_id=0, send_callback=None):
        self.id = id
        self.nodes = nodes
        self.is_leader = is_leader
        self.leader_id = leader_id
        self.send_callback = send_callback

        self.next_to_deliver = 0
        self.waiting_messages = {}
        self.deliver_callback = None
        self.lock = threading.Lock()

        if is_leader:
            self.global_counter = 0

    def register_send_callback(self, callback):
        """
        Registra a função que realmente envia a mensagem pela rede.
        Essa função deve receber: callback(node, packet_json)
        """
        self.send_callback = callback

    def register_deliver_callback(self, callback):
        """
        Registra a função da camada de aplicação que será 'acordada' pelo Building Block. Isso permite que a aplicação fique esperando passivamente enquanto o Atomic Broadcast resolve a ordenação das mensagens.
        """
        self.deliver_callback = callback

    def broadcast(self, message_content):
        """Chamado pela aplicação para enviar mensagem para os outros nodes"""
        if self.is_leader:
            # líderes introduzem um ID na mensagem
            seq_id = self._get_next_seq_id()
            self._send_to_all(seq_id, message_content)
        else:
            # não líderes, pedem para o líder
            self._send_to_leader(message_content)

    def _on_receive_from_network(self, packet):
        """
        Método chamado sempre que o Socket recebe um dado
        """
        data = json.loads(packet)

        if data['type'] == 'request':
            # Só o líder ordena pedidos recebidos de outros nós
            if self.is_leader:
                seq_id = self._get_next_seq_id()
                self._send_to_all(seq_id, data['data'])
            return

        if data['type'] != 'deliver':
            return

        seq_id = data['seq_id']
        message = data['data']

        # 1. Coloca no buffer de espera
        self.waiting_messages[seq_id] = message

        # 2. Tenta entregar na ordem correta (Atomicidade e Ordem)
        while self.next_to_deliver in self.waiting_messages:
            msg_to_deliver = self.waiting_messages.pop(self.next_to_deliver)
            
            # ENTREGA REAL PARA A APLICAÇÃO
            if self.deliver_callback:
                self.deliver_callback(msg_to_deliver)
            
            self.next_to_deliver += 1

    def _send_to_all(self, seq_id, message):
        """Manda a mensagem já com ordem para todos os processos, incluindo ele mesmo"""
        packet = json.dumps({
            'type': 'deliver',
            'seq_id': seq_id,
            'data': message
        })
        for node in self.nodes:
            self._send(node, packet)


    def _send_to_leader(self, message):
        """Manda pedido para o líder ordenar e difundir"""
        packet = json.dumps({
            'type': 'request',
            'sender_id': self.id,
            'data': message
        })
        self._send(self.leader_id, packet)

    def _send(self, node, packet):
        if self.send_callback is None:
            raise RuntimeError("send_callback não foi registrado")
        self.send_callback(node, packet)

    def _get_next_seq_id(self):
        with self.lock:
            seq_id = self.global_counter
            self.global_counter += 1
            return seq_id
