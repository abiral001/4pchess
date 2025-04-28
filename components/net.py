import socket
import threading
import json
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization

class Network:
    def __init__(self, color, peers, port=5000):
        """
        color: one of 'w', 'r', 'b', 'g'
        peers: list of (host, port) tuples to broadcast to
        """
        self.color = color
        self.peers = peers or []
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', port))

        # generate RSA key pair
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()

        # serialize and broadcast our public key
        pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        key_msg = {'type': 'pubkey', 'color': color, 'pem': pem}
        for peer in self.peers:
            self.sock.sendto(json.dumps(key_msg).encode(), peer)

        # store peers' public keys here
        self.peer_pubkeys = {}
        # callback to invoke on verified move: on_move(from_pos, to_pos, color)
        self.on_move = None

        # start listening in background
        threading.Thread(target=self._listen, daemon=True).start()

    def sign(self, msg_bytes):
        return self.private_key.sign(
            msg_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

    def send_move(self, from_pos, to_pos):
        """
        Broadcast a signed move to all peers.
        from_pos and to_pos are 2-tuples, e.g. (r, c).
        """
        msg = {
            'type':  'move',
            'color': self.color,
            'from':  from_pos,
            'to':    to_pos
        }
        data = json.dumps(msg).encode()
        sig  = self.sign(data).hex()
        packet = {'msg': msg, 'sig': sig}

        for peer in self.peers:
            self.sock.sendto(json.dumps(packet).encode(), peer)

    def _listen(self):
        while True:
            data, _ = self.sock.recvfrom(65536)
            packet = json.loads(data.decode())
            msg    = packet.get('msg')
            if not msg:
                continue

            if msg['type'] == 'pubkey':
                # register new peer's public key
                self.peer_pubkeys[msg['color']] = serialization.load_pem_public_key(
                    msg['pem'].encode()
                )
                continue

            if msg['type'] == 'move':
                pub = self.peer_pubkeys.get(msg['color'])
                if not pub:
                    continue
                sig = bytes.fromhex(packet.get('sig', ''))
                try:
                    pub.verify(
                        sig,
                        json.dumps(msg).encode(),
                        padding.PSS(
                            mgf=padding.MGF1(hashes.SHA256()),
                            salt_length=padding.PSS.MAX_LENGTH
                        ),
                        hashes.SHA256()
                    )
                except Exception:
                    # invalid signature
                    continue

                # if verified, invoke callback
                if self.on_move:
                    fr = tuple(msg['from'])
                    to = tuple(msg['to'])
                    self.on_move(fr, to, msg['color'])
