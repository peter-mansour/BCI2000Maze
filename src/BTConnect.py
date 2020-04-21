
import bluetooth as BT
import subprocess
from win_cmd import Console

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