from .board import Board
from .player import Player, players_colors

class Game:
    def __init__(self):
        self.board = Board()
        self.players = [Player(c) for c in players_colors]
        self.turn = 0
        self.selected = None
        self.on_remote_move = None  # hook for network

    def current_player(self):
        return self.players[self.turn]

    def is_alive(self, color):
        # True if that color’s king is still on the board
        return any(
            piece.symbol == 'K' and piece.color == color
            for row in self.board.grid
            for piece in row if piece
        )

    def advance_turn(self):
        # Move to next player who is still alive
        self.turn = (self.turn + 1) % len(self.players)
        while not self.is_alive(self.current_player().color):
            self.turn = (self.turn + 1) % len(self.players)

    def select(self, pos):
        color = self.current_player().color
        if not self.is_alive(color):
            return []
        piece = self.board.get_piece(pos)
        if piece and piece.color == color:
            self.selected = pos
            return piece.legal_moves(self.board, pos)
        return []

    def move(self, to_pos):
        color = self.current_player().color
        if not self.is_alive(color) or self.selected is None:
            return False
        if self.board.move(color, self.selected, to_pos):
            self.selected = None
            self.advance_turn()
            return True
        return False

    def apply_remote_move(self, from_pos, to_pos, color):
        # ignore moves from dead players
        if not self.is_alive(color):
            return

        # fast‑forward to that player’s turn
        while self.current_player().color != color:
            self.turn = (self.turn + 1) % len(self.players)

        # apply the move
        self.board.move(color, from_pos, to_pos)

        # advance to next live player
        self.advance_turn()
        self.selected = None
