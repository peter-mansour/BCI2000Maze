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

class OutOfBounds(BaseException):
	def __init__(self, msg, x, y):
		self.msg = msg
		self.x = x
		self.y = y

class GameCtrl:
	__players = []
	start_pos = [160, 310]
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
	
	def __init__(self, sckt_tcp, file, clr):
		self.__sckt_tcp = sckt_tcp
		self.__file = file 
		self.__my_clr = clr
		sock = sckt.socket(sckt.AF_INET, sckt.SOCK_DGRAM)
		sock.connect(('8.8.8.8', 80))
		self.__my_ip = sock.getsockname()[0]
	
	def start(self, assist):
		try:
			Console.disable_quick_edit()
			self.__sckt_tcp.send(Pkt('_x_play_x_', self.__my_ip, self.__my_clr))
			self.discover_players()
			self.wait()
			self.count_down()
			self.update_ui(assist)
		except KeyboardInterrupt:
			print('', flush=True)
			self.__sckt_tcp.shutdown()
			self.__file.shutdown()
		Shell.close()
		Console.enable_quick_edit()
		
	def discover_players(self):
		try:
			bar = Bar('locating players', self.__TEST_COUNT)
			for i in range(self.__TEST_COUNT):
				self.__status(self.__sckt_tcp.status, self.__file.status)
				time.sleep(3)
				self.__sckt_tcp.send(Pkt('_x_join_x_', self.__my_ip, self.__my_clr))
				pkt = self.__sckt_tcp.get()
				if pkt and pkt.val == '_x_join_x_' and not self.get_player(pkt.ip, pkt.clr):
					if self.is_unique_clr(pkt.clr) and len(self.__players) < self.MAX_PLAYERS:
						self.add2players(self.__create_player(pkt.ip, pkt.clr))
					elif not self.is_unique_clr(pkt.clr) and pkt.ip == self.__my_ip:
						print('', flush=True)
						sys.stderr.write(self.__ERR_EXISTS)
						sys.stderr.flush()
						raise KeyboardInterrupt
				bar.update()
		except KeyboardInterrupt as e:
			bar.shutdown()
			raise e
	
	def wait(self):
		ips = []
		joined = 0
		Console.disable_quick_edit()
		print(self.__MSG_WAIT_JOIN, flush=True)
		while joined < len(self.__players):
			self.__sckt_tcp.send(Pkt('_x_ready_x_', self.__my_ip, ''))
			time.sleep(3)
			pkt = self.__sckt_tcp.get()
			if pkt and pkt.val == '_x_ready_x_':
				try:
					index = ips.index(pkt.ip)
				except ValueError:
					index = -1
				if index == -1:
					ips.append(pkt.ip)
					joined += 1
		self.__sckt_tcp.flush()
		
	def count_down(self):
		Console.disable_quick_edit()
		t_curr = dt_dt.now()
		t_last_count = dt_dt.now()
		print(self.__MSG_WILL_START, flush=True)
		while self.__sec_till_start >= 0 and \
			not self.__status(self.__sckt_tcp.status, self.__file.status):
			while t_curr - t_last_count < self.__ONE_SEC and \
				not self.__status(self.__sckt_tcp.status, self.__file.status):
				t_curr = dt_dt.now()
			if self.__sec_till_start == 0:
				print(self.__MSG_START, flush=True)
			else:
				print(self.__sec_till_start, flush=True)
			t_last_count = dt_dt.now()
			self.__sec_till_start -= 1
	
	def update_ui(self, assist):
		t_last_assist = dt_dt.now()
		while not self.__status(self.__sckt_tcp.status, self.__file.status):
			t_curr = dt_dt.now()
			i = 0
			P = None
			c = self.__sckt_tcp.get()
			if c:
				P = self.get_player(c.ip, c.clr)
				if P != None:
					if P.get_ip() == self.__my_ip:
							t_last_assist = dt_dt.now()
					try:
						if c.val == '_x_B_x_':
							P.crawl(self.moves['b'], self.travel_t)
						elif c.val == '_x_L_x_':
							P.crawl(self.moves['l63'], self.travel_t)
						elif c.val == '_x_R_x_':
							P.crawl(self.moves['r63'], self.travel_t)
						elif c.val == '_x_F_x_': 
							P.crawl(self.moves['f'], self.travel_t)	
					except OutOfBounds as e:
						print("%s (%d, %d)" % (e.msg, e.x, e.y), flush=True)
			if assist and (t_curr - t_last_assist > 2*self.__ONE_SEC):
				me = self.get_player(self.__my_ip, self.__my_clr)
				if me and not me.near_wall(math.cos(math.radians(me.get_dir())), -1*math.sin(math.radians(me.get_dir()))):
					self.__sckt_tcp.send(Pkt('_x_F_x_', self.__my_ip, self.__my_clr))
					t_last_assist = dt_dt.now()

	def add2players(self, new_p):
		self.__players.append(new_p)

	def is_unique_clr(self, clr):
		for p in self.__players:
			if p.get_clr() == clr:
				return False
		return True

	def get_player(self, ip, clr):
		for p in self.__players:
			if p.get_ip() == ip and p.get_clr() == clr:
				return p
		return None

	def __create_player(self, ip, clr):
		return Player(self.start_pos[0], self.start_pos[1], clr, ip)

	def __status(self, *status_q):
		for q in status_q:
			if not q.empty() and q.get(block=True) == self.__ERR_FLAG:
				raise KeyboardInterrupt

