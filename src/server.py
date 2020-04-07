from connect_utils import TCPServer
import sys
import click

@click.command()
@click.argument('ipv4_host')
@click.argument('port', default=9001, type=int)
def main(ipv4_host, port):
	try:
		server = TCPServer(ipv4_host, port)
		server.setup_host()
		while True:
			pass
	except KeyboardInterrupt:
		print("Closing Server...", flush=True)

if __name__ == "__main__":
	main()