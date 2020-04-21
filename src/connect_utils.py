
from json import JSONEncoder

class ClientInfo:
	def __init__(self, sock, ip, ext, clr=None, role=None, pkts=None, misc=None):
		self.sock = sock
		self.ip = ip
		self.ext = ext
		self.role = role
		self.pkts = pkts
		self.misc = misc
		self.clr = clr

class Pkt:
	def __init__(self, subject, id_from={'ip':'0.0.0.0', 'clr':None}, id_to={'ip':'0.0.0.0', 'clr':None}, 
		trgt={'ip':'0.0.0.0', 'clr':None}, data=None, sz=0, txn=None, misc=None, warn=None):
		self.request = subject
		self.data = data
		self.id_from = id_from
		self.id_to = id_to
		self.id_trgt = trgt
		self.sz = sz
		self.txn = txn
		self.misc = misc
		self.warn = warn

class PktCompact:
	def __init__(self, subject=None, plyr_ip=None, plyr_clr=None, direction=None,degree=None):
		self.request = subject
		self.plyr_ip = plyr_ip
		self.plyr_clr = plyr_clr
		self.direction = direction
		self.degree = degree

class PktJsonEncoder(JSONEncoder):
	def default(self, obj):
		return obj.__dict__

