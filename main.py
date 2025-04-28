import pygame
import sys
import random
import string
from components.game import Game
from components.gui import GUI
from components.net import Network
from components.player import players_colors

import socket
import time
import json

# UDP settings for discovery
DISCOVERY_PORT = 5001
DISCOVERY_TIMEOUT = 30
BROADCAST_ADDRESS = '255.255.255.255'

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
    font = pygame.font.SysFont(None, 32)
    create_rect = pygame.Rect(100, 60, BUTTON_W, BUTTON_H)
    join_rect   = pygame.Rect(100, 150, BUTTON_W, BUTTON_H)

    while True:
        screen.fill((60, 60, 60))
        pygame.draw.rect(screen, (100, 200, 100), create_rect)
        screen.blit(font.render("Create Room", True, (0, 0, 0)),
                    (create_rect.x + 20, create_rect.y + 10))
        pygame.draw.rect(screen, (200, 200, 100), join_rect)
        screen.blit(font.render("Join Room", True, (0, 0, 0)),
                    (join_rect.x + 20, join_rect.y + 10))

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.MOUSEBUTTONDOWN:
                if create_rect.collidepoint(e.pos):
                    return 'create'
                if join_rect.collidepoint(e.pos):
                    return 'join'

        pygame.display.flip()

def input_code(prompt="Enter room code: "):
    screen = pygame.display.get_surface()
    font = pygame.font.SysFont(None, 28)
    code = ""

    while True:
        screen.fill((30, 30, 30))
        screen.blit(font.render(prompt + code, True, (255, 255, 255)),
                    (20, 20))
        pygame.display.flip()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_RETURN and code:
                    return code
                elif e.key == pygame.K_BACKSPACE:
                    code = code[:-1]
                elif len(e.unicode) == 1:
                    code += e.unicode

# for creating a room code for 4 players to join
def generate_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits,
                                  k=length))

def decode_peers_from_code(code, mode):
    '''
    mode = "join" or "create"
    returns a list of tuples (ip, port)
    '''    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(DISCOVERY_TIMEOUT)
    sock.bind(('', DISCOVERY_PORT))
    peers = []
    start = time.time()
    if mode == "create":
        while time.time() - start < DISCOVERY_TIMEOUT:
            try:
                data, addr = sock.recvfrom(1024)
                msg = json.loads(data.decode())
                if msg.get('type') == 'join' and msg.get('code') == code:
                    peer = (addr[0], 5000)
                    if peer not in peers:
                        print(f"Peer found: {peer}")
                        peers.append(peer)
                        resp = {'type': 'host', 'code': code}
                        sock.sendto(json.dumps(resp).encode(), addr)
            except socket.timeout:
                continue
    else:
        join_msg = json.dumps({'type': 'join', 'code': code})
        while time.time() - start < DISCOVERY_TIMEOUT:
            sock.sendto(join_msg.encode(), (BROADCAST_ADDRESS, DISCOVERY_PORT))
            time.sleep(1)
        # collect host responses
        start = time.time()
        while time.time() - start < DISCOVERY_TIMEOUT:
            try:
                data, addr = sock.recvfrom(1024)
                msg = json.loads(data.decode())
                if msg.get('type') == 'host' and msg.get('code') == code:
                    peer = (addr[0], 5000)
                    if peer not in peers:
                        peers.append(peer)
            except socket.timeout:
                continue
    sock.close()
    return peers

def choose_color():
    while True:
        c = input(f"Choose your color {players_colors}: ").lower()
        if c in players_colors:
            return c

def main():
    mode = show_menu()
    pygame.display.quit()

    if mode == 'single':
        game = Game()
        gui = GUI(game)
        gui.run()
        return

    pygame.init()
    pygame.display.set_mode((SCREEN_W, SCREEN_H))
    mp_choice = show_mp_menu()

    if mp_choice == 'create':
        room_code = generate_code()
        input_code(f"Room created: {room_code}(press Enter to continue)")
    else:
        room_code = input_code()

    peers = decode_peers_from_code(room_code, mp_choice)
    if mp_choice == 'join':
        host_ip = input_code("Could not autodiscover room creator. Enter room creator IP: ")
        peers = [(host_ip.strip(), 5000)]
    local_color = choose_color()

    game = Game()
    network = Network(local_color, peers)
    game.on_remote_move = game.apply_remote_move
    network.on_move   = game.on_remote_move

    gui = GUI(game, local_color=local_color, network=network)
    gui.run()

if __name__ == '__main__':
    main()
