import socket
import threading
import json
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization

# message framing: newline-delimited JSON
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
        self.clients      = {}   # addr -> socket
        self.peer_pubkeys = {}   # color -> public key object
        self.assignments  = {}   # addr -> color
        self.on_move      = None # callback(fr, to, color)

        # generate host RSA keypair
        self.private_key = rsa.generate_private_key(65537, 2048)
        self.public_key  = self.private_key.public_key()

        # start listening
        self._shutdown = False
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(('', self.port))
        self.server.listen(self.max_players)
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def _accept_loop(self):
        while not self._shutdown and len(self.clients) < self.max_players:
            client_sock, addr = self.server.accept()
            self.clients[addr] = client_sock
            print(f"[HOST] Client connected: {addr}")

    def wait_for_start(self):
        """Block until host presses S in main.py (at least min_players connected)."""
        while len(self.clients) + 1 < self.min_players:
            pass
        # now main.py will call start_game()

    def start_game(self):
        """Assign colors, exchange pubkeys, send INIT to each, start move‐relay thread."""
        # 1) random color assignment
        from components.player import players_colors
        import random
        pool = players_colors.copy()
        random.shuffle(pool)
        # host is first
        host_addr = ('HOST', self.port)
        self.assignments[host_addr] = pool.pop()
        for addr in self.clients:
            self.assignments[addr] = pool.pop()

        # 2) send each client their color
        for addr, sock in self.clients.items():
            send_json(sock, {
                "type": "assign",
                "color": self.assignments[addr]
            })

        # 3) collect client pubkeys
        #    and also store host's own pubkey under its color
        self.peer_pubkeys[self.assignments[host_addr]] = self.public_key
        for addr, sock in self.clients.items():
            msg = recv_json(sock)
            assert msg["type"] == "pubkey"
            color = msg["color"]
            pem   = msg["pem"].encode()
            pub   = serialization.load_pem_public_key(pem)
            self.peer_pubkeys[color] = pub

        # 4) send host's pubkey back to clients
        host_pem = self.public_key.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        init = {
            "type":      "init",
            "assignments": {str(k):v for k,v in self.assignments.items()},
            "pubkeys":   {c: host_pem for c in self.peer_pubkeys}
        }
        # include all client pubkeys too
        for c,pub in self.peer_pubkeys.items():
            pem = pub.public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode()
            init["pubkeys"][c] = pem

        for sock in self.clients.values():
            send_json(sock, init)

        # 5) launch relay thread
        threading.Thread(target=self._relay_loop, daemon=True).start()

    def _relay_loop(self):
        """Accept moves from any client, verify, then broadcast to all."""
        while True:
            for addr, sock in list(self.clients.items()):
                try:
                    msg = recv_json(sock)
                except ConnectionError:
                    continue
                if msg["type"] == "move":
                    # verify
                    color = msg["color"]
                    pub   = self.peer_pubkeys[color]
                    data  = json.dumps({
                        "type":"move","color":color,
                        "from":msg["from"],"to":msg["to"]
                    }).encode()
                    sig = bytes.fromhex(msg["sig"])
                    pub.verify(sig, data,
                        padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                                    salt_length=padding.PSS.MAX_LENGTH),
                        hashes.SHA256()
                    )
                    # forward to all clients + host callback
                    for _, s2 in self.clients.items():
                        send_json(s2, msg)
                    if self.on_move:
                        self.on_move(tuple(msg["from"]),
                                     tuple(msg["to"]),
                                     color)

    def send_move(self, fr, to, color):
        """Host makes a move → broadcast to all clients."""
        data = {"type":"move","color":color,"from":fr,"to":to}
        b   = json.dumps(data).encode()
        sig = self.private_key.sign(
            b,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256()
        ).hex()
        packet = {"type":"move","color":color,"from":fr,"to":to,"sig":sig}
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
        self.host_addr = (host_ip, port)
        self.sock      = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(self.host_addr)

        # generate my keypair
        self.private_key = rsa.generate_private_key(65537,2048)
        self.public_key  = self.private_key.public_key()

        self.color        = None
        self.peer_pubkeys = {}
        self.on_move      = None

        # listener
        threading.Thread(target=self._listen, daemon=True).start()

        # wait for assign, send pubkey, wait for init
        msg = recv_json(self.sock)
        assert msg["type"]=="assign"
        self.color = msg["color"]

        # send pubkey
        pem = self.public_key.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        send_json(self.sock, {
            "type":"pubkey", "color": self.color, "pem": pem
        })

        # receive init
        init = recv_json(self.sock)
        assert init["type"]=="init"
        # load all pubkeys
        for c,pem in init["pubkeys"].items():
            self.peer_pubkeys[c] = serialization.load_pem_public_key(
                pem.encode()
            )

    def send_move(self, fr, to):
        """Client makes a move → send to host (it will relay)."""
        data = {"type":"move","color":self.color,"from":fr,"to":to}
        b    = json.dumps(data).encode()
        sig  = self.private_key.sign(
            b,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256()
        ).hex()
        packet = {"type":"move","color":self.color,
                  "from":fr,"to":to,"sig":sig}
        send_json(self.sock, packet)

    def _listen(self):
        """Receive relayed moves from host."""
        while True:
            msg = recv_json(self.sock)
            if msg["type"]=="move":
                # already verified by host
                if self.on_move:
                    self.on_move(tuple(msg["from"]),
                                 tuple(msg["to"]),
                                 msg["color"])
