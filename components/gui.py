import pygame
from .game import Game
from .player import players_colors, player_names
from .pieces import Pawn, Rook, Knight, Bishop, Queen, King

CELL = 800 // 14
FPS = 30
TEXT_HEIGHT = 30

# outline colors per player in multiplayer
OUTLINE_COLORS = {
    'w': (255, 255, 255),  # white
    'r': (255, 0, 0),  # red
    'b': (0, 0, 0),  # black
    'g': (0, 255, 0),  # green
}

class GUI:
    def __init__(self, game: Game, local_color=None, network=None):
        pygame.init()
        pygame.font.init()
        self.game = game
        self.local_color = local_color
        self.network = network
        self.window = pygame.display.set_mode((CELL*14, CELL*14 + TEXT_HEIGHT))
        pygame.display.set_caption("4-Player Chess")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, TEXT_HEIGHT)
        self.images = self._load_images()

    def _load_images(self):
        imgs = {}
        for color in players_colors:
            for cls in [Pawn, Rook, Knight, Bishop, Queen, King]:
                key = (color, cls.symbol)
                img = pygame.image.load(f"assets/{color}{cls.symbol}.png").convert_alpha()
                imgs[key] = pygame.transform.scale(img, (CELL, CELL))
        return imgs

    def _is_forbidden(self, pos):
        r, c = pos
        return (r < 3 and c < 3) or (r < 3 and c >= 11) or (r >= 11 and c < 3) or (r >= 11 and c >= 11)

    def draw(self):
        # determine eliminated players
        dead = {c for c in players_colors if not self.game.is_alive(c)}

        # draw board cells
        for r in range(14):
            for c in range(14):
                rect = pygame.Rect(c*CELL, r*CELL, CELL, CELL)
                if self._is_forbidden((r, c)):
                    pygame.draw.rect(self.window, (0, 0, 0), rect)
                else:
                    color = (235, 209, 166) if (r + c) % 2 == 0 else (165, 117, 81)
                    pygame.draw.rect(self.window, color, rect)

        # highlight selected tile
        if self.game.selected:
            r, c = self.game.selected
            pygame.draw.rect(self.window, (255, 255, 0), (c*CELL, r*CELL, CELL, CELL), 4)

        # draw pieces, dim eliminated
        for r in range(14):
            for c in range(14):
                piece = self.game.board.get_piece((r, c))
                if piece:
                    img = self.images[(piece.color, piece.symbol)].copy()
                    if piece.color in dead:
                        img.set_alpha(100)
                    self.window.blit(img, (c*CELL, r*CELL))

        # multiplayer outline for your color if still alive
        if self.local_color and self.local_color not in dead:
            outline = OUTLINE_COLORS.get(self.local_color, (255, 255, 255))
            pygame.draw.rect(self.window, outline, (0, 0, CELL*14, CELL*14), 4)

        # turn message area
        pygame.draw.rect(self.window, (0, 0, 0), (0, CELL*14, CELL*14, TEXT_HEIGHT))
        current = self.game.current_player().color
        if current in dead:
            msg = "Player " + player_names[current] + " eliminated"
        elif self.local_color and current != self.local_color:
            msg = f"Waiting for player {player_names[current]}"
        else:
            msg = f"{player_names[current]}'s turn"
        surf = self.font.render(msg, True, (255, 255, 255))
        self.window.blit(surf, (10, CELL*14 + (TEXT_HEIGHT - surf.get_height())//2))

    def run(self):
        valid_moves = []
        running = True
        while running:
            self.clock.tick(FPS)
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    running = False
                elif e.type == pygame.MOUSEBUTTONDOWN:
                    pos = (e.pos[1]//CELL, e.pos[0]//CELL)
                    if self._is_forbidden(pos):
                        continue
                    # skip if dead or not your turn in multiplayer
                    if self.local_color and (not self.game.is_alive(self.local_color) or self.game.current_player().color != self.local_color):
                        continue
                    piece = self.game.board.get_piece(pos)
                    # select or re-select your piece
                    if not self.game.selected or (piece and piece.color == self.game.current_player().color):
                        raw = self.game.select(pos)
                        valid_moves = [m for m in raw if not self._is_forbidden(m)]
                    else:
                        sel = self.game.selected
                        if self.game.move(pos):
                            if self.network:
                                self.network.send_move(sel, pos)
                            valid_moves = []
            self.draw()
            # highlight valid destinations
            for mr, mc in valid_moves:
                pygame.draw.circle(self.window, (0, 255, 0), (mc*CELL + CELL//2, mr*CELL + CELL//2), 10)
            pygame.display.flip()
        pygame.quit()
