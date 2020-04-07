import threading
from maze_ui import Maze, Player, GameCtrl, Shell
from connect_utils import TCPClient, Pkt
from file_utils import FParse
import socket as sckt
import sys
import time
import click
from win_cmd import Console

MSG_CLOSE = 'Closing app...'
MSG_READY = 'Are you Ready [y/n]: '
MSG_WAIT = 'waiting...\n'
MSG_RGB_THRES_MIN = 'lowest rgb ratio for detecting walls. 0=black 1=white'
MSG_RGB_THRES_MAX = 'highest rgb ratio for detecting walls. 0=black 1=white'
MSG_MAZE_IMG_PATH = 'path to image to be used as maze template'
MSG_ASSIST = 'When enabled, player only needs to choose left/right at intersections \
 (forward movement is managed by software)'

@click.command()
@click.option('--rgb_thres_min', default=0, type=float, help=MSG_RGB_THRES_MIN)
@click.option('--rgb_thres_max', default=0.4, type=float, help=MSG_RGB_THRES_MAX)
@click.option('--maze', default='../templates/lvl1.jpg', help=MSG_MAZE_IMG_PATH)
@click.option('--assist', is_flag=True, type=bool, help=MSG_ASSIST)
@click.argument('ipv4_host')
@click.argument('port', default=9001, type=int)
@click.argument('color')
@click.argument('bci2000_app_log_path', type=click.Path(exists=True))
def main(rgb_thres_min, rgb_thres_max, maze, assist, ipv4_host, port, color, bci2000_app_log_path):
	try:
		Console.disable_quick_edit()
		
		sock = sckt.socket(sckt.AF_INET, sckt.SOCK_DGRAM)
		sock.connect(('8.8.8.8', 80))
		p_ip = sock.getsockname()[0]
		
		tcp_c = TCPClient(ipv4_host, port)
		if tcp_c.join():
			
			Shell.init()
			Shell.set_rgb_thres(rgb_thres_min, rgb_thres_max)
			Shell.load(maze)
			ui = Maze()
			ui.draw_maze()
			
			request = 0
			
			Console.disable_quick_edit()
			ready = input(MSG_READY)
			while ready.lower() != 'y' and request < 5:
				request += 1
				sys.stdout.write(MSG_WAIT)
				sys.stdout.flush()
				time.sleep(5)
				ready = input(MSG_READY)
			if ready.lower() == 'y':
				file = FParse(p_ip, color, tcp_c)
				file.read(bci2000_app_log_path)
				gc = GameCtrl(tcp_c, file, color)
				gc.start(assist)	
	except KeyboardInterrupt:
		pass
	print(MSG_CLOSE, flush=True)

if __name__ == "__main__":
	main()
	