import time
import queue
import math
from datetime import datetime as dt_dt
import datetime as dt
import socket as sckt
import sys
from progress_bar import Bar
from connect_utils import Pkt
import numpy as np
from win_cmd import Console
from PIL import Image
import os
from GameLogic import pos
from ImageProcessing import *
import zlib
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
import io
import logging

if not os.path.isdir('../logs'):
	os.makedirs('../logs')
with open('../logs/mazeui.log', 'w'):
	pass
log_ui = logging.getLogger(__name__)
log_ui.setLevel(logging.INFO)
handler_f = logging.FileHandler('../logs/mazeui.log')
handler_f.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s:%(message)s'))
log_ui.addHandler(handler_f)

class OutOfBounds(BaseException):
	def __init__(self, msg, x, y):
		self.msg = msg
		self.x = x
		self.y = y

class GameCtrl:
	_players = []
	__TICK = dt.timedelta(seconds=1)/16
	__sec_till_start = 10
	__MSG_START = "Go...Go...Go..."
	__MSG_WILL_START = "Game will start in:"
	__MSG_WAIT_JOIN = "Waiting for players to join..."
	__ERR_EXISTS = "Player with same attributes already exists"
	__TEST_COUNT = 8
	MAX_PLAYERS = 5
	__ERR_FLAG = -9999
	__dependencies = []
	travel_t = 0.05
	moves = {'f':0, 'b':180, 'l':90, 'r':-90, 'ul':45, 'ur':-45, 'dl':225, 'dr':-135, 'l63':63, 'r63':-63}
	P = None
	__sckt_tcp = None
	__start = False
	
	def init(sckt_tcp, clr, fpv, keyboard, assist, mvbuff, file, speech, bci, mapl, mapr, listen):
		GameCtrl.__sckt_tcp = sckt_tcp 
		GameCtrl.__my_clr = clr
		if file:
			GameCtrl.__dependencies.append(file.status)
		if sckt_tcp:
			GameCtrl.__dependencies.append(sckt_tcp.status)
		sock = sckt.socket(sckt.AF_INET, sckt.SOCK_DGRAM)
		sock.connect(('8.8.8.8', 80))
		GameCtrl.__my_ip = sock.getsockname()[0]
		GameCtrl.__key = keyboard
		GameCtrl.__fpv = True if (fpv or speech) else False
		GameCtrl.__assist = assist
		GameCtrl.__mvbuff = mvbuff
		GameCtrl.__speech = speech
		GameCtrl.__bci = bci
		GameCtrl.__listen = listen
		if mapl:
			GameCtrl.moves['l'] = mapl
		if mapr:
			GameCtrl.moves['r'] = mapr
	
	def start():
		try:
			Console.disable_quick_edit()
			GameCtrl.__sckt_tcp.send(Pkt('_x_play_x_', {'ip':GameCtrl.__my_ip, 'clr':GameCtrl.__my_clr}, 
				{'ip':'0.0.0.0', 'clr':None}, None, None, 0, None, None, None))
			GameCtrl.__sckt_tcp.send(Pkt('_x_ready_x_', {'ip':GameCtrl.__my_ip, 'clr':GameCtrl.__my_clr}, 
				{'ip':'0.0.0.0', 'clr':None}, None, None, 0, None, None, None))
			time.sleep(0.05)
			GameCtrl.__sckt_tcp.send(Pkt('_x_keyboard_x_', {'ip':GameCtrl.__my_ip, 'clr':GameCtrl.__my_clr}, 
				{'ip':'0.0.0.0', 'clr':None}, None, GameCtrl.moves, 0, None, None, None))
			GameCtrl.update_pos()
		except KeyboardInterrupt:
			GameCtrl.__sckt_tcp.shutdown()
		Shell.exit()
		Console.enable_quick_edit()
	
	def update_pos():
		last_mv = 0
		Shell.init()
		warning = False
		t_curr = dt_dt.now()
		t_last = dt_dt.now()
		while True:
			if Shell.is_quit() and GameCtrl.__status(*GameCtrl.__dependencies):
				break
			c = GameCtrl.__sckt_tcp.get()
			if c:
				if c.request == '_x_img_x_':	
					Shell.set_bgnd(ImageProcessing.base642img(zlib.decompress(c.data)))
				elif c.request == '_x_new_player_x_':
					GameCtrl.add2players(Player(c.id_trgt['ip'], c.id_trgt['clr'], c.misc.curx, c.misc.cury, c.misc.deg))
				elif c.request == '_x_start_x_':
					GameCtrl.__start = True
				elif c.request == '_x_gameplay_x_' and not GameCtrl.__start:
					GameCtrl.__sckt_tcp.send(Pkt('_x_ready_x_', {'ip':GameCtrl.__my_ip, 'clr':GameCtrl.__my_clr}, 
						{'ip':'0.0.0.0', 'clr':None}, None, None, 0, None, None, None))
				elif c.request == '_x_gameplay_x_' and GameCtrl.__start:
					P = GameCtrl.get_player(c.id_trgt['ip'], c.id_trgt['clr'])
					if P:
						P.crawl(c.misc.curx, c.misc.cury)
				if c.warn:
					warning = True
					log_ui.info(c.warn)
				else:
					warning = False
				Shell.update_ui(GameCtrl._players)
			t_curr = dt_dt.now()
			if t_curr - t_last > GameCtrl.__TICK:
				t_last = dt_dt.now()
				next_mv = None
				if GameCtrl.__speech:
					if not GameCtrl.__listen.is_set() and warning:
						GameCtrl.__listen.set()
					if not GameCtrl.__mvbuff.empty():
						next_mv = GameCtrl.moves[GameCtrl.__mvbuff.get(block=True)]
					elif not warning:
						next_mv = 0
				elif GameCtrl.__bci and not GameCtrl.__mvbuff.empty():
					try:
						key = GameCtrl.__mvbuff.get(block=True)
						next_mv = GameCtrl.moves[key]
					except KeyError:
						log_ui.warning('received an unidentifiable key move: %s'%key)
				elif GameCtrl.__key:
					key = Shell.key_pressed()
					next_mv = GameCtrl.moves[key] if key else None
				if GameCtrl.__assist and not warning and next_mv == None:			
					next_mv = last_mv
				if next_mv != None:
					GameCtrl.__sckt_tcp.send(Pkt('_x_gameplay_x_', {'ip':GameCtrl.__my_ip, 'clr':GameCtrl.__my_clr}, 
						{'ip':'0.0.0.0', 'clr':None}, {'ip':GameCtrl.__my_ip, 'clr':GameCtrl.__my_clr}, (next_mv, GameCtrl.__fpv), 0, None, None, None))
				last_mv = next_mv
				
	def add2players(new_p):
		GameCtrl._players.append(new_p)

	def is_unique_clr(clr):
		for p in GameCtrl._players:
			if p.clr == clr:
				return False
		return True

	def get_player(ip, clr):
		for p in GameCtrl._players:
			if p.ip == ip and p.clr == clr:
				return p
		return None

	def __status(*status_q):
		for q in status_q:
			if not q.empty() and q.get(block=True) == GameCtrl.__ERR_FLAG:
				return False
		return True

