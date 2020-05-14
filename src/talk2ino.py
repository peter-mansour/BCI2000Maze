from BTConnect import *
from win_cmd import Console
import threading
import time
import os
import queue
import logging

if not os.path.isdir('../logs'):
    os.makedirs('../logs')
with open('../logs/talk2ino.log', 'w'):
    pass
log_ino = logging.getLogger(__name__)
log_ino.setLevel(logging.INFO)
handler_f = logging.FileHandler('../logs/talk2ino.log')
handler_f.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s:%(message)s'))
log_ino.addHandler(handler_f)

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
        log_ino.info("Forcebly closed by user: %s" %str(e))
    except OSError as e:
        log_ino.warning(str(e))
    Console.enable_quick_edit()
    
if __name__=="__main__":
    talk2ino(addr_port, inbuff, outbuff)