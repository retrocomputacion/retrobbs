        ############ Classes ############
# any generic classses without companion functions here

########### BBS Class ###########

class BBS:
	def __init__(self, name, ip, port):
		self.name = name
		self.ip = ip
		self.port = port
		self.lang = 'en'
		self.MenuList = None
		self.WMess = ''		#Welcome Message
		self.GBMess = ''	#Logoff Message