class Player:
	def __init__(self, ip, clr, c, r, deg):
		self.ip = ip
		self.clr = clr
		self.loc = (c, r)
		self.deg = deg
	
	def crawl(self, lr, ud):
		self.loc = (lr, ud)
		
class Shell:
	__WIN_MAX_X = 600
	__WIN_MAX_Y = 600
	__BORDER_X = 10
	__BORDER_Y = 10
	__SPRITE_SZ = 1
	__FIG_MAX_W = math.floor(__WIN_MAX_X/__SPRITE_SZ)
	__FIG_MAX_H = math.floor(__WIN_MAX_Y/__SPRITE_SZ)
	__bgnd = None
	__win = None
	__PLY_SIZE = 5

	def init():
		Shell.__win = pygame.display.set_mode((Shell.__WIN_MAX_X, Shell.__WIN_MAX_Y))
		pygame.display.set_caption('Maze game')
		
	def set_bgnd(img):
		Shell.__bgnd = pygame.image.fromstring(img.tobytes(), img.size, img.mode).convert()
	
	def __draw_bgnd():
		Shell.__win.blit(Shell.__bgnd, [0,0])
	
	def __draw_player(p):
		log_ui.info('updating player %s to x=%d y=%d'% (p.ip, p.loc[0], p.loc[1]))
		pygame.draw.circle(Shell.__win, pygame.Color(p.clr), p.loc, Shell.__PLY_SIZE)
	
	def update_ui(players):
		Shell.__draw_bgnd()
		for p in players:
			Shell.__draw_player(p)
		pygame.display.update()
	
	def is_quit():
		for e in pygame.event.get():
			if e.type == pygame.QUIT:
				return True
		return False
	
	def exit():
		pygame.quit()
		
	def key_pressed():
		keys=pygame.key.get_pressed()
		if keys[pygame.K_LEFT]:
			if keys[pygame.K_UP]:
				return 'ul'
			elif keys[pygame.K_DOWN]:
				return 'dl'
			else:
				return 'l'
		elif keys[pygame.K_RIGHT]:
			if keys[pygame.K_UP]:
				return 'ur'
			elif keys[pygame.K_DOWN]:
				return 'dr'
			else:
				return 'r'
		elif keys[pygame.K_UP]:
			return 'f'
		elif keys[pygame.K_DOWN]:
			return 'b'
		return None