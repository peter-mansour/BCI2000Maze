import turtle
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

class OutOfBounds(BaseException):
	def __init__(self, msg, x, y):
		self.msg = msg
		self.x = x
		self.y = y

class GameCtrl:
	_players = []
	__ONE_SEC = dt.timedelta(seconds=1)
	__sec_till_start = 10
	__MSG_START = "Go...Go...Go..."
	__MSG_WILL_START = "Game will start in:"
	__MSG_WAIT_JOIN = "Waiting for players to join..."
	__ERR_EXISTS = "Player with same attributes already exists"
	__TEST_COUNT = 8
	MAX_PLAYERS = 5
	__ERR_FLAG = -9999
	travel_t = 0.05
	moves = {'f':0, 'b':180, 'l':90, 'r':-90, 'l63':63, 'r63':-63}
	P = None
	__sckt_tcp = None
	__start = False
	
	def init(sckt_tcp, clr, fpv, keyboard, assist, mvbuff):
		GameCtrl.__sckt_tcp = sckt_tcp 
		GameCtrl.__my_clr = clr
		sock = sckt.socket(sckt.AF_INET, sckt.SOCK_DGRAM)
		sock.connect(('8.8.8.8', 80))
		GameCtrl.__my_ip = sock.getsockname()[0]
		GameCtrl.__key = keyboard
		GameCtrl.__fpv = fpv
		GameCtrl.__assist = assist
		GameCtrl.__mvbuff = mvbuff
	
	def start():
		try:
			Console.disable_quick_edit()
			GameCtrl.__sckt_tcp.send(Pkt('_x_play_x_', {'ip':GameCtrl.__my_ip, 'clr':GameCtrl.__my_clr}, 
				{'ip':'0.0.0.0', 'clr':None}, None, None, 0, None, None, None))
			GameCtrl.__sckt_tcp.send(Pkt('_x_ready_x_', {'ip':GameCtrl.__my_ip, 'clr':GameCtrl.__my_clr}, 
				{'ip':'0.0.0.0', 'clr':None}, None, None, 0, None, None, None))
			GameCtrl.update_pos()
		except KeyboardInterrupt:
			print('', flush=True)
			GameCtrl.__sckt_tcp.shutdown()
		Shell.exit()
		Console.enable_quick_edit()
	
	def update_pos():
		#GameCtrl.__file.status
		last_mv = 0
		Shell.init()
		start = True
		while start:
			if c := GameCtrl.__sckt_tcp.get():
				if c.request == '_x_maze_outline_x_':	
					Shell.set_maze(ImageProcessing.base642img(zlib.decompress(c.data)))
				elif c.request == '_x_new_player_x_':
					GameCtrl.add2players(Player(c.id_trgt['ip'], c.id_trgt['clr'], c.misc.curx, c.misc.cury, c.misc.deg))
				elif c.request == '_x_start_x_':
					GameCtrl.__start = True
				elif c.request == '_x_gameplay_x_' and GameCtrl.__start:
					if P := GameCtrl.get_player(c.id_trgt['ip'], c.id_trgt['clr']):
						P.crawl(c.misc.curx, c.misc.cury)
				if c.warn:
					print(c.warn, flush=True)
				Shell.update_ui(GameCtrl._players)
			if not GameCtrl.__mvbuff.empty():
				mv = GameCtrl.moves[GameCtrl.__mvbuff.get(block=True)]
				next_mv = 0 if GameCtrl.__fpv and last_mv == mv else mv
			elif GameCtrl.__assist:	
				next_mv = 0 if GameCtrl.__fpv else last_mv
			else:
				next_mv = None
			if next_mv != None:
				GameCtrl.__sckt_tcp.send(Pkt('_x_gameplay_x_', {'ip':GameCtrl.__my_ip, 'clr':GameCtrl.__my_clr}, 
					{'ip':'0.0.0.0', 'clr':None}, {'ip':GameCtrl.__my_ip, 'clr':GameCtrl.__my_clr}, next_mv, 0, None, None, None))
			if Shell.is_quit() and GameCtrl.__status(GameCtrl.__sckt_tcp.status):
				start = False

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
	__maze = None
	__win = None
	__PLY_SIZE = 5

	def init():
		Shell.__win = pygame.display.set_mode((Shell.__WIN_MAX_X, Shell.__WIN_MAX_Y))
		pygame.display.set_caption('Maze game')
		
	def set_maze(maze):
		Shell.__maze = pygame.image.fromstring(maze.tobytes(), maze.size, maze.mode).convert()
	
	def __draw_maze():
		Shell.__win.blit(Shell.__maze, [0,0])
	
	def __draw_player(p):
		pygame.draw.circle(Shell.__win, pygame.Color(p.clr), p.loc, Shell.__PLY_SIZE)
	
	def update_ui(players):
		Shell.__draw_maze()
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
	