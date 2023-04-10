from html.parser import HTMLParser, starttagopen, charref, entityref, incomplete, endendtag, endtagfind, tagfind_tolerant
import re
#import _markupbase
from html import unescape
from html.entities import name2codepoint
from collections import deque
import common.petscii as P
import common.turbo56k as TT
import common.extensions as EX
#from common.connection import Connection
import time


# Internal registers:
#
# Write only:
# _C = String output to Connection object assigned to this Parser
# _B = Binary output to Connection object assigned to this Parser
#
# Read/Write:
# _A = Accumulator, no type casting
# _S = String accumulator
# _I = Integer accumulator
#
# Read only:
# _R =	Returned value from last function call
#		Used as a special parameter name. Assignation order is reversed ie:
#			('_R','_S') will assign the returned value of the function to .S


t_registers = ['_a','_c','_b','_r','_s','_i']

# Tokens
t_statements = {'mode':[('m','PET64')],'switch':[('r','_A')],'case':[('c',False)],'while':[('c',False)],'if':[('c',False)]}

t_gen_mono = {	'PAUSE':(lambda n:time.sleep(n),[('n',0)]),'AT':(TT.set_CRSR,[('_R','_C'),('x',0),('y',0)]),
	      		'INKEYS':(lambda k:input(),[('_R','_A'),('k','\n')]),
	      		'LET':(lambda x:x,[('_R','_I'),('x','_I')]),'OUT':(lambda x:print(x),[('_R','_C'),('x','_I')]),
	      		'INC':(lambda x:x+1,[('_R','_I'),('x','_I')]),'DEC':(lambda x:x-1,[('_R','_I'),('x','_I')])}
t_gen_multi = {'SPC':' '}

t_mono = 	{'PET64':{'CLR':chr(P.CLEAR),'HOME':chr(P.HOME),'RVSON':chr(P.RVS_ON),'RVSOFF':chr(P.RVS_OFF),'BR':'\r',
			'CBMSHIFT-D':chr(P.DISABLE_CBMSHIFT),'CBMSHIFT-E':chr(P.ENABLE_CBMSHIFT),'UPPER':chr(P.TOUPPER),'LOWER':chr(P.TOLOWER),
			'BLACK':chr(P.BLACK),'WHITE':chr(P.WHITE),'RED':chr(P.RED),'CYAN':chr(P.CYAN),'PURPLE':chr(P.PURPLE),'GREEN':chr(P.GREEN),'BLUE':chr(P.BLUE),'YELLOW':chr(P.YELLOW),
			'ORANGE':chr(P.ORANGE),'BROWN':chr(P.BROWN),'PINK':chr(P.PINK),'GREY1':chr(P.GREY1),'GREY2':chr(P.GREY2),'LTGREEN':chr(P.LT_GREEN),'LTBLUE':chr(P.LT_BLUE),'GREY3':chr(P.GREY3)}
			}
t_multi =	{'PET64':{'CRSRL':chr(P.CRSR_LEFT),'CRSRU':chr(P.CRSR_UP),'CRSRR':chr(P.CRSR_RIGHT),'CRSRD':chr(P.CRSR_DOWN),'DEL':chr(P.DELETE),'INS':chr(P.INSERT),
			'POUND':chr(P.POUND),'PI':chr(P.PI),'HASH':chr(P.HASH),'HLINE':chr(P.HLINE),'VLINE':chr(P.VLINE),'SPC':' '}}
	

