############ Connection Class ############
#########################################################################
#Changelog																#
#																		#
#	April  6-2021	: Moved all functions to methods inside the			#
#					  Connection class									#
#########################################################################

import socket
from common.bbsdebug import _LOG, bcolors

class Connection:

	def __init__(self, socket, addr, bbs, id):
		self.connected = True
		self.socket = socket
		self.addr = addr
		self.id = id
		self.bbs = bbs

		# MenuDef entry:
		# [Function, (Parameters tuple), Title, ShowMenu , WaitKey]
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
		self.userclass = 0			# 0 = Guest
		_LOG('Incoming connection from', addr,id=id)
	
	def __del__(self):
		try:
			self.socket.close()
		except:
			pass

	#Close socket
	def Close(self):
		_LOG("Total bytes sent/received: "+str(self.outbytes)+'/'+str(self.inbytes),id=self.id)
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
				_LOG(bcolors.WARNING+'Remote disconnect/timeout detected - Sendall'+bcolors.ENDC, id=self.id)

	#Send binary string via socket
	def Sendallbin(self, cadena=b''):

		if self.connected == True:
			try:
				self.socket.sendall(cadena)
				self.outbytes += len(cadena)
			except socket.error:
				#if e == errno.EPIPE:
				_LOG(bcolors.WARNING+'Remote disconnect/timeout detected - Sendallbin'+bcolors.ENDC, id=self.id)
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
					_LOG(bcolors.WARNING+'Remote disconnect/timeout detected - Receive'+bcolors.ENDC, id=self.id)
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
					_LOG("ReceiveKey - Waiting...",id=self.id)
					cadena = self.socket.recv(1)
					self.inbytes += 1
					_LOG("ReceiveKey - Received", cadena, id=self.id)
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
					_LOG(bcolors.WARNING+'Remote disconnect/timeout detected - ReceiveKey'+bcolors.ENDC, id=self.id)
					cadena = ''
					self.connected = False
					t = False
			else:
				t = False
		return cadena

	#Interactive reception with echo
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
			k = self.ReceiveKey(keys)
			if self.connected:
				if k != b'\r' and k != b'':
					if k == b'\x14':
						if len(cadena) > 0:
							cadena = cadena[:-1]	#Delete character
							self.Sendallbin(k)
					elif len(cadena) < maxlen:
						cadena += k	#Add character
						#print(cadena)
						if pw:
							self.Sendall('*')
						else:
							self.Sendallbin(k)
				else:
					done = True
			else:
				done = True
		return(cadena.decode('ascii','ignore'))

