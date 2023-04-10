        ############ Classes ############
# any generic classses without companion functions here

from common.dbase import DBase
import time

########### BBS Class ###########

class BBS:
	def __init__(self, name, ip, port):
		self.name = name
		self.ip = ip
		self.port = port
		self.lines = 5			#Number of simultaneous incoming connections
		self.lang = 'en'
		self.MenuList = None
		self.WMess = ''			#Welcome Message
		self.GBMess = ''		#Logoff Message
		self.BSYMess = ''		#Busy Message
		self.OSText = ''		#Host OS (Specific distro for Linux)
		self.TOut = 60*5		#Default Connection Timeout
		self.Paths = {'bbsfiles': 'bbsfiles/', 'plugins': 'plugins/', }
		self.PlugOptions = {}	#Plugins options from the config file
		self.BoardOptions = {}	#Message boards options from the config file
		self.Paths = {}			#Preset paths
		self.dateformat = 0		#Date format
		self.database = None	#Database
		self.version = 0		#BBS version
		self.runtime = 0		#Timestamp this BBS session started
		self.visits = 0			#Number of visits in this session
		self.cfgmts = 0			#Config file modification timestamp
		self.plugins = {}		#Plugins
		self.encoders = {}		#Encoders

	def start(self):
		if self.database != None:
			self.stop()
		self.database = DBase(self.Paths['bbsfiles'])
		self.runtime = time.time()

	def stop(self):
		if self.database != None:
			self.database.uptime(time.time() - self.runtime)	#Update total uptime
			self.database.closeDB()

	def __del__(self):
		self.stop()

