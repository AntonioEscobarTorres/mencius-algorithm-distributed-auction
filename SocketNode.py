import socket
import threading


class SocketNode:

    def __init__(self, id: int, nodes, atomic_broadcast):
        self.id = id
        self.nodes = nodes
        self.atomic_broadcast = atomic_broadcast

        self.host, self.port = self.nodes[self.id]
        self.server_socket = None
        self.running = False

    def start(self):
        """Inicia o servidor socket deste nó."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen()
        except OSError:
            self.server_socket.close()
            self.server_socket = None
            raise

        self.running = True

        thread = threading.Thread(target=self._listen, daemon=True)
        thread.start()

        print(f"[node {self.id}] escutando em {self.host}:{self.port}")

    def stop(self):
        """Para o servidor socket deste nó."""
        self.running = False

        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None

    def send(self, node_id, packet_json):
        """Envia uma string JSON para outro nó."""
        host, port = self.nodes[node_id]

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                client_socket.connect((host, port))
                client_socket.sendall(packet_json.encode("utf-8"))
        except ConnectionRefusedError:
            print(f"[node {self.id}] não conseguiu conectar no node {node_id}")

    def _listen(self):
        while self.running:
            try:
                connection, address = self.server_socket.accept()
            except OSError:
                break

            thread = threading.Thread(
                target=self._handle_connection,
                args=(connection, address),
                daemon=True
            )
            thread.start()

    def _handle_connection(self, connection, address):
        with connection:
            packet_json = connection.recv(4096).decode("utf-8")

            if packet_json:
                print(f"[node {self.id}] recebeu de {address}: {packet_json}")
                self.atomic_broadcast._on_receive_from_network(packet_json)
