
import socket
import threading
import queue
import pickle
import time
import sys
import os
from connect_utils import *
import logging
import binascii

if not os.path.isdir('../logs'):
    os.makedirs('../logs')
with open('../logs/tcpclient.log', 'w'):
    pass
log_tcpc = logging.getLogger(__name__)
log_tcpc.setLevel(logging.INFO)
handler_f = logging.FileHandler('../logs/tcpclient.log')
handler_f.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s:%(funcName)s:%(message)s'))
log_tcpc.addHandler(handler_f)

class TCPClient:
    BUFFER_SZ = 10000
    __MSG_NOT_UP = "Server is not running"
    __MSG_DISCONNECT = "Disconnected from server..."
    __ERR = -9999
    __byte_delim = b'?_?'
    __MAX_MSGS = 50

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
            log_tcpc.error(self.__MSG_NOT_UP)
            print(self.__MSG_NOT_UP, flush=True)
            return False
    
    def __send_c(self, sock, trigger):
        try:
            while trigger.wait() and not self.__destroy:
                byte_msg = b''
                msg_sz = 0
                while not self.__send_buff.empty() and msg_sz < self.__MAX_MSGS:
                    pkt = self.__send_buff.get(block=True)
                    if byte_msg:
                        byte_msg+=self.__byte_delim
                    byte_msg+=pickle.dumps(pkt)
                    log_tcpc.info('sending pkt to %s with request %s and transaction id %s'%
                        (self.__IP, pkt.request, str(binascii.hexlify(pkt.txn))))
                    msg_sz+=1
                sock.send(byte_msg)
                trigger.clear()
        except ConnectionResetError as e:
            log_tcpc.error(str(e))
            self.status.put(self.__ERR, block=True)
        except ConnectionAbortedError as e:
            log_tcpc.error(str(e))
            if e.winerror != 10053:
                raise e
            
    def __rcv_c(self, sock):
        try:
            while not self.__destroy:
                pkt = sock.recv(self.BUFFER_SZ)
                if not self.__rcv_buff.full() and pkt:
                    pkts = pkt.split(self.__byte_delim)
                    for p in pkts:
                        pkt_content = pickle.loads(p)
                        log_tcpc.info('received pkt from %s with request %s and transaction id %s'%
                            (self.__IP, pkt_content.request, str(binascii.hexlify(pkt_content.txn))))
                        self.__rcv_buff.put(pkt_content, block=True)
        except ConnectionAbortedError as e:
            log_tcpc.error(str(e))
            self.status.put(self.__ERR, block=True)
            if e.winerror != 10053:
                raise e
        except ConnectionResetError as e:
            log_tcpc.error(str(e))
            self.status.put(self.__ERR, block=True)
        except OSError as e:
            log_tcpc.error(str(e))
            if e.winerror != 10038:
                self.status.put(self.__ERR, block=True)
                raise e
        print(self.__MSG_DISCONNECT, file=sys.stderr)
        self.__sock.shutdown(socket.SHUT_RDWR)
        self.__sock.close()
    
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
        log_tcpc.info('shutting down connection with server')
        self.__destroy = 1