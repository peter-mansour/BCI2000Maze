
import socket
import threading
import queue
import pickle
import time
from connect_utils import *

class TCPClient:
	BUFFER_SZ = 10000
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
				if self.__send_buff.empty():
					trigger.clear()
		except ConnectionResetError:
			print(self.__MSG_DISCONNECT, flush=True)
			self.status.put(self.__ERR, block=True)
		except ConnectionAbortedError as e:
			if e.winerror != 10053:
				raise e
			
	def __rcv_c(self, sock):
		try:
			while not self.__destroy:
				pkt = sock.recv(self.BUFFER_SZ)
				if not self.__rcv_buff.full() and pkt:
					self.__rcv_buff.put(pickle.loads(pkt), block=True)
		except ConnectionAbortedError as e:
			if e.winerror != 10053:
				raise e
		except ConnectionResetError:
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