class Shell:
	__WIN_MAX_X         = 650
	__WIN_MAX_Y         = 650
	__BORDER_X          = 10
	__BORDER_Y          = 10
	__PX_LOW_LIMIT      = -1*(__WIN_MAX_X-__BORDER_X)/2
	__PX_HIGH_LIMIT     = (__WIN_MAX_X-__BORDER_X)/2
	__SPRITE_SZ         = 2
	__FIG_MAX_W         = math.floor((__WIN_MAX_X-__BORDER_X)/__SPRITE_SZ)
	__FIG_MAX_H         = math.floor((__WIN_MAX_Y-__BORDER_Y)/__SPRITE_SZ)
	DEFAULT_TEMP      = 0
	DEFAULT_TEMP_DIR  = "../templates/"
	IMG_EXTS          = ['.png', '.jpg', '.gif']
	STEP_SZ           = 4
	__MSG_EXIT          = "Closing UI..."
	__ERR_MAP           = "Attempting to add element outside window"
	__RGB_THRESHOLD_MAX = 0
	__RGB_THRESHOLD_MIN = 0
	maze_template     = None
	walls             = None
	win               = None
	cur               = None
	
	@staticmethod
	def init():
		Shell.cur = turtle
		Shell.cur.colormode(255)
		Shell.cur.delay(0)
		Shell.__set_win()
	
	def __set_win(): 
		Shell.win = turtle.Screen()
		Shell.win.bgcolor("white")
		Shell.win.setup(Shell.__WIN_MAX_X, Shell.__WIN_MAX_Y)
		Shell.win.tracer(0,0)
	
	def __map_loc(x, y):
		return (math.floor(Shell.__SPRITE_SZ * x + Shell.__PX_LOW_LIMIT), 
			math.floor(-1*Shell.__SPRITE_SZ * y + Shell.__PX_HIGH_LIMIT))
	
	def __binarize(img, rgb_thr_l, rgb_thr_h):
		new_img = np.zeros([img.shape[0], img.shape[1]])
		for r in range(img.shape[0]):
			for c in range(img.shape[1]):
				if rgb_thr_h > np.average(img[r,c,:])/255 and \
					np.average(img[r,c,:])/255 > rgb_thr_l:
					new_img[r,c] = 1
		return new_img	

	@staticmethod
	def print_at(x, y, update=1):
		x, y = Shell.__map_loc(x, y)
		if x < Shell.__PX_LOW_LIMIT or y < Shell.__PX_LOW_LIMIT \
			or x > Shell.__PX_HIGH_LIMIT or y > Shell.__PX_HIGH_LIMIT:
			raise OutOfBounds(Shell.__ERR_MAP, x, y)
		Shell.cur.setpos(x, y)
		stmp_id = Shell.cur.stamp()
		if update:
			Shell.win.update()
		return stmp_id	
	
	@staticmethod
	def set_rgb_thres(rgb_thr_l, rgb_thr_h):
		Shell.__RGB_THRESHOLD_MIN = rgb_thr_l
		Shell.__RGB_THRESHOLD_MAX = rgb_thr_h
	
	@staticmethod
	def rm_stmp(stmp_id):
		Shell.cur.clearstamp(stmp_id)
		Shell.win.update()
	
	@staticmethod
	def close():
		print(Shell.__MSG_EXIT, flush=True)
		Shell.win.bye()

	@staticmethod
	def set_cursor(shp, clr, sz):
		Shell.cur.shape(shp)
		Shell.cur.color(clr)
		Shell.cur.shapesize(sz, sz, None)
		Shell.cur.penup()
		Shell.cur.speed(0)
	
	@staticmethod
	def get_imgs(dir=DEFAULT_TEMP_DIR, ext=IMG_EXTS):
		files = []
		for f in os.listdir(dir):
			for e in ext:
				if f.endswith(e):
					files.append(os.path.join(dir, f))
		return files
	
	@staticmethod
	def load(path):
		img = Image.open(path)
		img = img.resize((Shell.__FIG_MAX_W, Shell.__FIG_MAX_H))
		Shell.maze_template = np.array(img)
		Shell.walls = Shell.__binarize(Shell.maze_template, Shell.__RGB_THRESHOLD_MIN, Shell.__RGB_THRESHOLD_MAX)
	
