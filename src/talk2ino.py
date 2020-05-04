from BTConnect import *
from win_cmd import Console
import threading
import time
import os
import queue

def talk2ino(addr_port, inbuff, outbuff):
	try:
		Console.disable_quick_edit()
		bt_dev = BTConnect(addr_port[0], addr_port[1])
		bt_dev.connect()
		status = queue.Queue()
		threading.Thread(target=bt_dev.rcv, args=(inbuff,status), daemon=True).start()
		while status.empty() or status.get(block=True):
			if not outbuff.empty():
				bt_dev.send(outbuff.get(block=True))
		bt_dev.disconnect()
	except KeyboardInterrupt:
		pass
	except OSError as e:
		print(str(e))
	Console.enable_quick_edit()
	
if __name__=="__main__":
	talk2ino(addr_port, inbuff, outbuff)