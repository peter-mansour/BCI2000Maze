import threading
from maze_ui import GameCtrl
from connect_utils import Pkt
from TCPClient import TCPClient
from file_utils import FParse
import socket as sckt
import sys
import time
import click
from win_cmd import Console
from Keyboard import *
import multiprocessing

MSG_CLOSE = 'Closing app...'
MSG_READY = 'Are you Ready [y/n]: '
MSG_WAIT = 'waiting...\n'
MSG_FPV = 'Forward to continue moving in same direction'
MSG_KEY = 'Use Keyboard to control player movement'
MSG_ASSIST = 'When enabled, player only needs to choose left/right at intersections \
 (forward movement is managed by software)'

@click.command()
@click.option('--assist', is_flag=True, type=bool, help=MSG_ASSIST)
@click.option('--fpv', is_flag=True, type=bool, help=MSG_FPV)
@click.option('--keyboard', is_flag=True, type=bool, help=MSG_KEY)
@click.argument('ipv4_host')
@click.argument('port', default=9001, type=int)
@click.argument('color')
@click.argument('bci2000_app_log_path', default='/', type=click.Path(exists=True))
def main(assist, ipv4_host, port, color, keyboard, fpv, bci2000_app_log_path):
	try:
		Console.disable_quick_edit()
		
		sock = sckt.socket(sckt.AF_INET, sckt.SOCK_DGRAM)
		sock.connect(('8.8.8.8', 80))
		p_ip = sock.getsockname()[0]
		
		tcp_c = TCPClient(ipv4_host, port)
		
		if tcp_c.join():
			
			Console.disable_quick_edit()
			if input(MSG_READY).lower() == 'y':
				if not keyboard:
					file = FParse(p_ip, color, tcp_c)
					file.read(bci2000_app_log_path)
				else:
					inbuff = multiprocessing.Queue()
					p = multiprocessing.Process(target=Keyboard.get_arrowhits, args=(inbuff,), daemon=True)
					p.start()
				GameCtrl.init(tcp_c, color, fpv, keyboard, assist, inbuff)
				GameCtrl.start()	
	except KeyboardInterrupt:
		pass
	print(MSG_CLOSE, flush=True)

if __name__ == "__main__":
	main()
	