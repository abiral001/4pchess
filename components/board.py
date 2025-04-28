from .pieces import Pawn, Rook, Knight, Bishop, Queen, King
from .player import players_colors

class Board:
    def __init__(self, size=14):
        self.size = size
        self.grid = [[None] * size for _ in range(size)]
        self._init_pieces()

    def in_bounds(self, pos):
        r, c = pos
        return 0 <= r < self.size and 0 <= c < self.size

    def is_empty(self, pos):
        r, c = pos
        return self.grid[r][c] is None

    def get_piece(self, pos):
        r, c = pos
        return self.grid[r][c]

    def set_piece(self, pos, piece):
        r, c = pos
        self.grid[r][c] = piece

    def _init_pieces(self):
        back_order = [Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook]
        # white (bottom)
        for i, cls in enumerate(back_order):
            self.set_piece((13, 3 + i), cls('w'))
            self.set_piece((12, 3 + i), Pawn('w'))
        # black (top)
        for i, cls in enumerate(back_order):
            self.set_piece((0, 3 + i), cls('b'))
            self.set_piece((1, 3 + i), Pawn('b'))
        # red (right)
        for i, cls in enumerate(back_order):
            self.set_piece((3 + i, 13), cls('r'))
            self.set_piece((3 + i, 12), Pawn('r'))
        # green (left)
        for i, cls in enumerate(back_order):
            self.set_piece((3 + i, 0), cls('g'))
            self.set_piece((3 + i, 1), Pawn('g'))

    def move(self, color, from_pos, to_pos):
        piece = self.get_piece(from_pos)
        if not piece or piece.color != color:
            return False
        if to_pos not in piece.legal_moves(self, from_pos):
            return False
        # perform move / capture
        self.set_piece(to_pos, piece)
        self.set_piece(from_pos, None)
        return True
