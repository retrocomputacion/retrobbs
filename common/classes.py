        ############ Classes ############
# any generic classses without companion functions here

from common.dbase import DBase

########### BBS Class ###########

class BBS:
	def __init__(self, name, ip, port):
		self.name = name
		self.ip = ip
		self.port = port
		self.lang = 'en'
		self.MenuList = None
		self.WMess = ''			#Welcome Message
		self.GBMess = ''		#Logoff Message
		self.OSText = ''		#Host OS (Specific distro for Linux)
		self.TOut = 60*5		#Default Connection Timeout
		self.Paths = {'bbsfiles': 'bbsfiles/', 'plugins': 'plugins/', }
		self.PlugOptions = {}	#Plugins options from the config file
		self.BoardOptions = {}	#Message boards options from the config file
		self.dateformat = 0		#Date format
		self.database = DBase()
		self.version = 0		#BBS version

	def __del__(self):
		self.database.closeDB()