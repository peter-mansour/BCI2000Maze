from TCPServer import TCPServer
import sys
import click
import signal
from ImageProcessing import *
from GameLogic import *

MSG_MAZE_IMG_PATH = 'path to image to be used as maze template'
MSG_LUMA_THRES = 'Maze image is inverted. Walls have higher luma (whiter). 0=black 1=white'

@click.command()
@click.option('--inverted_color', is_flag=True, type=bool, help=MSG_LUMA_THRES)
@click.option('--maze', default='../templates/lvl1.jpg', help=MSG_MAZE_IMG_PATH)
@click.argument('ipv4_host')
@click.argument('port', default=9001, type=int)
@click.argument('player_count', default=3, type=int)
def main(ipv4_host, port, player_count, inverted_color, maze):
	try:
		signal.signal(signal.SIGINT, signal.SIG_DFL)
		GameLogic.init(maze, inverted_color)
		TCPServer.init(ipv4_host, port, player_count)
		TCPServer.run_host()
		TCPServer._wait()
		while True:
			pass
	except KeyboardInterrupt:
		print("Closing Server...", flush=True)

if __name__ == "__main__":
	main()