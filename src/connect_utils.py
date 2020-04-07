import bluetooth as BT
import subprocess
import socket
import threading
import queue
import pickle
import time
from win_cmd import Console

class TCPServer:
	BUFFER_SZ = 150
	__MSG_JOIN = "%s joined the network"
	__MSG_REQ = "%s requested to be a %s"
	__MSG_WELCOME = "Server is Up and Running..."
	__HOW2CLOSE = "Ctrl + C to close Server"
	__MSG_FORWARD = "forwarding pkt to %s (%s) from %s (%s)"
	__MSG_LEFT = "%s left the network"
	__MSG_REJECT_JOIN = "Rejected %s request to join (already on network)"
	__clients = []
	__players = []
	__listeners = []
	
	def __init__(self, IP, PORT):
		self.__IP = IP
		self.__PORT = PORT
		self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.__run_host_t = threading.Thread(target=self.__run_host, args=(self.__sock,), daemon=True)
	
	def setup_host(self):
		self.__sock.bind((self.__IP, self.__PORT))
		self.__run_host_t.start()
	
	def __run_host(self, server_sock):
		Console.disable_quick_edit()
		print(self.__MSG_WELCOME, flush=True)
		print(self.__HOW2CLOSE)
		server_sock.listen(1)
		while True:
			sock, (ip, ext) = server_sock.accept()
			client = ClientInfo(sock, ip, ext, ' ')
			Console.disable_quick_edit()
			if not self.on_network(client):
				self.__clients.append(client)
				print(self.__MSG_JOIN % client.ip, flush=True)
				client_t = threading.Thread(target=self.__talk2client, args=(client,), daemon=True)
				client_t.start()
			else:
				print(self.__MSG_REJECT_JOIN % client.ip)
	
	def __talk2client(self, client):
		try:
			while True:
				pkt = client.sock.recv(self.BUFFER_SZ)
				pkt_content = pickle.loads(pkt)
				if pkt:
					if pkt_content.val == '_x_play_x_':
						client.role = 'Player'
						self.__players.append(client)
						Console.disable_quick_edit()
						print(self.__MSG_REQ % (client.ip, 'Player'), flush=True)
					elif pkt_content.val == '_x_watch_x_':
						client.role = 'Listener'
						self.__listeners.append(client)
						Console.disable_quick_edit()
						print(self.__MSG_REQ % (client.ip, 'Listener'), flush=True)
					elif self.get_client(pkt_content.ip).role != 'Listener':
						self.broadcast(self.__listeners, client, pkt)
						self.broadcast(self.__players, client, pkt)
				else:
					self.remove(client)
					break
			client.sock.close()
		except (ConnectionResetError, EOFError):
			self.remove(client)
			
	def broadcast(self, users, sender, pkt):
		for c in users:
			c.sock.send(pkt)
			Console.disable_quick_edit()
			print(self.__MSG_FORWARD % (c.ip, c.role, sender.ip, sender.role) , flush=True)
	
	def on_network(self, client):
		for c in self.__clients:
			if c.ip == client.ip:
				return True
		return False
	
	def get_client(self, ip):
		for c in self.__clients:
			if c.ip == ip:
				return c
		return None
	
	def remove(self, client):
		print(self.__MSG_LEFT % client.ip)
		for c in self.__clients:
			if c.ip == client.ip:
				self.__clients.remove(c)
				if c in self.__listeners:
					self.__listeners.remove(c)
				if c in self.__players:
					self.__players.remove(c)

class ClientInfo:
	def __init__(self, sock, ip, ext, role):
		self.sock = sock
		self.ip = ip
		self.ext = ext
		self.role = role

class Pkt:
	def __init__(self, val, ip, clr):
		self.val = val
		self.ip = ip
		self.clr = clr

