
import bluetooth as BT
import subprocess
import logging
import os

if not os.path.isdir('../logs'):
    os.makedirs('../logs')
with open('../logs/btconnect.log', 'w'):
    pass
log_bt = logging.getLogger(__name__)
log_bt.setLevel(logging.INFO)
handler_f = logging.FileHandler('../logs/btconnect.log')
handler_f.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s:%(message)s'))
log_bt.addHandler(handler_f)

class BTConnect:
    __MSG_CONNECT     = "Connected to target BT device..."
    __MSG_NO_CONNECT  = "Failed to connect to target BT device..."
    __MSG_DISCONNECT  = "Disconnecting BT device..."
    __MSG_FIND_FAILED = "Make sure target BT device is in range and is turned on!"
    __MSG_BT_NOTFOUND = "Could not locate target BT device"
    __TRIAL_COUNT     = 3
    __SEARCH_FOR      = 5
    __MSG_SEARCHING   = "Looking for nearby BT devices..."
    __MSG_BTS         = "Nearby BT devices:"
    __MSG_NO_BTS      = "No BT devices found"
    __MSG_BT_NOTFOUND = "Could not locate target BT device"
    __DIVIDER         = "+-----------------+---------------------+"
    __FORMAT_LNG     = "| %s | %s\t|"
    __FORMAT_SHRT     = "| %s\t  | %s\t|"
    __COL_WIDTH       = 10
    __MSG_BT_FOUND    = "Found target BT device"
    __MSG_FIND_FAILED = "Make sure target BT device is in range and is turned on!"
    __BUFF_SZ = 9600
    
    def __init__(self, trgt_addr, trgt_port):
        self.__port       = trgt_port
        self.__trgt_addr  = trgt_addr
        self.__sock       = BT.BluetoothSocket(BT.RFCOMM)
    
    @staticmethod
    def find(addr=None, verbose=True):
        trial = 0
        found = False
        
        while not found and trial < BTConnect.__TRIAL_COUNT:
            trial+=1
            if verbose:
                print(BTConnect.__MSG_SEARCHING)
            log_bt.info(BTConnect.__MSG_SEARCHING)
            bt_devices = BT.discover_devices(lookup_names = True, 
                         duration = BTConnect.__SEARCH_FOR, flush_cache = True)
            if len(bt_devices):
                if verbose:
                    print(BTConnect.__MSG_BTS, flush=True)
                    print(BTConnect.__DIVIDER, flush=True)
                    print(BTConnect.__FORMAT_SHRT %("Device Name", "Device Address"))
                    print(BTConnect.__DIVIDER)
                log_bt.info(BTConnect.__MSG_BTS)
                log_bt.info(BTConnect.__DIVIDER)
                log_bt.info(BTConnect.__FORMAT_SHRT %("Device Name", "Device Address"))
                log_bt.info(BTConnect.__DIVIDER)
                for dev_addr, dev_id in bt_devices:
                    if verbose:
                        if len(dev_id) < BTConnect.__COL_WIDTH:
                            str_form = BTConnect.__FORMAT_SHRT
                        else:
                            str_form = BTConnect.__FORMAT_LNG
                        print(str_form%(dev_id[:BTConnect.__COL_WIDTH], dev_addr),flush=True)
                        log_bt.info(str_form%(dev_id[:BTConnect.__COL_WIDTH], dev_addr))
                    if dev_addr == addr:
                        found = True
                    if verbose:
                        print(BTConnect.__DIVIDER, flush=True)
                    log_bt.info(BTConnect.__DIVIDER)
            else:
                log_bt.info(BTConnect.__MSG_NO_BTS)
                if verbose:
                    print(BTConnect.__MSG_NO_BTS, flush=True)
            if not found:
                log_bt.info(BTConnect.__MSG_BT_NOTFOUND)
                log_bt.info(BTConnect.__MSG_FIND_FAILED)
                if verbose:
                    print(BTConnect.__MSG_BT_NOTFOUND, flush=True)
                    print(BTConnect.__MSG_FIND_FAILED, flush=True)
            else:
                log_bt.info(BTConnect.__MSG_BT_FOUND)
                if verbose:
                    print(BTConnect.__MSG_BT_FOUND, flush=True)
        return found
    
    def connect(self):
        if BTConnect.find(self.__trgt_addr, True):
            self.__sock.connect((self.__trgt_addr, self.__port))
            log_bt.info(self.__MSG_CONNECT)
        else:
            log_bt.warning(self.__MSG_NO_CONNECT)
    
    def disconnect(self):
        log_bt.info(self.__MSG_DISCONNECT)
        self.__sock.close()
        
    def rcv(self, inbuff, status):
        while True:
            val = self.__sock.recv(self.__BUFF_SZ)
            if val:
                log_bt.info('received %s from %s'%(val, self.__trgt_addr))
                inbuff.put(val, block=True)
            else:
                log_bt.info('Connection was terminated by BT server')
                status.put(0, block=True)

    def send(self, data):
        if self.__sock.send(data):
            log_bt.info('Sent %s to %s' % (data, self.__trgt_addr))
        else:
            log_bt.warning('Failed to send %s to %s' % (data, self.__trgt_addr))