class Maze():
	__MSG_WAIT = "Generating background..."
	def __init__(self):
		self.__stmp_id = 0
		self.__admin = 1

	def draw_maze(self):
		try:
			Shell.win.tracer(0,0)
			bar = Bar('loading maze', Shell.maze_template.shape[0])
			for pos_y in range(Shell.maze_template.shape[0]):
				for pos_x in range(Shell.maze_template.shape[1]):
					R = Shell.maze_template[pos_x, pos_y, 0]
					G = Shell.maze_template[pos_x, pos_y, 1]
					B = Shell.maze_template[pos_x, pos_y, 2]
					Shell.set_cursor("square", (R, G, B), 0.1)
					self.__stmp_id = Shell.print_at(pos_y, pos_x, update=0)
				bar.update()
			print(self.__MSG_WAIT, flush=True)
			Shell.win.update()
		except KeyboardInterrupt as e:
			bar.shutdown()
			raise e

class Player():
	__DOT_SZ  = 0.3
	__rotate = 90
	__idle = 1
	__ERR_WALL          = "About to hit a wall"
	
	def __init__(self, start_x, start_y, clr, ip):
		self.__clr = clr
		self.__ip  = ip
		self.__admin = 0
		self.__r = start_y
		self.__c = start_x
		Shell.set_cursor("circle", self.__clr, self.__DOT_SZ)
		self.__stmp_id = Shell.print_at(start_x, start_y)

	def __mv_cur(self, lr, ud):
		try:
			if not self.__admin and self.near_wall(lr, ud):
				raise OutOfBounds(self.__ERR_WALL, self.__c+lr, self.__r+ud)
			Shell.rm_stmp(self.__stmp_id)
			self.__r+=ud
			self.__c+=lr
			self.__stmp_id = Shell.print_at(self.__c, self.__r)
		except IndexError:
			raise OutOfBounds(self.__ERR_MAP, self.__r+ud, self.__c+lr)	
					
	def near_wall(self, lr, ud):
		err_fact = 0.6
		if Shell.walls[math.floor(round(self.__r+err_fact+ud)), math.floor(round(self.__c+lr))] or \
		   Shell.walls[math.floor(round(self.__r-err_fact+ud)), math.floor(round(self.__c+lr))] or \
		   Shell.walls[math.floor(round(self.__r+ud)), math.floor(round(self.__c-err_fact+lr))] or \
		   Shell.walls[math.floor(round(self.__r+ud)), math.floor(round(self.__c+err_fact+lr))]:
			return True
		return False
		
	def crawl(self, deg, t):
		self.__rotate = (self.__rotate+deg)%360
		lr = Shell.STEP_SZ*math.cos(math.radians(self.__rotate))
		ud = -1*Shell.STEP_SZ*math.sin(math.radians(self.__rotate))
		baby_step_x = lr/Shell.STEP_SZ
		baby_step_y = ud/Shell.STEP_SZ
		Shell.set_cursor("circle", self.__clr, self.__DOT_SZ)
		t_inc = t/(abs(lr)+abs(ud))
		try:
			while round(ud, 10) != 0 or round(lr, 10) != 0:
				x = 0
				y = 0
				if round(lr, 10) != 0:
					x = baby_step_x
					lr -= baby_step_x
				if round(ud, 10) != 0:
					y = baby_step_y
					ud -= baby_step_y

				self.__mv_cur(x, y)
				time.sleep(t_inc)
		except OutOfBounds as e:
			raise e
	
	def get_ip(self):
		return self.__ip
	
	def get_clr(self):
		return self.__clr
	
	def get_dir(self):
		return self.__rotate