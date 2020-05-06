from TCPServer import TCPServer
import sys
import click
import signal
from ImageProcessing import *
from GameLogic import *
import multiprocessing
from talk2ino import *
from win_cmd import Console

MSG_MAZE_IMG_PATH = 'path to image to be used as maze template'
MSG_LUMA_THRES = 'Maze image is inverted. Walls have higher luma (whiter). 0=black 1=white'

@click.command()
@click.option('--inverted_color', is_flag=True, type=bool, help=MSG_LUMA_THRES)
@click.option('--maze', default='../templates/lvl1.jpg', help=MSG_MAZE_IMG_PATH)
@click.option('--ino', type=click.Tuple([str, int]), multiple=True)
@click.option('--start', default=[None]*2, type=click.Tuple([int, int]))
@click.option('--end', default=[None]*2, type=click.Tuple([int, int]))
@click.argument('ipv4_host')
@click.argument('port', default=9001, type=int)
@click.argument('player_count', default=1, type=int)
def main(ipv4_host, port, player_count, inverted_color, maze, ino, start, end):
	try:
		children = []
		inos = []
		signal.signal(signal.SIGINT, signal.SIG_DFL)
		Console.disable_quick_edit()
		for i in ino:
			inbuff = multiprocessing.Queue()
			outbuff = multiprocessing.Queue()
			p = multiprocessing.Process(target=talk2ino, args=(i, inbuff, outbuff), daemon=True)
			p.start()
			children.append(p)
			inos.append((inbuff, outbuff, True))
		GameLogic.init(maze, inverted_color, start, end)
		TCPServer.init(ipv4_host, port, player_count, inos)
		TCPServer.run_host()
		TCPServer._wait()
		while not TCPServer._shutdown:
			pass
	except KeyboardInterrupt:
		print("Closing Server...", flush=True)
	for p in children:
		p.join()
if __name__ == "__main__":
	main()