class TCPClient:
	BUFFER_SZ = 150
	__MSG_NOT_UP = "Server is not running"
	__MSG_DISCONNECT = "Disconnected from server..."
	__ERR = -9999

	def __init__(self, IP, PORT):
		self.__IP = IP
		self.__PORT = PORT
		self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.__send_buff = queue.Queue()
		self.__trigger_send = threading.Event()
		self.__rcv_buff = queue.Queue()
		self.__send_t = threading.Thread(target=self.__send_c, args=(self.__sock, self.__trigger_send), daemon=True)
		self.__rcv_t = threading.Thread(target=self.__rcv_c, args=(self.__sock,), daemon=True)
		self.status = queue.Queue()
		self.__destroy = 0
		
	def join(self):
		try:
			self.__sock.connect((self.__IP, self.__PORT))
			self.__send_t.start()
			self.__rcv_t.start()
			return True
		except socket.error:
			print(self.__MSG_NOT_UP, flush=True)
			return False
	
	def __send_c(self, sock, trigger):
		try:
			while trigger.wait() and not self.__destroy and not self.__send_buff.empty():
				sock.send(pickle.dumps(self.__send_buff.get(block=True)))
				time.sleep(0.5)
				trigger.clear()
		except ConnectionResetError as e:
			print(self.__MSG_DISCONNECT, flush=True)
			self.status.put(self.__ERR, block=True)
			
	def __rcv_c(self, sock):
		try:
			while not self.__destroy:
				pkt = sock.recv(self.BUFFER_SZ)
				if not self.__rcv_buff.full() and pkt:
					self.__rcv_buff.put(pickle.loads(pkt), block=True)
		except ConnectionResetError as e:
			print(self.__MSG_DISCONNECT, flush=True)
			self.status.put(self.__ERR, block=True)
		except OSError as e:
			if e.winerror != 10038:
				raise e
	
	def send(self, msg):
		self.__send_buff.put(msg, block=True)
		self.__trigger_send.set()
	
	def get(self):
		if not self.__rcv_buff.empty():
			return self.__rcv_buff.get(block=True)
		return None
	
	def flush(self):
		with self.__rcv_buff.mutex:
			self.__rcv_buff.queue.clear()
		with self.__send_buff.mutex:
			self.__send_buff.queue.clear()
	
	def shutdown(self):
		self.__destroy = 1
		self.__sock.shutdown(socket.SHUT_RDWR)
		self.__sock.close()

class BTConnect:
	TRIAL_COUNT     = 3
	SEARCH_FOR      = 5
	MSG_SEARCHING   = "Looking for nearby BT devices..."
	MSG_BTS         = "Nearby BT devices:"
	MSG_NO_BTS      = "No BT devices found"
	MSG_BT_NOTFOUND = "Could not locate target BT device"
	DIVIDER         = "+-----------------+---------------------+"
	format_lng      = "| %s | %s\t|"
	format_shrt     = "| %s\t  | %s\t|"
	COL_WIDTH       = 15
	MSG_BT_FOUND    = "Found target BT device"
	MSG_FIND_FAILED = "Make sure target BT device is in range and is turned on!"
	MSG_CONNECT     = "Connected to target BT device..."
	__MSG_DISCONNECT  = "Disconnecting BT device..."
	
	def __init__(self, trgt_addr, trgt_port):
		self.port       = trgt_port
		self.trgt_addr  = trgt_addr
		self.__sock       = BT.BluetoothSocket(BT.RFCOMM)
		
	def connect(self, addr):
		if addr != "":
			self.__sock.connect((addr, self.port))
			print(self.MSG_CONNECT)
			
	def find(self):
		trial = 0
		addr = ""
		
		while addr == "" and trial < self.TRIAL_COUNT:
			trial+=1
			print(self.MSG_SEARCHING)
			bt_devices = BT.discover_devices(lookup_names = True, 
						 duration = self.SEARCH_FOR, flush_cache = True)
			if len(bt_devices)!=0:
				print(self.MSG_BTS, flush=True)
				print(self.DIVIDER, flush=True)
				print(self.format_shrt %("Device Name", "Device Address"))
				print(self.DIVIDER)
				for dev_addr, dev_id in bt_devices:
					if len(dev_id) < self.COL_WIDTH:
						str_form = self.format_shrt
					else:
						str_form = self.format_lng
					print(str_form%(dev_id[:self.COL_WIDTH], dev_addr),flush=True)
					if dev_addr == self.trgt_addr:
						addr = dev_addr
					print(self.DIVIDER, flush=True)
			else:
				print(self.MSG_NO_BTS, flush=True)
			if addr == "":
				print(self.MSG_BT_NOTFOUND, flush=True)
			else:
				print(self.MSG_BT_FOUND, flush=True)
		if addr == "":
			print(self.MSG_FIND_FAILED, flush=True)
		
		return addr
	
	def disconnect(self):
		print(self.__MSG_DISCONNECT, flush=True)
		self.__sock.close()
		
	def send(self, data):
		err = "Failed to send msg to"
		connected_dev = subprocess.getoutput("hcitool con")
		if self.trgt_addr in connected_dev:
			self.__sock.send(data)
		else:
			raise RuntimeError(err+self.trgt_addr)