import re
import time
from datetime import datetime as dt_dt
import datetime as dt
import queue
import threading

class FParse:
	__REG         = ".*Selected command: ([A-Z_ ]).*"
	__str_glbl    = ""
	__TIME_OUT    = dt.timedelta(seconds=300)
	__MSG_TIMEOUT = "Parser Timed out"
	__ERR_NOT_FOUND = "File Not Found"
	__MSG_CLOSE_F = "Closing BCI2000 app log: "
	__ERR_FLAG = -9999
	
	def __init__(self, buff):
		self.__regex = re.compile(self.__REG)
		self.__buff = buff
		self.status = queue.Queue()
		self.__destroy = 0

	def __put_on_stream(self, e):
		self.__buff.put(e.lower())
	
	def shutdown(self):
		self.__destroy = 1

	def read(self, path):
		threading.Thread(target=self.__parse_f, args=(path,), daemon=True).start()

	def __parse_f(self, path):
		t_curr = dt_dt.now()
		t_last_match = dt_dt.now()
		try:
			with open(path, "r+") as file:
				file.truncate(0)
				file.close()
			while not self.__destroy and t_curr - t_last_match < self.__TIME_OUT:
				with open(path, "r") as file:
					matches = self.__regex.findall(file.read())
					t_curr = dt_dt.now()
					if len(matches) > len(self.__str_glbl):
						self.__str_glbl = ""
						for m in matches:
							self.__str_glbl += m
						if len(self.__str_glbl) > 0:
							self.__put_on_stream(self.__str_glbl[len(self.__str_glbl)-1].lower())
						t_last_match = dt_dt.now()
					file.close()
			print(self.__MSG_TIMEOUT, flush=True)
			print(self.__MSG_CLOSE_F + path, flush=True)
		except FileNotFoundError:
			print(self.__ERR_NOT_FOUND)
		self.status.put(self.__ERR_FLAG, block=True)