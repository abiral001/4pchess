import socket
import threading
import json
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization

def send_json(sock, msg):
    sock.sendall((json.dumps(msg) + "\n").encode())

def recv_json(sock):
    buf = b""
    while not buf.endswith(b"\n"):
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectionError()
        buf += chunk
    return json.loads(buf.decode().strip())

class HostNetwork:
    def __init__(self, port=5000, min_players=2, max_players=4):
        self.port         = port
        self.min_players  = min_players
        self.max_players  = max_players
        self.clients      = {}
        self.peer_pubkeys = {}
        self.assignments  = {}
        self.on_move      = None
        self.private_key  = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_key   = self.private_key.public_key()
        self._shutdown    = False

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(('', self.port))
        self.server.listen(self.max_players)
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def _accept_loop(self):
        while not self._shutdown and len(self.clients) < self.max_players:
            client_sock, addr = self.server.accept()
            self.clients[addr] = client_sock
            print(f"[HOST] Client connected: {addr}")

    def start_game(self):
        from components.player import players_colors
        import random
        pool = players_colors.copy()
        random.shuffle(pool)
        host_addr = ('HOST', self.port)
        self.assignments[host_addr] = pool.pop()
        for addr in self.clients:
            self.assignments[addr] = pool.pop()

        for addr, sock in self.clients.items():
            send_json(sock, {
                "type": "assign",
                "color": self.assignments[addr]
            })

        self.peer_pubkeys[self.assignments[host_addr]] = self.public_key
        for addr, sock in self.clients.items():
            msg = recv_json(sock)
            color = msg["color"]
            pem   = msg["pem"].encode()
            pub   = serialization.load_pem_public_key(pem)
            self.peer_pubkeys[color] = pub

        host_pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        init = {
            "type":        "init",
            "assignments": {str(k): v for k, v in self.assignments.items()},
            "pubkeys":     {}
        }
        for c, pub in self.peer_pubkeys.items():
            pem = pub.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode()
            init["pubkeys"][c] = pem

        for sock in self.clients.values():
            send_json(sock, init)

        threading.Thread(target=self._relay_loop, daemon=True).start()

    def _relay_loop(self):
        while True:
            for addr, sock in list(self.clients.items()):
                try:
                    msg = recv_json(sock)
                except ConnectionError:
                    continue
                if msg["type"] == "move":
                    color = msg["color"]
                    pub   = self.peer_pubkeys[color]
                    data  = json.dumps({
                        "type": "move",
                        "color": color,
                        "from": msg["from"],
                        "to":   msg["to"]
                    }).encode()
                    sig = bytes.fromhex(msg["sig"])
                    pub.verify(
                        sig,
                        data,
                        padding.PSS(
                            mgf=padding.MGF1(hashes.SHA256()),
                            salt_length=padding.PSS.MAX_LENGTH
                        ),
                        hashes.SHA256()
                    )
                    for s in self.clients.values():
                        send_json(s, msg)
                    if self.on_move:
                        self.on_move(tuple(msg["from"]),
                                     tuple(msg["to"]),
                                     color)

    def send_move(self, fr, to, color):
        data   = {"type": "move", "color": color, "from": fr, "to": to}
        sig    = self.private_key.sign(
            json.dumps(data).encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        ).hex()
        packet = {"type": "move", **data, "sig": sig}
        for sock in self.clients.values():
            send_json(sock, packet)
        if self.on_move:
            self.on_move(fr, to, color)

    def shutdown(self):
        self._shutdown = True
        self.server.close()
        for s in self.clients.values():
            s.close()

class ClientNetwork:
    def __init__(self, host_ip, port=5000):
        self.host_addr    = (host_ip, port)
        self.sock         = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(self.host_addr)

        self.private_key  = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_key   = self.private_key.public_key()
        self.color        = None
        self.peer_pubkeys = {}
        self.on_move      = None

        self.ready        = False

        # start handshake + listener thread
        threading.Thread(target=self._handshake_and_listen, daemon=True).start()

    def _handshake_and_listen(self):
        # 1) receive assign
        msg = recv_json(self.sock)
        self.color = msg["color"]

        # 2) send our pubkey
        pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        send_json(self.sock, {"type": "pubkey", "color": self.color, "pem": pem})

        # 3) receive init (assignments + all pubkeys)
        init = recv_json(self.sock)
        # load all peer pubkeys
        for c, pem in init["pubkeys"].items():
            self.peer_pubkeys[c] = serialization.load_pem_public_key(pem.encode())

        # mark ready so main loop can proceed
        self.ready = True

        # 4) finally, enter the normal move‐listening loop
        while True:
            msg = recv_json(self.sock)
            if msg["type"] == "move" and self.on_move:
                self.on_move(tuple(msg["from"]), tuple(msg["to"]), msg["color"])

    def send_move(self, fr, to):
        data   = {"type":"move","color":self.color,"from":fr,"to":to}
        sig    = self.private_key.sign(
            json.dumps(data).encode(),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256()
        ).hex()
        packet = {"type":"move", **data, "sig":sig}
        send_json(self.sock, packet)