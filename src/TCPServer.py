
import socket
import threading
import queue
import pickle
from connect_utils import *
from GameLogic import *
import os
import zlib
import json
from json import JSONEncoder

class TCPServer:
	BUFFER_SZ = 5000
	__MSG_JOIN = "%s joined the network"
	__MSG_REQ = "%s requested to be a %s"
	__MSG_WELCOME = "Server is Up and Running..."
	__HOW2CLOSE = "Ctrl + C to close Server"
	__MSG_FORWARD = "forwarding pkt to %s (%s)"
	__MSG_LEFT = "%s left the network"
	__MSG_REJECT_JOIN = "Rejected %s request to join (already on network)"
	__clients = []
	__players = []
	__listeners = []
	__ready_pkgs = queue.Queue()
	__trig_ready = threading.Event()
	__trig_process = threading.Event()
	__pkt_buffer = queue.Queue()
	__player_count = 0
	__game_on = False
	__threads = {0: None}
	__destroy_threads = queue.Queue()
	__cleanup = threading.Event()
	__manager_t = None
	
	@staticmethod
	def init(IP, PORT, count, inos):
		TCPServer.__IP = IP
		TCPServer.__PORT = PORT
		TCPServer.__player_count = count
		TCPServer.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		TCPServer.__inos = inos
		TCPServer.__run_host_t = threading.Thread(target=TCPServer.__run_host, args=(), daemon=True)
		TCPServer.__manager_t = threading.Thread(target=TCPServer.__manage_threads, args=(), daemon=True)
		TCPServer.__process_pkt_t = threading.Thread(target=TCPServer.__process_pkt, args=(), daemon=True)
		TCPServer.__threads.update({os.urandom(16):TCPServer.__run_host_t, os.urandom(16):TCPServer.__manager_t, 
			os.urandom(16):TCPServer.__process_pkt_t})
	
	@staticmethod
	def run_host():
		TCPServer.__sock.bind((TCPServer.__IP, TCPServer.__PORT))
		TCPServer.__run_host_t.start()
	
	@staticmethod
	def __run_host():
		print(TCPServer.__MSG_WELCOME, flush=True)
		print(TCPServer.__HOW2CLOSE)
		TCPServer.__manager_t.start()
		TCPServer.__process_pkt_t.start()
		TCPServer.__sock.listen(1)
		try:
			while True:
				sock, (ip, ext) = TCPServer.__sock.accept()
				client = ClientInfo(sock, ip, ext)
				if not TCPServer.on_network(client):
					TCPServer.__clients.append(client)
					print(TCPServer.__MSG_JOIN % client.ip, flush=True)
					thid = os.urandom(16)
					client_th = threading.Thread(target=TCPServer.__talk2client, args=(client, thid), daemon=True)
					client_th.start()
					TCPServer.__threads.update({thid:client_th})
				else:
					print(TCPServer.__MSG_REJECT_JOIN % client.ip)
		except KeyboardInterrupt as e:
			TCPServer.__manager_t.join()
			raise e
	
	@staticmethod
	def __json2dict(str):
		try:
			return json.loads(str)
		except ValueError:
			return None
	
	@staticmethod
	def __ascii2str(asci):
		try:
			return asci.decode('ascii')
		except UnicodeDecodeError:
			return None
	
	@staticmethod
	def __talk2client(client, thid):
		try:
			while True:
				if pkt := client.sock.recv(TCPServer.BUFFER_SZ):
					if pkt_str:= TCPServer.__ascii2str(pkt):
						pkt_content = TCPServer.__json2dict(pkt_str)
						TCPServer.__pkt_buffer.put((pkt_content, 'json', client), block=True)
					else:
						TCPServer.__pkt_buffer.put((pickle.loads(pkt), 'pickle', client), block=True)
					TCPServer.__trig_process.set()
				else:
					TCPServer.remove(client)
					break
			client.sock.close()
		except (ConnectionResetError, EOFError):
			TCPServer.remove(client)
		TCPServer.__destroy_threads.put(thid, block=True)
		TCPServer.__cleanup.set()
	
	@staticmethod
	def __manage_threads():
		while TCPServer.__cleanup.wait():
			thid = TCPServer.__destroy_threads.get(block=True)
			TCPServer.__threads[thid].join()
			if TCPServer.__destroy_threads.empty():
				TCPServer.__cleanup.clear()
	
	@staticmethod
	def __process_pkt():
		while TCPServer.__trig_process.wait() and not TCPServer.__pkt_buffer.empty():
			pkt_info = TCPServer.__pkt_buffer.get(block=True)
			if pkt_info[1] == 'json' and pkt_info[0]['request'] == '_x_watch_x_':
				pkt_info[2].role = 'Listener'
				TCPServer.__listeners.append(pkt_info[2])
				print(TCPServer.__MSG_REQ % (pkt_info[2].ip, 'Listener'), flush=True)
			elif pkt_info[1] == 'pickle':
				client = TCPServer.get_client(pkt_info[0].id_from['ip'], TCPServer.__clients)
				if pkt_info[0].request == '_x_play_x_':
					client.role = 'Player'
					client.clr = pkt_info[0].id_from['clr']
					client.misc = pos(GameLogic._start_pos[0], GameLogic._start_pos[1], 0, 0, 90, None)
					for ino in TCPServer.__inos:
						client.ino = (ino[0], ino[1]) if ino[2] else None
					TCPServer.__players.append(client)
					TCPServer.dm(client, Pkt('_x_maze_outline_x_', {'ip':'0.0.0.0', 'clr':None}, {'ip':'0.0.0.0', 'clr':None}, 
						{'ip':'0.0.0.0', 'clr':None}, zlib.compress(ImageProcessing.img2base64(GameLogic._maze_img_obj)), None, os.urandom(32), None, None))
					rsp = Pkt('_x_new_player_x_', {'ip':'0.0.0.0', 'clr':None}, {'ip':'0.0.0.0', 'clr':None}, 
						{'ip':client.ip, 'clr':client.clr}, None, None, os.urandom(32), client.misc, None)
					TCPServer.broadcast(TCPServer.__players, rsp)
					print(TCPServer.__MSG_REQ % (client.ip, 'Player'), flush=True)
				elif pkt_info[0].request == '_x_gameplay_x_' and client.role == 'Player' and TCPServer.__game_on:
					new_pos = client.misc
					warn = None
					try:
						new_pos, dir = GameLogic.update_pos(client.misc, pkt_info[0].data)
					except OutOfBounds as e:
						warn = "%s (%d, %d)" % (e.msg, e.x, e.y)
					rsp_pick = Pkt('_x_gameplay_x_', {'ip':'0.0.0.0', 'clr':None}, {'ip':'0.0.0.0', 'clr':None}, 
						{'ip':client.ip, 'clr':client.clr}, None, None, os.urandom(32), new_pos, warn)
					rsp_json = PktCompact('_x_gameplay_x_', client.ip, client.clr, dir, new_pos.deg)
					TCPServer.broadcast(TCPServer.__listeners, rsp_json, serial_method='json')
					TCPServer.broadcast(TCPServer.__players, rsp_pick)
					if client.ino:
						client.ino[1].put(dir, block=True)
				elif pkt_info[0].request == '_x_ready_x_' and client.role == 'Player':
					if TCPServer.__game_on:
						rsp = Pkt('_x_start_x_', {'ip':'0.0.0.0', 'clr':None}, {'ip':'0.0.0.0', 'clr':None},
							None, None, None, os.urandom(32), None, None)
						TCPServer.dm(client, rsp)
					else:
						TCPServer.__ready_pkgs.put(pkt_info[0])
						TCPServer.__trig_ready.set()			
			if TCPServer.__pkt_buffer.empty():
				TCPServer.__trig_process.clear()
		TCPServer.__destroy_threads.put(th_id, block=True)
		TCPServer.__cleanup.set()
	
	@staticmethod
	def _wait():
		kill = threading.Event()
		ready_t = threading.Thread(target=TCPServer.__ready_up, args=(kill,), daemon=True)
		ready_t.start()
		if kill.wait():
			ready_t.join()
	
	def __ready_up(kill):
		ips = []
		while TCPServer.__trig_ready.wait() and len(ips) < TCPServer.__player_count:
			if not TCPServer.__ready_pkgs.empty():
				pkt = TCPServer.__ready_pkgs.get(block=True)
				if pkt.request == '_x_ready_x_':
					try:
						index = ips.index(pkt.id_from['ip'])
					except ValueError:
						index = -1
					if index == -1:
						ips.append(pkt.id_from['ip'])
		rsp = Pkt('_x_start_x_', {'ip':'0.0.0.0', 'clr':None}, {'ip':'0.0.0.0', 'clr':None},
			None, None, None, os.urandom(32), None, None)
		TCPServer.broadcast(TCPServer.__players, rsp)
		TCPServer.__game_on = True
		kill.set()
			
	@staticmethod
	def broadcast(users, pkt, serial_method='pickle'):
		for c in users:
			if serial_method == 'json':
				c.sock.send(json.dumps(pkt, cls=PktJsonEncoder).encode('ascii'))
			elif serial_method == 'pickle':
				c.sock.send(pickle.dumps(pkt))
			#print(TCPServer.__MSG_FORWARD % (c.ip, c.role) , flush=True)
	
	@staticmethod
	def dm(user, pkt, serial_method='pickle'):
		if serial_method == 'json':
			user.sock.send(json.dumps(pkt, cls=PktJsonEncoder).encode('ascii'))
		elif serial_method == 'pickle':
			user.sock.send(pickle.dumps(pkt))
		#print(TCPServer.__MSG_FORWARD % (user.ip, user.role) , flush=True)
	
	@staticmethod
	def on_network(client):
		for c in TCPServer.__clients:
			if c.ip == client.ip:
				return True
		return False
	
	@staticmethod
	def get_client(ip, clients):
		for c in clients:
			if c.ip == ip:
				return c
		return None
	
	@staticmethod
	def remove(client):
		print(TCPServer.__MSG_LEFT % client.ip)
		for c in TCPServer.__clients:
			if c.ip == client.ip:
				TCPServer.__clients.remove(c)
				if c in TCPServer.__listeners:
					TCPServer.__listeners.remove(c)
				if c in TCPServer.__players:
					TCPServer.__players.remove(c)