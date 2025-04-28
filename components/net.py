import socket
import threading
import json
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization

class Network:
    def __init__(self, color, peers, port=5000, announce_pubkey=True):
        """
        color: one of 'w','r','b','g' (or None for joiners awaiting assignment)
        peers: list of (host, port) tuples to talk to
        announce_pubkey: if False, we'll defer sending our public key until after assignment
        """
        self.color = color
        self.peers = peers or []
        self.sock  = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', port))

        # generate RSA key pair
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key  = self.private_key.public_key()

        # callbacks
        self.on_move   = None   # signature-verified moves: callable(fr, to, color)
        self.on_assign = None   # host→joiner color assignment: callable(color)

        # only broadcast our pubkey now if host (announce_pubkey=True and color set)
        if announce_pubkey and self.color:
            self._broadcast_pubkey()

        # start listener
        threading.Thread(target=self._listen, daemon=True).start()

    def _broadcast_pubkey(self):
        """Send our public key to every peer."""
        pem     = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        key_msg = {'type':'pubkey', 'color':self.color, 'pem':pem}
        packet  = json.dumps(key_msg).encode()
        for peer in self.peers:
            self.sock.sendto(packet, peer)

    def send_assignments(self, assignments):
        """
        Host-only: inform each peer of its assigned color.
        assignments: dict mapping (host,port)->color
        """
        for peer, color in assignments.items():
            msg    = {'type':'assign', 'color': color}
            packet = json.dumps(msg).encode()
            self.sock.sendto(packet, peer)

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
        from_pos and to_pos are 2-tuples, e.g. (row, col).
        """
        msg = {
            'type': 'move',
            'color': self.color,
            'from':  from_pos,
            'to':    to_pos
        }
        data   = json.dumps(msg).encode()
        sig    = self.sign(data).hex()
        packet = json.dumps({'msg': msg, 'sig': sig}).encode()

        for peer in self.peers:
            self.sock.sendto(packet, peer)

    def _listen(self):
        while True:
            data, addr = self.sock.recvfrom(65536)
            try:
                packet = json.loads(data.decode())
            except Exception:
                continue

            # 1) Color assignment from host
            if packet.get('type') == 'assign':
                assigned = packet.get('color')
                if self.on_assign:
                    self.on_assign(assigned)
                continue

            # 2) Public key exchange
            msg = packet.get('msg')
            if not msg:
                continue

            if msg.get('type') == 'pubkey':
                # register a new peer's public key
                self.peer_pubkeys[msg['color']] = serialization.load_pem_public_key(
                    msg['pem'].encode()
                )
                continue

            # 3) Signed move
            if msg.get('type') == 'move':
                pub = self.peer_pubkeys.get(msg['color'])
                if not pub:
                    # we haven't received that peer's pubkey yet
                    continue

                sig = bytes.fromhex(packet.get('sig',''))
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
                    # signature invalid
                    continue

                # verified—invoke the move callback
                if self.on_move:
                    fr = tuple(msg['from'])
                    to = tuple(msg['to'])
                    self.on_move(fr, to, msg['color'])
