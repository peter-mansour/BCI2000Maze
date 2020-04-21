import math
from ImageProcessing import *

class OutOfBounds(BaseException):
	def __init__(self, msg, x, y):
		self.msg = msg
		self.x = x
		self.y = y

class pos:
	def __init__(self, curx=0, cury=0, prevx=0, prevy=0, deg=90, dist=None):
		self.curx = curx
		self.cury = cury
		self.prevx = prevx
		self.prevy = prevy
		self.deg = deg
		self.dist = dist
		
class GameLogic:
	_maze_template = None
	__walls = None
	__STEP_SZ = 4
	_start_pos = [150, 220]
	__ERR_WALL = "About to hit a wall"
	__ERR_MAP = "Attempting to add element outside window"
	_maze_img_obj = None
	
	@staticmethod
	def init(maze, inverted_color):
		GameLogic._maze_template, GameLogic._maze_img_obj = ImageProcessing.load(maze)
		ImageProcessing.set_luma_thres(GameLogic._maze_img_obj, inverted_color)
		GameLogic.__walls = ImageProcessing.binarize(GameLogic._maze_template)
	
	@staticmethod
	def deg2xy(deg):
		lr = GameLogic.__STEP_SZ*math.cos(math.radians(deg))
		ud = -1*GameLogic.__STEP_SZ*math.sin(math.radians(deg))
		return lr, ud
	
	@staticmethod
	def near_wall(pre, post):
		try:
			for r in range(min(pre[0], post[0])-1, max(pre[0], post[0])+1):
				for c in range(min(pre[1], post[1])-1, max(pre[1], post[1])+1):
					if GameLogic.__walls[r, c]:
						return True
			return False
		except IndexError:
			raise OutOfBounds(GameLogic.__ERR_MAP, c, r)
	
	@staticmethod
	def update_pos(pos, deg):
		new_deg = (deg+pos.deg)%360
		lr, ud = GameLogic.deg2xy(new_deg)
		dir = None
		if not GameLogic.near_wall((pos.cury, pos.curx), (pos.cury+round(ud), pos.curx+round(lr))):
			pos.new_deg = new_deg
			pos.prevx = pos.curx
			pos.prevy = pos.cury
			pos.cury += round(ud)
			pos.curx += round(lr)
			if ud > 0:
				dir = 'f'
			elif ud < 0:
				dir = 'b'
			if lr > 0:
				dir = 'r'
			elif lr < 0:
				dir = 'l'
		else:
			raise OutOfBounds(GameLogic.__ERR_WALL, pos.curx+round(lr), pos.cury+round(ud))
		return pos, dir
	
	@staticmethod
	def __map_loc(x, y):
		return (math.floor(Shell.__SPRITE_SZ * x + Shell.__PX_LOW_LIMIT), 
			math.floor(-1*Shell.__SPRITE_SZ * y + Shell.__PX_HIGH_LIMIT))