from .board import Board
from .player import Player, players_colors

class Game:
    def __init__(self):
        self.board = Board()
        self.players = [Player(c) for c in players_colors]
        self.turn = 0
        self.selected = None
        self.on_remote_move = None

        # track colors with no player
        self.disabled_colors = set()

    def disable_color(self, color):
        """Mark a color as inactive (no human/host assigned)."""
        self.disabled_colors.add(color)

    def is_alive(self, color):
        """Return False if color is disabled or its king is gone."""
        if color in self.disabled_colors:
            return False
        return any(
            piece.symbol == 'K' and piece.color == color
            for row in self.board.grid
            for piece in row if piece
        )

    def current_player(self):
        """Return the next alive (and non-disabled) player."""
        n = len(self.players)
        for _ in range(n):
            player = self.players[self.turn]
            if self.is_alive(player.color):
                return player
            # skip disabled/dead
            self.turn = (self.turn + 1) % n
        # fallback
        return self.players[self.turn]

    def advance_turn(self):
        """Advance to the following alive player."""
        n = len(self.players)
        self.turn = (self.turn + 1) % n
        while not self.is_alive(self.players[self.turn].color):
            self.turn = (self.turn + 1) % n

    def select(self, pos):
        """Select a piece if it belongs to the current alive player."""
        color = self.current_player().color
        if not self.is_alive(color):
            return []
        piece = self.board.get_piece(pos)
        if piece and piece.color == color:
            self.selected = pos
            return piece.legal_moves(self.board, pos)
        return []

    def move(self, to_pos):
        """
        Make a local move for the current player.
        Returns True if successful.
        """
        color = self.current_player().color
        if not self.is_alive(color) or self.selected is None:
            return False
        if self.board.move(color, self.selected, to_pos):
            self.selected = None
            self.advance_turn()
            return True
        return False

    def apply_remote_move(self, from_pos, to_pos, color):
        """
        Apply a move received over the network.
        Fast-forwards to that color, makes the move, then advances.
        """
        if not self.is_alive(color):
            return

        # fast-forward until it's that player's turn
        while self.current_player().color != color:
            self.turn = (self.turn + 1) % len(self.players)

        # apply move (no need to re-check legality here)
        self.board.move(color, from_pos, to_pos)

        # advance to next alive player
        self.advance_turn()
        self.selected = None