class TMLParser(HTMLParser):

	mode = 'PET64'

	# Conversion function for plain text
	t_conv = {'PET64':P.toPETSCII,'ASCII':lambda c: c}

	modes = ['PET64']

	def __init__(self, conn):
		mode = conn.mode
		self.conn = conn
		##### Build dictionaries
		self.t_mono = t_gen_mono.copy()
		#self.t_mono.update(t_mono[mode])
		self.t_mono.update(EX.t_mono)			# Plugins functions
		self.t_mono.update(conn.encoder.tml_mono)	# Encoder definitions
		self.t_mono.update(TT.t_mono)			# Turbo56K functions
		self.t_mono =  {k.lower(): v for k, v in self.t_mono.items()}
		self.t_multi = t_gen_multi.copy()
		#self.t_multi.update(t_multi[mode])
		self.t_multi.update(conn.encoder.tml_multi)
		self.t_multi =  {k.lower(): v for k, v in self.t_multi.items()}
		self.buffer = []
		self.skip = 0	# > 0 if skipping a section
		self.stack = deque('')	# Tag stack push and pop from left - Stack entry format: ('TAG',[parameters],(position))
		##### Registers
		self._A = None
		self._S = ''
		self._I = 0
		self._R = None
		###############
		HTMLParser.__init__(self)
	
	def close(self) -> None:
		self.buffer = []
		return super().close()

	#############################################################
	# Functions taken from the HTMLParser code

	# Internal -- parse endtag, return end or -1 if incomplete
	def parse_endtag(self, i):
		_i = None
		rawdata = self.rawdata
		assert rawdata[i:i+2] == "</", "unexpected call to parse_endtag"
		match = endendtag.search(rawdata, i+1) # >
		if not match:
			return _i, -1
		gtpos = match.end()
		match = endtagfind.match(rawdata, i) # </ + tag + >
		if not match:
			if self.cdata_elem is not None:
				self.handle_data(rawdata[i:gtpos])
				return _i, gtpos
			# find the name: w3.org/TR/html5/tokenization.html#tag-name-state
			namematch = tagfind_tolerant.match(rawdata, i+2)
			if not namematch:
				# w3.org/TR/html5/tokenization.html#end-tag-open-state
				if rawdata[i:i+3] == '</>':
					return _i, i+3
				else:
					return _i, self.parse_bogus_comment(i)
			tagname = namematch.group(1).lower()
			# consume and ignore other stuff between the name and the >
			# Note: this is not 100% correct, since we might have things like
			# </tag attr=">">, but looking for > after the name should cover
			# most of the cases and is much simpler
			gtpos = rawdata.find('>', namematch.end())
			_i, j = self.handle_endtag(tagname)
			if _i != None:
				return _i, j
			return _i, gtpos+1

		elem = match.group(1).lower() # script or style
		if self.cdata_elem is not None:
			if elem != self.cdata_elem:
				self.handle_data(rawdata[i:gtpos])
				return _i, gtpos

		_i, j = self.handle_endtag(elem)
		if _i != None:
			return _i, j
		self.clear_cdata_mode()
		return _i, gtpos

	# Internal -- handle data as far as reasonable.  May leave state
	# and data to be processed by a subsequent call.  If 'end' is
	# true, force handling all data as if followed by EOF marker.
	def goahead(self, end):
		rawdata = self.rawdata
		i = 0
		n = len(rawdata)
		while i < n:
			if self.convert_charrefs and not self.cdata_elem:
				j = rawdata.find('<', i)
				if j < 0:
					# if we can't find the next <, either we are at the end
					# or there's more text incoming.  If the latter is True,
					# we can't pass the text to handle_data in case we have
					# a charref cut in half at end.  Try to determine if
					# this is the case before proceeding by looking for an
					# & near the end and see if it's followed by a space or ;.
					amppos = rawdata.rfind('&', max(i, n-34))
					if (amppos >= 0 and
						not re.compile(r'[\s;]').search(rawdata, amppos)):
						break  # wait till we get all the text
					j = n
			else:
				match = self.interesting.search(rawdata, i)  # < or &
				if match:
					j = match.start()
				else:
					if self.cdata_elem:
						break
					j = n
			if i < j:
				if self.convert_charrefs and not self.cdata_elem:
					self.handle_data(unescape(rawdata[i:j]))
				else:
					self.handle_data(rawdata[i:j])
			i = self.updatepos(i, j)
			if i == n: break
			startswith = rawdata.startswith
			if startswith('<', i):
				if starttagopen.match(rawdata, i): # < + letter
					k = self.parse_starttag(i)
				elif startswith("</", i):
					_i, k = self.parse_endtag(i)
					if _i != None:
						i = _i
				elif startswith("<!--", i):
					k = self.parse_comment(i)
				elif startswith("<?", i):
					k = self.parse_pi(i)
				elif startswith("<!", i):
					k = self.parse_html_declaration(i)
				elif (i + 1) < n:
					self.handle_data("<")
					k = i + 1
				else:
					break
				if k < 0:
					if not end:
						break
					k = rawdata.find('>', i + 1)
					if k < 0:
						k = rawdata.find('<', i + 1)
						if k < 0:
							k = i + 1
					else:
						k += 1
					if self.convert_charrefs and not self.cdata_elem:
						self.handle_data(unescape(rawdata[i:k]))
					else:
						self.handle_data(rawdata[i:k])
				#print('update',i,k)
				i = self.updatepos(i, k)
			elif startswith("&#", i):
				match = charref.match(rawdata, i)
				if match:
					name = match.group()[2:-1]
					self.handle_charref(name)
					k = match.end()
					if not startswith(';', k-1):
						k = k - 1
					i = self.updatepos(i, k)
					continue
				else:
					if ";" in rawdata[i:]:  # bail by consuming &#
						self.handle_data(rawdata[i:i+2])
						i = self.updatepos(i, i+2)
					break
			elif startswith('&', i):
				match = entityref.match(rawdata, i)
				if match:
					name = match.group(1)
					self.handle_entityref(name)
					k = match.end()
					if not startswith(';', k-1):
						k = k - 1
					i = self.updatepos(i, k)
					continue
				match = incomplete.match(rawdata, i)
				if match:
					# match.group() will contain at least 2 chars
					if end and match.group() == rawdata[i:]:
						k = match.end()
						if k <= i:
							k = n
						i = self.updatepos(i, i + 1)
					# incomplete
					break
				elif (i + 1) < n:
					# not the end of the buffer, and can't be confused
					# with some other construct
					self.handle_data("&")
					i = self.updatepos(i, i + 1)
				else:
					break
			else:
				assert 0, "interesting.search() lied"
		# end while
		if end and i < n and not self.cdata_elem:
			if self.convert_charrefs and not self.cdata_elem:
				self.handle_data(unescape(rawdata[i:n]))
			else:
				self.handle_data(rawdata[i:n])
			i = self.updatepos(i, n)
		self.rawdata = rawdata[i:]

    # Internal -- update line number and offset.  This should be
    # called for each piece of data exactly once, in order -- in other
    # words the concatenation of all the input strings to this
    # function should be exactly the entire input.
	def updatepos(self, i, j):
		if i >= j:
			return j
		rawdata = self.rawdata
		nlines = rawdata.count("\n", i, j)
		if nlines:
			self.lineno = self.lineno + nlines
			pos = rawdata.rindex("\n", i, j) # Should not fail
			self.offset = j-(pos+1)
		else:
			self.offset = j
		return j

	#
	#############################################################

	def process(self, data: str):
		data = data.translate({ord(i): None for i in '\t\r\n'})	# remove control characters
		self.close()
		self.skip = 0
		self.stack.clear()
		self.prev = [0,0]
		##### Registers
		self._A = None
		self._S = ''
		self._I = 0
		self._R = None
		###############
		super().feed(data)
		super().close()
		super().reset()


	def _insert(self,data):
		if len(self.buffer) == 0:
			self.buffer.append(data)
		else:
			if isinstance(data,tuple):
				self.buffer.append(data)
			elif isinstance(data,str):
				if isinstance(self.buffer[-1],str):
					self.buffer[-1] += data
				else:
					self.buffer.append(data)

	# Find latest instance of 'tag' pushed into the stack and return the entry without disturbing the stack 
	def _findLatest(self, tag:str):
		for i in range(len(self.stack)):
			if self.stack[i][0] == tag:
				return self.stack[i]
		return None
	
	# Pop entries from the stack until 'tag' is found
	def _popLatest(self, tag:str):
		if self._findLatest(tag) != None:
			while (en := self.stack.popleft())[0] != tag:
				pass
			return en
		else:
			return None
	
	# Eval parameter
	def _evalParameter(self, data, default):
		try:	#convert to target type
			data = eval(data,{'_A':self._A,'_I':self._I,'_S':self._S,'_C':self.conn})
			if type(default) == int:
				data = int(data)
		except:
			data = default
		return data

	def handle_starttag(self, tag, attrs):
		#print(tag, self.getpos())
		# if self.skip != 0:
		# 	return
		parms = []
		attr =  dict(attrs)
		if tag in t_statements:
			epos = self.getpos()[1]
			spos = self.rawdata[:epos].rfind('<')
			if self.skip != 0:
				self.skip += 1
			# Handle MODE
			elif tag == 'mode':
				if attr.get('m','PET64') != self.mode:
					self.skip += 1
			# Handle WHILE
			elif tag == 'while':
				if self._evalParameter(attr.get('c',False),False):
					self.stack.appendleft((tag,[],(spos,epos)))
				else:
					self.skip += 1
			# Handle SWITCH
			elif tag == 'switch':
				parm = self._evalParameter(attr.get('r',0),0)
				self.stack.appendleft((tag,parm,(spos,epos)))
			# Handle CASE
			elif tag == 'case':
				if self._findLatest('switch') != None:
					parm = self._evalParameter(attr.get('c',0),0)
					if parm != self._findLatest('switch')[1]:
						self.skip += 1
					else:
						self.stack.appendleft((tag,[],(spos,epos)))
			# Handle IF
			elif tag == 'if':
				if self._evalParameter(attr.get('c',False),False):
					self.stack.appendleft((tag,[],(spos,epos)))
				else:
					self.skip += 1

		elif self.skip == 0: 
			if tag in self.t_mono:
				if isinstance(self.t_mono[tag],str):
					#print(self.t_mono[tag], flush=True, end='')
					self.conn.Sendall(self.t_mono[tag])
				else:
					func = self.t_mono[tag][0]
					ret = None
					for p in self.t_mono[tag][1]:
						val = attr.get(p[0],p[1])
						if p[0] == '_R' and val.lower() in t_registers:
							ret = val
						else:
							val = self._evalParameter(val,p[1])
							parms.append(val)
						...
					#print(tag,parms,ret)
					self._R = func(*parms)
					if ret == '_A':
						self.set_A(self._R)
					elif ret == '_I':
						self.set_I(self._R)
					elif ret == '_S':
						self.set_S(self._R)
					elif ret == '_C':
						#print('\nString:',self._R)
						self.conn.Sendall(self._R)
					elif ret == '_B':
						#print('\nBinary:',self._R)
						self.conn.Sendallbin(self._R)
			elif tag in self.t_multi:
				n = self._evalParameter(attr.get('n','1'),1)
				for i in range(n):
					self.conn.Sendall(self.t_mono[tag])
					# print(self.t_multi[tag], flush=True, end='')
			else:
				print('invalid tag')

	def handle_endtag(self, tag):
		#print("End tag  :", tag, self.skip)
		i = j = None
		if tag in t_statements:
			if self.skip > 0:
				self.skip -= 1
			elif tag == 'while':	# WHILE loop
				pos = self._popLatest(tag)
				#print('while pos',pos, self._I)
				i,j = pos[2][0],pos[2][1]
			elif tag in ['switch','case','if']:	# SWITCH/CASE/IF
				pos = self._popLatest(tag)

		return (i, j)

	def handle_data(self, data):
		if self.skip == 0:
			if len(self.stack) > 0:
				if self.stack[0][0] == 'switch':	# Dont parse orphan data in-between switch and case tags
					return
			#print(self.t_conv[self.mode](data.translate({ord(i): None for i in '\t\r\n'})),end='',flush=True)
			self.conn.Sendall(self.t_conv[self.mode](data.translate({ord(i): None for i in '\t\r\n'})))

	def handle_comment(self, data):
		# print("Comment  :", data)
		...

	def handle_entityref(self, name):
		if self.skip == 0:
			c = chr(name2codepoint[name])
			# print("Named ent:", c)

	def handle_charref(self, name):
		if self.skip == 0:
			if name.startswith('x'):
				c = chr(int(name[1:], 16))
			else:
				c = chr(int(name))
			# print("Num ent  :", c)

	def handle_decl(self, data):
		# print("Decl     :", data)
		...
	
	def handle_pi(self, data: str):
		data = data.strip('?').split('=')
		data[1] = data[1].strip('"\'')
		...
	
	# Set internal registers
	############################
	def set_I(self,data):
		try:
			self._I = int(data)
		except:
			self._I = 0

	def set_S(self,data):
		try:
			self._S = str(data)
		except:
			self._S = ''
	
	def set_A(self,data):
		self._A = data

# parser = TMLParser('PET64')

# x = 2

# parser.process(f'<MODE m=PET64><CLR>Da&ta<POUND n={x}><PAUSE n=2> S <WHILE c="_I>-2" >newline<DEC></WHILE><VLINE></MODE>Outside')



# parser.close()
# print()

# x = 20

# parser.process(f"""
# <MODE m=PET64>
# 	<BLUE>SeCOND<HLINE n={x}>
# 	<LET _R=_I x=0>
# 	<PAUSE n=2+_I>newline
# 	<LET _R=_I x=5>
# 	<OUT x=_I>
# 	<POUND n=_I>
# 	<SWITCH r=_I>
# 		<CASE c=5>
# 			cInCo
# 			<LET _R=_I x=0>
# 			<WHILE c="_I<{x}">
# 				HEY! MACARENA 
# 				<INC _R=_I>
# 			</WHILE>
# 		</CASE>
# 		hola
# 		<CASE c=4>
# 			cuatro
# 		</CASE>
# 	</SWITCH>
# 	<INKEYS>
# 	Result:
# 	<OUT x=_A>
# 	<IF c="_A=='G'">
# 		VERDADERO
# 	</IF>
# 	<AT x=23 y=30/3>
# </MODE>""")

# parser.close()
# print()
