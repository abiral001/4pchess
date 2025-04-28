import pygame
import sys
import socket
from components.game import Game
from components.gui import GUI
from components.net import HostNetwork, ClientNetwork

SCREEN_W, SCREEN_H = 500, 300
BUTTON_W, BUTTON_H = 200, 50

def show_menu():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("4-Player Chess")
    font = pygame.font.SysFont(None, 36)
    single_rect = pygame.Rect(100, 60, BUTTON_W, BUTTON_H)
    multi_rect  = pygame.Rect(100, 150, BUTTON_W, BUTTON_H)

    while True:
        screen.fill((50, 50, 50))
        pygame.draw.rect(screen, (100, 100, 200), single_rect)
        screen.blit(font.render("Single-Player", True, (255, 255, 255)),
                    (single_rect.x + 20, single_rect.y + 10))
        pygame.draw.rect(screen, (200, 100, 100), multi_rect)
        screen.blit(font.render("Multi-Player", True, (255, 255, 255)),
                    (multi_rect.x + 20, multi_rect.y + 10))

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.MOUSEBUTTONDOWN:
                if single_rect.collidepoint(e.pos):
                    return 'single'
                if multi_rect.collidepoint(e.pos):
                    return 'multi'

        pygame.display.flip()

def show_mp_menu():
    screen = pygame.display.get_surface()
    font   = pygame.font.SysFont(None, 32)
    host_rect = pygame.Rect(100, 60, BUTTON_W, BUTTON_H)
    join_rect = pygame.Rect(100, 150, BUTTON_W, BUTTON_H)

    while True:
        screen.fill((60, 60, 60))
        pygame.draw.rect(screen, (100, 200, 100), host_rect)
        screen.blit(font.render("Host Game", True, (0, 0, 0)),
                    (host_rect.x + 20, host_rect.y + 10))
        pygame.draw.rect(screen, (200, 200, 100), join_rect)
        screen.blit(font.render("Join Game", True, (0, 0, 0)),
                    (join_rect.x + 20, join_rect.y + 10))

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.MOUSEBUTTONDOWN:
                if host_rect.collidepoint(e.pos):
                    return 'host'
                if join_rect.collidepoint(e.pos):
                    return 'join'

        pygame.display.flip()

def input_text_screen(prompt, width=300, height=50):
    screen = pygame.display.get_surface()
    font   = pygame.font.SysFont(None, 28)
    clock  = pygame.time.Clock()

    box = pygame.Rect((SCREEN_W - width)//2,
                      (SCREEN_H - height)//2,
                      width, height)
    color_inactive = pygame.Color('lightskyblue3')
    color_active   = pygame.Color('dodgerblue2')
    color = color_inactive
    active = True
    text = ''

    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and active:
                if e.key == pygame.K_RETURN:
                    return text.strip()
                elif e.key == pygame.K_BACKSPACE:
                    text = text[:-1]
                else:
                    if len(e.unicode) == 1:
                        text += e.unicode

        screen.fill((30, 30, 30))
        prompt_surf = font.render(prompt, True, (200, 200, 200))
        screen.blit(prompt_surf, (box.x, box.y - 30))
        pygame.draw.rect(screen, color, box, 2)
        txt_surf = font.render(text, True, (255, 255, 255))
        screen.blit(txt_surf, (box.x + 5, box.y + 10))

        pygame.display.flip()
        clock.tick(30)

def get_local_ip():
    """Returns the LAN IP by connecting a dummy socket."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()

def main():
    mode = show_menu()
    pygame.display.quit()

    if mode == 'single':
        game = Game()
        gui  = GUI(game)
        gui.run()
        return

    pygame.init()
    pygame.display.set_mode((SCREEN_W, SCREEN_H))
    choice = show_mp_menu()

    if choice == 'host':
        host_net = HostNetwork()
        font    = pygame.font.SysFont(None, 28)
        screen  = pygame.display.get_surface()
        local_ip = get_local_ip()

        # Host waiting screen
        while True:
            screen.fill((30, 30, 30))
            ip_surf   = font.render(f"Host IP: {local_ip}", True, (255,255,255))
            prompt_surf = font.render("Waiting for players (2–4). Press S to start.", True, (200,200,200))
            screen.blit(ip_surf, (20, SCREEN_H//2 - 40))
            screen.blit(prompt_surf, (20, SCREEN_H//2))
            pygame.display.flip()

            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if e.type == pygame.KEYDOWN and e.key == pygame.K_s:
                    if len(host_net.clients) + 1 >= 2:
                        host_net.start_game()
                        goto_game = True
                        break
            if 'goto_game' in locals():
                break

        game = Game()
        host_net.on_move = game.apply_remote_move
        local_color = host_net.assignments.get(('HOST', host_net.port))
        gui = GUI(game, local_color=local_color, network=host_net)
        gui.run()

    else:  # join
        host_ip = input_text_screen("Enter host IP (e.g. 10.10.54.196):", width=280)
        cli_net = ClientNetwork(host_ip)

        game = Game()
        cli_net.on_move = game.apply_remote_move
        gui = GUI(game, local_color=cli_net.color, network=cli_net)
        gui.run()

if __name__ == '__main__':
    main()
