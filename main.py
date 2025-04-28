import pygame, sys
from components.game import Game
from components.gui  import GUI
from components.net  import HostNetwork, ClientNetwork

SCREEN_W, SCREEN_H = 500,300

def show_menu():
    pygame.init()
    screen=pygame.display.set_mode((SCREEN_W,SCREEN_H))
    font = pygame.font.SysFont(None,36)
    a=pygame.Rect(100,60,200,50)
    b=pygame.Rect(100,150,200,50)
    while True:
        screen.fill((50,50,50))
        pygame.draw.rect(screen,(100,100,200),a)
        pygame.draw.rect(screen,(200,100,100),b)
        screen.blit(font.render("Single-Player",1,(255,255,255)),(a.x+20,a.y+10))
        screen.blit(font.render("Multi-Player",1,(255,255,255)),(b.x+20,b.y+10))
        for e in pygame.event.get():
            if e.type==pygame.QUIT: sys.exit()
            if e.type==pygame.MOUSEBUTTONDOWN:
                if a.collidepoint(e.pos): return 'single'
                if b.collidepoint(e.pos): return 'multi'
        pygame.display.flip()

def show_mp_menu():
    screen=pygame.display.get_surface()
    font=pygame.font.SysFont(None,32)
    a=pygame.Rect(100,60,200,50)
    b=pygame.Rect(100,150,200,50)
    while True:
        screen.fill((60,60,60))
        pygame.draw.rect(screen,(100,200,100),a)
        pygame.draw.rect(screen,(200,200,100),b)
        screen.blit(font.render("Host Game",True,(0,0,0)),(a.x+20,a.y+10))
        screen.blit(font.render("Join Game",True,(0,0,0)),(b.x+20,b.y+10))
        for e in pygame.event.get():
            if e.type==pygame.QUIT: sys.exit()
            if e.type==pygame.MOUSEBUTTONDOWN:
                if a.collidepoint(e.pos): return 'host'
                if b.collidepoint(e.pos): return 'join'
        pygame.display.flip()

def main():
    mode = show_menu()
    pygame.display.quit()

    if mode=='single':
        game = Game()
        gui  = GUI(game)
        gui.run()
        return

    pygame.init()
    pygame.display.set_mode((SCREEN_W,SCREEN_H))
    choice = show_mp_menu()

    if choice=='host':
        host_net = HostNetwork()
        print("[HOST] Waiting for players (min 2, max 4). Press S to start.")
        # in your main loop you could listen for S; for brevity:
        while True:
            for e in pygame.event.get():
                if e.type==pygame.KEYDOWN and e.key==pygame.K_s:
                    if len(host_net.clients)+1 >= 2:
                        host_net.start_game()
                        goto_game = True
                        break
            if 'goto_game' in locals(): break
        game = Game()
        host_net.on_move = game.apply_remote_move
        gui = GUI(game, local_color=host_net.assignments[('HOST',host_net.port)],
                  network=host_net)
        gui.run()

    else:  # join
        # ask for host IP
        host_ip = input("Enter host IP (e.g. 10.10.54.196): ").strip()
        cli_net = ClientNetwork(host_ip)
        game    = Game()
        cli_net.on_move = game.apply_remote_move
        gui = GUI(game, local_color=cli_net.color, network=cli_net)
        gui.run()

if __name__=='__main__':
    main()
