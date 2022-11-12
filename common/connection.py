############ Connection Class ############
#########################################################################
#Changelog																#
#																		#
#	April  6-2021	: Moved all functions to methods inside the			#
#					  Connection class									#
#########################################################################

import socket
from common.bbsdebug import _LOG, bcolors
import datetime
import common.petscii as P
from common.classes import BBS

class Connection:

	def __init__(self, socket, addr, bbs, id):
		self.connected = True
		self.socket = socket
		self.addr = addr
		self.id = id
		self.bbs:BBS = bbs

		# MenuDef entry:
		# [Function, (Parameters tuple), Title, UserClass , WaitKey]
		self.MenuDefs = {}			#Current Menu functions dictionary
		self.MenuParameters = {}	#Current Menu parameters dictionary
		self.MenuStack = []			#Menu stack

		self.waitkey = False		# Menu is waiting for a keypress
		self.showmenu = False		# Menu needs to be redrawn
		self.newmenu = 0			# Temporal menu id storage
		self.menu = 0				# Current menu id

		self.samplerate = 11520		# PCM audio stream samplerate 

		self.outbytes = 0			#Total bytes sent
		self.inbytes = 0			#Total bytes received

		self.username = '_guest_'
		self.userid	= 0
		self.userclass = 0			# 0 = Guest

		self.TermString = '' #Terminal identification string
		self.T56KVer = 0	#Terminal Turbo56K version
		self.TermFt = []	#Terminal features

		_LOG('Incoming connection from', addr,id=id,v=3)
	
	def __del__(self):
		try:
			self.socket.close()
		except:
			pass

	#Close socket
	def Close(self):
		_LOG("Total bytes sent/received: "+str(self.outbytes)+'/'+str(self.inbytes),id=self.id,v=3)
		try:
			self.socket.close()
		except:
			pass

	#Convert string to binary string and sends it via socket
	def Sendall(self, cadena):

		if self.connected == True:
			m = map(ord,cadena)
			l = list(m)
			_bytes = bytearray(l)
			try:
				self.socket.sendall(_bytes)
				self.outbytes += len(_bytes)
			except socket.error:
				self.connected = False
				_LOG(bcolors.WARNING+'Remote disconnect/timeout detected - Sendall'+bcolors.ENDC, id=self.id,v=2)

	#Send binary string via socket
	def Sendallbin(self, cadena=b''):

		if self.connected == True:
			try:
				self.socket.sendall(cadena)
				self.outbytes += len(cadena)
			except socket.error:
				#if e == errno.EPIPE:
				_LOG(bcolors.WARNING+'Remote disconnect/timeout detected - Sendallbin'+bcolors.ENDC, id=self.id,v=2)
				self.connected = False

	#Receive (count) binary chars from socket
	def Receive(self, count):

		cadena = b''
		if self.connected == True:
			for c in range(0,count):
				try:
					cadena += self.socket.recv(1)
					self.inbytes += 1
				except socket.error:
					#if e.errno == errno.ECONNRESET:
					_LOG(bcolors.WARNING+'Remote disconnect/timeout detected - Receive'+bcolors.ENDC, id=self.id,v=2)
					self.connected = False
					cadena = b''
					break

		return cadena

	#Receive single binary char from socket
	def ReceiveKey(self, lista=b'\r'):

		t = True
		while t == True:
			cadena = b''

			if self.connected == True:
				try:
					_LOG("ReceiveKey - Waiting...",id=self.id,v=4)
					cadena = self.socket.recv(1)
					self.inbytes += 1
					_LOG("ReceiveKey - Received", cadena, id=self.id,v=4)
					if cadena != b'':
						if cadena[0] in range(0xC1,0xDA + 1):
							cadena = bytes([cadena[0]-96])
						if cadena in lista:
							t = False
					else:
						self.connected = False
						t = False
				except socket.error:
					#if e.errno == errno.ECONNRESET:
					_LOG(bcolors.WARNING+'Remote disconnect/timeout detected - ReceiveKey'+bcolors.ENDC, id=self.id,v=2)
					cadena = ''
					self.connected = False
					t = False
			else:
				t = False
		return cadena

	#Receive single binary char from socket - NO LOG
	def ReceiveKeyQuiet(self, lista=b'\r'):

		t = True
		while t == True:
			cadena = b''

			if self.connected == True:
				try:
					cadena = self.socket.recv(1)
					self.inbytes += 1
					if cadena != b'':
						if cadena[0] in range(0xC1,0xDA + 1):
							cadena = bytes([cadena[0]-96])
						if cadena in lista:
							t = False
					else:
						self.connected = False
						t = False
				except socket.error:
					#if e.errno == errno.ECONNRESET:
					_LOG(bcolors.WARNING+'Remote disconnect/timeout detected - ReceiveKey'+bcolors.ENDC, id=self.id,v=2)
					cadena = ''
					self.connected = False
					t = False
			else:
				t = False
		return cadena

	#Interactive string reception with echo
	#maxlen = max number of characters to receive
	#pw = True for password entry
	def ReceiveStr(self, keys, maxlen = 20, pw = False):
		
		if b'\r' not in keys:
			keys += b'\r'	#Add RETURN if not originaly included
		if b'\x14' not in keys:
			keys += b'\x14' #Add DELETE if not originaly included
		cadena = b''
		done = False
		while not done:
			if pw:
				k = self.ReceiveKeyQuiet(keys)
			else:
				k = self.ReceiveKey(keys)
			if self.connected:
				if k != b'\r' and k != b'':
					if k == b'\x14':
						if len(cadena) > 0:
							cadena = cadena[:-1]	#Delete character
							self.Sendallbin(k)
					elif len(cadena) < maxlen:
						cadena += k	#Add character
						if pw:
							self.Sendall('*')
						else:
							self.Sendallbin(k)
				else:
					done = True
			else:
				done = True
		return(cadena.decode('ascii','ignore'))

	#Interactive positive integer reception with echo
	#min = minimun value
	#max = maximun value
	#default = default value returned when pressing return
	#auto = if True entry can be canceled by pressing delete with no value entered,
	#		and is completed if the number of digits matches the limits
	def ReceiveInt(self, minv, maxv, defv, auto = False):

		if minv < 0:
			minv = -minv
		if maxv < 0:
			maxv = -minv
		if maxv < minv:
			maxv = minv+1
		if not(minv <= defv <= maxv):
			defv = minv

		#keys = b'0123456789\x14\r'
		temp = b''
		done = False
		vall = max(len(str(minv)),len(str(maxv))) #Max digits
		mins = str(minv).zfill(vall)	#Min value string with padding 0s
		maxs = str(maxv).zfill(vall)	#Max value string with padding 0s
		defs = str(defv).zfill(vall)	#Default value string with padding 0s
		tval = ['0']*vall

		d = 0
		minr = int(mins[0])
		maxr =int(maxs[0])+1
		while True:
			keys = b'\x14'
			if d < vall:
				for x in range(minr,maxr):
					keys += bytearray(str(x),'utf-8')
					if d == 0:
						keys += b'\r'
			else:
				keys += b'\r'
			temp = self.ReceiveKey(keys)
			if not self.connected:
				return(None)
			if d == 0:
				if temp == b'\x14':
					if auto:
						return(None)
					else:
						continue
				elif temp == b'\r':
					self.Sendall(defs)
					return(defv)
			if temp != b'\r':
				self.Sendallbin(temp)
			if temp != b'\x14':
				tval[d] = temp.decode('utf-8')
				d += 1
			else:
				d -= 1
				self.Sendallbin(b'\x94') #Insert

			# Calculate next digit range
			if d == 0:
				minr = int(mins[0])
				maxr =int(maxs[0])+1
			elif d < vall:
				if int(tval[d-1]) == int(mins[d-1]):
					minr = int(mins[d])
				else:
					minr = 0
				if int(tval[d-1]) == int(maxs[d-1]):
					maxr = int(maxs[d])+1
				else:
					maxr = 10
			if d == vall and auto:
				break
		return(int(''.join(tval)))

	# Receive a date, format taken from bbs instance
	# prompt: Text prompt
	# mindate: Earliest date possible
	# maxdate: Latest date possible
	# defdate: Default date
	# all dates of datetime.date type
	# Returns a datetime.date object, None if the parameters are incorrect
	def ReceiveDate(self, prompt, mindate, maxdate, defdate):

		if (mindate > maxdate) or not (mindate <= defdate <= maxdate):
			return None

		odate = defdate

		dateord = [[0,1,2],[1,0,2],[2,1,0]]		#Fields order
		dateleft = [[0,3,3],[3,0,3],[3,5,0]]	#Left cursor count

		dord = dateord[self.bbs.dateformat]
		dleft = dateleft[self.bbs.dateformat]
		if self.bbs.dateformat == 1:
			datestr = "%m/%d/%Y"
			dout = "mm/dd/yyyy"
		elif self.bbs.dateformat == 2:
			datestr = "%Y/%m/%d"
			dout = "yyyy/mm/dd"
		else:
			datestr = "%d/%m/%Y"
			dout = "dd/mm/yyyy"
		while True:
			self.Sendall(prompt+dout+chr(P.CRSR_LEFT)*10)
			x = 0
			while True:
				if x == dord[0]: #0
					day = self.ReceiveInt(1,31,defdate.day,True)
					if not self.connected:
						return
					if day == None:
						if x > 0:
							self.Sendall(chr(P.CRSR_LEFT)*dleft[0])
							x -= 1
						continue
					if x < 2:
						x += 1
						self.Sendall(chr(P.CRSR_RIGHT))
					else:
						if self.ReceiveKey(b'\x14\r') == b'\r':
							break
						else:
							self.Sendall(chr(P.DELETE)*2)
				if x == dord[1]: #1
					month = self.ReceiveInt(1,12,defdate.month,True)
					if not self.connected:
						return
					if month == None:
						if x > 0:
							self.Sendall(chr(P.CRSR_LEFT)*dleft[1])
							x -= 1
						continue
					if x < 2:
						x += 1
						self.Sendall(chr(P.CRSR_RIGHT))
					else:
						if self.ReceiveKey(b'\x14\r') == b'\r':
							break
						else:
							self.Sendall(chr(P.DELETE)*2)
				if x == dord[2]: #2
					year = self.ReceiveInt(mindate.year,maxdate.year,defdate.year,True)
					if not self.connected:
						return
					if year == None:
						if x > 0:
							x -= 1
							self.Sendall(chr(P.CRSR_LEFT)*dleft[2])
						continue
					if x < 2:
						x += 1
						self.Sendall(chr(P.CRSR_RIGHT))
					else:
						if self.ReceiveKey(b'\x14\r') == b'\r':
							break
						else:
							self.Sendall(chr(P.DELETE)*4)
			try:
				odate = datetime.date(year,month,day)
				if mindate <= odate <= maxdate:
					break;
				else:
					self.Sendall("\riNVALID DATE!\r")
			except ValueError:
				self.Sendall("\riNVALID DATE!\r")
		return odate
                    