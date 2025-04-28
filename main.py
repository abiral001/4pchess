import pygame, sys, socket, threading, time
from components.game   import Game
from components.gui    import GUI
from components.net    import HostNetwork, ClientNetwork
from components.player import players_colors

SCREEN_W, SCREEN_H = 500, 300
BUTTON_W, BUTTON_H = 200, 50

def show_menu():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("4-Player Chess")
    font = pygame.font.SysFont(None,36)
    single = pygame.Rect(100,60,BUTTON_W,BUTTON_H)
    multi  = pygame.Rect(100,150,BUTTON_W,BUTTON_H)
    while True:
        screen.fill((50,50,50))
        pygame.draw.rect(screen,(100,100,200),single)
        pygame.draw.rect(screen,(200,100,100),multi)
        screen.blit(font.render("Single-Player",True,(255,255,255)),
                    (single.x+20,single.y+10))
        screen.blit(font.render("Multi-Player",True,(255,255,255)),
                    (multi.x+20,multi.y+10))
        for e in pygame.event.get():
            if e.type==pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type==pygame.MOUSEBUTTONDOWN:
                if single.collidepoint(e.pos): return 'single'
                if multi.collidepoint(e.pos):  return 'multi'
        pygame.display.flip()

def show_mp_menu():
    screen=pygame.display.get_surface()
    font=pygame.font.SysFont(None,32)
    host_b=pygame.Rect(100,60,BUTTON_W,BUTTON_H)
    join_b=pygame.Rect(100,150,BUTTON_W,BUTTON_H)
    while True:
        screen.fill((60,60,60))
        pygame.draw.rect(screen,(100,200,100),host_b)
        pygame.draw.rect(screen,(200,200,100),join_b)
        screen.blit(font.render("Host Game",True,(0,0,0)),
                    (host_b.x+20,host_b.y+10))
        screen.blit(font.render("Join Game",True,(0,0,0)),
                    (join_b.x+20,join_b.y+10))
        for e in pygame.event.get():
            if e.type==pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type==pygame.MOUSEBUTTONDOWN:
                if host_b.collidepoint(e.pos): return 'host'
                if join_b.collidepoint(e.pos): return 'join'
        pygame.display.flip()

def input_text_screen(prompt,width=300,height=50):
    screen=pygame.display.get_surface()
    font=pygame.font.SysFont(None,28)
    clock=pygame.time.Clock()
    box=pygame.Rect((SCREEN_W-width)//2,(SCREEN_H-height)//2,width,height)
    text=''
    while True:
        for e in pygame.event.get():
            if e.type==pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN:
                if e.key==pygame.K_RETURN:
                    return text.strip()
                elif e.key==pygame.K_BACKSPACE:
                    text=text[:-1]
                else:
                    if len(e.unicode)==1:
                        text+=e.unicode
        screen.fill((30,30,30))
        screen.blit(font.render(prompt,True,(200,200,200)),(box.x,box.y-30))
        pygame.draw.rect(screen,pygame.Color('lightskyblue3'),box,2)
        screen.blit(font.render(text,True,(255,255,255)),(box.x+5,box.y+10))
        pygame.display.flip()
        clock.tick(30)

def show_message_screen(msg,fg=(255,50,50)):
    screen=pygame.display.get_surface()
    font=pygame.font.SysFont(None,28)
    clock=pygame.time.Clock()
    while True:
        screen.fill((30,30,30))
        surf=font.render(msg,True,fg)
        rect=surf.get_rect(center=(SCREEN_W//2,SCREEN_H//2))
        screen.blit(surf,rect)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type==pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN:
                return
        clock.tick(30)

def get_local_ip():
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8",80))
        return s.getsockname()[0]
    except:
        return "127.0.0.1"
    finally:
        s.close()

def main():
    mode=show_menu()
    pygame.display.quit()
    if mode=='single':
        g=Game(); GUI(g).run(); return

    pygame.init()
    pygame.display.set_mode((SCREEN_W,SCREEN_H))
    choice=show_mp_menu()

    if choice=='host':
        host_net=HostNetwork()
        screen=pygame.display.get_surface()
        font=pygame.font.SysFont(None,28)
        local_ip=get_local_ip()
        started=False
        while not started:
            screen.fill((30,30,30))
            screen.blit(font.render(f"Host IP: {local_ip}",True,(255,255,255)),
                        (20,SCREEN_H//2-40))
            screen.blit(font.render(
                f"Players: {len(host_net.clients)+1}/4. Press S to start",
                True,(200,200,200)
            ),(20,SCREEN_H//2))
            pygame.display.flip()
            for e in pygame.event.get():
                if e.type==pygame.QUIT:
                    pygame.quit(); sys.exit()
                if e.type==pygame.KEYDOWN and e.key==pygame.K_s:
                    if len(host_net.clients)+1>=2:
                        threading.Thread(target=host_net.start_game,
                                         daemon=True).start()
                        started=True
                        break
        while len(host_net.peer_pubkeys)<len(host_net.assignments):
            screen.fill((30,30,30))
            screen.blit(font.render("Initializing...",True,(255,255,255)),
                        (20,SCREEN_H//2-10))
            screen.blit(font.render(
                f"Keys: {len(host_net.peer_pubkeys)}/"
                f"{len(host_net.assignments)}",True,(200,200,200)
            ),(20,SCREEN_H//2+20))
            pygame.display.flip()
            pygame.time.delay(100)

        game=Game()
        host_net.on_move=game.apply_remote_move
        assigned=set(host_net.assignments.values())
        for c in players_colors:
            if c not in assigned:
                game.disable_color(c)
        lc=host_net.assignments[('HOST',host_net.port)]
        GUI(game,local_color=lc,network=host_net).run()

    else:
        while True:
            ip=input_text_screen("Enter host IP:",width=280)
            try:
                cli_net=ClientNetwork(ip)
                break
            except ConnectionRefusedError:
                show_message_screen("Connection refused. Any key to retry.")
        while not cli_net.ready:
            screen=pygame.display.get_surface()
            font=pygame.font.SysFont(None,28)
            screen.fill((30,30,30))
            screen.blit(font.render("Joining...",True,(255,255,255)),
                        (20,SCREEN_H//2-10))
            pygame.display.flip()
            pygame.time.delay(100)
        game=Game()
        cli_net.on_move=game.apply_remote_move
        assigned=set(cli_net.assignments.values())
        for c in players_colors:
            if c not in assigned:
                game.disable_color(c)
        GUI(game,local_color=cli_net.color,network=cli_net).run()

if __name__=='__main__':
    main()
