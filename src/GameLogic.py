import math
from ImageProcessing import *
import numpy as np

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
    _lose_img = None
    _win_img = None
    _WIN_IMG_PATH = '../templates/win.png'
    _LOSE_IMG_PATH = '../templates/lose.jpg'
    __STEP_SZ = 4
    __SPRITE_SZ = 1
    __ERR_FACT = 50
    _start_pos = (100, 580)
    _end_pos = (510, 6)
    __ERR_WALL = "About to hit a wall"
    __ERR_MAP = "Attempting to add element outside window"
    _maze_img_obj = None
    default_moves = {0:'f', 180:'b', 90:'l', -90:'r', 45:'ul', -45:'ur', 225:'dl', -135:'dr', 63:'l63', -63:'r63'}
    moves = {'0.0.0.0':default_moves}
    __WIN_MAX_X  = 600
    __WIN_MAX_Y  = 600
    __FIG_MAX_W  = math.floor(__WIN_MAX_X/__SPRITE_SZ)
    __FIG_MAX_H  = math.floor(__WIN_MAX_Y/__SPRITE_SZ)
    __CAUTIOUS = 1
    __RISKY = 1
    
    @staticmethod
    def init(maze, inverted_color, start, end):
        GameLogic._maze_template, GameLogic._maze_img_obj = \
            ImageProcessing.load(maze, GameLogic.__FIG_MAX_W, GameLogic.__FIG_MAX_H)
        GameLogic._win_tmp, GameLogic._win_img = \
            ImageProcessing.load(GameLogic._WIN_IMG_PATH, GameLogic.__FIG_MAX_W, GameLogic.__FIG_MAX_H)
        GameLogic._lose_tmp, GameLogic._lose_img = \
            ImageProcessing.load(GameLogic._LOSE_IMG_PATH, GameLogic.__FIG_MAX_W, GameLogic.__FIG_MAX_H)
        ImageProcessing.set_luma_thres(GameLogic._maze_img_obj, inverted_color)
        GameLogic.__walls = ImageProcessing.binarize(GameLogic._maze_template)
        if start[0]:
            GameLogic._start_pos = start
        if end[0]:
            GameLogic._end_pos = end
    
    @staticmethod
    def deg2xy(deg):
        lr = GameLogic.__STEP_SZ*math.cos(math.radians(deg))
        ud = -1*GameLogic.__STEP_SZ*math.sin(math.radians(deg))
        return lr, ud
    
    @staticmethod
    def near_wall(pre, post, err_fact):
        try:
            if post[0] < 0 or post[1] < 0:
                return OutOfBounds(GameLogic.__ERR_MAP, post[1], post[0])
            for r in range(min(pre[0], post[0])-err_fact, max(pre[0], post[0])+err_fact):
                for c in range(min(pre[1], post[1])-err_fact, max(pre[1], post[1])+err_fact):
                    if GameLogic.__walls[r, c]:
                        return True
            return False
        except IndexError:
            raise OutOfBounds(GameLogic.__ERR_MAP, c, r)
    
    @staticmethod
    def update_pos(id, pos, move):
        win = False
        new_deg = (move[0]+pos.deg)%360 if move[1] else 90+move[0]
        lr, ud = GameLogic.deg2xy(new_deg)
        dir = None
        err_fact = GameLogic.__CAUTIOUS if not move[0] else GameLogic.__RISKY
        if not GameLogic.near_wall((pos.cury, pos.curx), (pos.cury+round(ud), pos.curx+round(lr)), err_fact):
            pos.deg = new_deg
            pos.prevx = pos.curx
            pos.prevy = pos.cury
            pos.cury += round(ud)
            pos.curx += round(lr)
            if pos.cury <= GameLogic._end_pos[1] and pos.curx >= GameLogic._end_pos[0]-GameLogic.__ERR_FACT \
                and  pos.curx <= GameLogic._end_pos[0]+GameLogic.__ERR_FACT:
                win = True
        else:
            raise OutOfBounds(GameLogic.__ERR_WALL, pos.curx+round(lr), pos.cury+round(ud))
        return pos, GameLogic.moves[id][move[0]], win
    
    @staticmethod
    def _bind_keys(id, keyboard):
        key_map = {val:key for key, val in keyboard.items()}
        GameLogic.moves[id] = key_map