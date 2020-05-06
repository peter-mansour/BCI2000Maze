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
import multiprocessing
import queue
#from speech2txt import *

MSG_CLOSE = 'Closing app...'
MSG_READY = 'Are you Ready [y/n]: '
MSG_WAIT = 'waiting...\n'
MSG_FPV = 'Forward to continue moving in same direction'
MSG_ASSIST = 'When enabled, player only needs to choose left/right at intersections \
 (forward movement is managed by software)'

@click.command()
@click.option('--assist', is_flag=True, type=bool, help=MSG_ASSIST)
@click.option('--fpv', is_flag=True, type=bool, help=MSG_FPV)
@click.option('--speech', is_flag=True, type=bool)
@click.option('--bci2000', envvar='PATHS', type=click.Path(exists=True))
@click.option('--mapl', type=int)
@click.option('--mapr', type=int)
@click.argument('ipv4_host')
@click.argument('port', default=9001, type=int)
@click.argument('color')
def main(assist, ipv4_host, port, color, fpv, bci2000, speech, mapl, mapr):
	try:
		Console.disable_quick_edit()
		file = None
		keyboard = False
		bci = False
		sock = sckt.socket(sckt.AF_INET, sckt.SOCK_DGRAM)
		sock.connect(('8.8.8.8', 80))
		p_ip = sock.getsockname()[0]
		tcp_c = TCPClient(ipv4_host, port)
		if tcp_c.join() and input(MSG_READY).lower() == 'y':
			if bci2000:
				inbuff = queue.Queue()
				file = FParse(inbuff)
				file.read(bci2000)
				bci = True
			elif speech:
				#inbuff = multiprocessing.Queue()
				#p = multiprocessing.Process(target=speech2txt, args=(inbuff,), daemon=True)
				#p.start()
				pass
			else:
				keyboard = True
				inbuff = None
			GameCtrl.init(tcp_c, color, fpv, keyboard, assist, inbuff, file, speech, bci, mapl, mapr)
			GameCtrl.start()	
	except KeyboardInterrupt:
		pass
	if speech:
		p.join()
	print(MSG_CLOSE, flush=True)
	Console.enable_quick_edit()

if __name__ == "__main__":
	main()
	