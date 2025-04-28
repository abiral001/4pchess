from abc import ABC, abstractmethod

# Direction vectors for pawn movement by color
dirs = {
    'w': (-1, 0),  # up
    'b': ( 1, 0),  # down
    'r': ( 0, -1),  # left
    'g': ( 0, 1),  # right
}

class Piece(ABC):
    symbol = '?'  # override in subclasses

    def __init__(self, color):
        self.color = color

    @abstractmethod
    def legal_moves(self, board, pos):
        """Return list of (r,c) legal destinations from pos"""
        pass

class Pawn(Piece):
    symbol = 'P'

    def legal_moves(self, board, pos):
        moves = []
        r, c = pos
        dr, dc = dirs[self.color]
        # one-step forward
        nr, nc = r + dr, c + dc
        if board.in_bounds((nr, nc)) and board.is_empty((nr, nc)):
            moves.append((nr, nc))
        # captures
        for odir in [(-dc, dr), (dc, -dr)]:
            cr, cc = r + dr + odir[0], c + dc + odir[1]
            if board.in_bounds((cr, cc)):
                target = board.get_piece((cr, cc))
                if target and target.color != self.color:
                    moves.append((cr, cc))
        return moves

class Rook(Piece):
    symbol = 'R'

    def legal_moves(self, board, pos):
        moves = []
        r, c = pos
        for dr, dc in [(1,0),(-1,0),(0,1),(0,-1)]:
            nr, nc = r+dr, c+dc
            while board.in_bounds((nr, nc)):
                if board.is_empty((nr, nc)):
                    moves.append((nr, nc))
                else:
                    if board.get_piece((nr, nc)).color != self.color:
                        moves.append((nr, nc))
                    break
                nr += dr; nc += dc
        return moves

class Bishop(Piece):
    symbol = 'B'

    def legal_moves(self, board, pos):
        moves = []
        r, c = pos
        for dr, dc in [(1,1),(1,-1),(-1,1),(-1,-1)]:
            nr, nc = r+dr, c+dc
            while board.in_bounds((nr, nc)):
                if board.is_empty((nr, nc)):
                    moves.append((nr, nc))
                else:
                    if board.get_piece((nr, nc)).color != self.color:
                        moves.append((nr, nc))
                    break
                nr += dr; nc += dc
        return moves

class Knight(Piece):
    symbol = 'N'

    def legal_moves(self, board, pos):
        moves = []
        r, c = pos
        for dr, dc in [(2,1),(2,-1),(-2,1),(-2,-1),(1,2),(1,-2),(-1,2),(-1,-2)]:
            nr, nc = r+dr, c+dc
            if board.in_bounds((nr, nc)):
                target = board.get_piece((nr, nc))
                if target is None or target.color != self.color:
                    moves.append((nr, nc))
        return moves

class Queen(Piece):
    symbol = 'Q'

    def legal_moves(self, board, pos):
        # combine rook + bishop moves
        return Rook.legal_moves(self, board, pos) + Bishop.legal_moves(self, board, pos)

class King(Piece):
    symbol = 'K'

    def legal_moves(self, board, pos):
        moves = []
        r, c = pos
        for dr, dc in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
            nr, nc = r+dr, c+dc
            if board.in_bounds((nr, nc)):
                target = board.get_piece((nr, nc))
                if target is None or target.color != self.color:
                    moves.append((nr, nc))
        return moves
