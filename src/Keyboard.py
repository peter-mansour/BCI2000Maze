import msvcrt
import multiprocessing

class Keyboard:
	mvs = {b'H':'f', b'P':'b', b'K':'l', b'M':'r'}
	SPECIAL_KEY = b'\xe0'
	CTRL_C = b'\x03'

	def get_arrowhits(buff):
		c = None
		while c != Keyboard.CTRL_C:
			c = msvcrt.getch()
			if c == Keyboard.SPECIAL_KEY:
				buff.put(Keyboard.mvs.get(msvcrt.getch()))