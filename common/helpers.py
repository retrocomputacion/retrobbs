############## Helpers ##############
# BBS stuff needed by external  	#
# modules that dont belong anywhere #
# else								#
#############################################################################
# Changelog:																#
#																			#
#	April  6-2021:	More() can now correctly print text with color codes	#
#					and a few other PETSCII control codes					#
#############################################################################


import textwrap
import itertools

from common.connection import Connection
from common import petscii as P
from common import turbo56k as TT
from common.style import bbsstyle, default_style, KeyPrompt


# Valid keys for menu entries
valid_keys = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890\\*;/'


# Menu alternating colors
menu_colors = [[P.LT_BLUE,P.GREY3],[P.CYAN,P.YELLOW]]

# convert int to Byte
_byte = lambda i: i.to_bytes(1,'little')


# Paginate current menu
def SetPage(conn:Connection,page):
    #global MenuParameters

    if conn.MenuParameters != {}:
        conn.MenuParameters['current'] = page


# Go back to previous/main menu
def MenuBack(conn:Connection):

	conn.MenuDefs,conn.menu = conn.MenuStack[-1]#0
	conn.MenuStack.pop()

	#Function = conn.MenuDefs[b'\r'][0]
	#Function(*conn.MenuDefs[b'\r'][1])

	conn.waitkey = False
	#conn.showmenu = True

	#reset menuparameters
	conn.MenuParameters = {}

#Format text to X columns with wordwrapping, PETSCII conversion optional
def formatX(text, columns = 40, convert = True):
	wrapper = textwrap.TextWrapper(width=columns)
	if convert == True:
		text = P.toPETSCII(text)
	output = []
	for i in text.replace('\r','\n').split('\n'):
		if i != '':
			output.append(wrapper.wrap(i))
		else:
			output.append('\r')
	#text = [wrapper.wrap(i) for i in text.split('\n') if i !='']
	output = list(itertools.chain.from_iterable(output))
	return(output)

# Find last color control code used in a string
def lastColor(text,defcolor=1):
	pos = -1
	for c in P.PALETTE:
		x = text.rfind(chr(c))
		if x > pos:
			pos = x
			defcolor = c
	return defcolor


#Text pagination
def More(conn:Connection, text, lines, colors=default_style):

	conn.Sendall(chr(P.PALETTE[colors.TxtColor]))
	if isinstance(text, list):
		l = 0
		tcolor = colors.TxtColor
		for t in text:
			conn.Sendall(t)
			tt = t.translate({ord(c):None for c in P.NONPRINTABLE})
			if len(tt) < 40 and t[-1]!='\r':
				conn.Sendall('\r')
			# Find last text color
			tcolor = P.PALETTE.index(lastColor(t,P.PALETTE[tcolor]))
			# pos = -1
			# for c in P.PALETTE:
			# 	x = t.rfind(chr(c))
			# 	if x > pos:
			# 		pos = x
			# 		tcolor = P.PALETTE.index(c)
			l+=1
			if l==(lines-1):
				conn.Sendall(chr(P.PALETTE[colors.PbColor])+'['+chr(P.PALETTE[colors.PtColor])+'return OR _'+chr(P.PALETTE[colors.PbColor])+']')
				k = conn.ReceiveKey(b'\r_')
				if conn.connected == False:
					return(-1)
				if k == b'_':
					return(-1)
				conn.Sendall(chr(P.DELETE)*13+chr(P.PALETTE[tcolor]))
				l = 0
		conn.Sendall(chr(P.PALETTE[colors.PbColor])+'['+chr(P.PALETTE[colors.PtColor])+'return'+chr(P.PALETTE[colors.PbColor])+']')
		conn.ReceiveKey()
	else:
		prompt='RETURN'
		cc=0
		ll=0
		page = 0
		rvs = ''
		color = ''
		pp = False
		#colors = (P.BLACK,P.WHITE,P.RED,P.PURPLE,P.CYAN,P.GREEN,P.BLUE,P.YELLOW,P.BROWN,P.PINK,P.ORANGE,P.GREY1,P.GREY2,P.LT_BLUE,P.LT_GREEN,P.GREY3)
		for char in text:
			pp = False
			conn.Sendall(char)
			#Keep track of cursor position
			if ord(char) in itertools.chain(range(32,128),range(160,256)): #Printable chars
				cc += 1
			elif char == chr(P.CRSR_RIGHT):
				cc += 1
			elif ord(char) in [P.CRSR_LEFT, P.DELETE]:
				cc -= 1
			elif char == chr(P.CRSR_UP):
				ll -= 1
			elif char == chr(P.CRSR_DOWN):
				ll += 1
			elif char == '\x0d':
				ll += 1
				cc = 0
				rvs = ''
			elif ord(char) == [P.HOME, P.CLEAR]:
				ll = 0
				page = 0
				cc = 0
			elif ord(char) in P.PALETTE:
				color = char
			elif char == chr(P.RVS_ON):
				rvs = chr(P.RVS_ON)
			elif char == chr(P.RVS_OFF):
				rvs = ''
			elif char == chr(P.TOLOWER):
				prompt = 'RETURN'
			elif char == chr(P.TOUPPER):
				prompt = 'return'
			if cc == 40:
				cc = 0
				ll += 1
			elif cc < 0:
				if ll!=lines*page:
					cc = 39
					ll -= 1
				else:
					cc = 0
			if ll < lines*page:
				ll = lines*page
			elif ll >= (lines*page)+(lines-1):
				if cc !=0:
					conn.Sendall('\r')
				conn.Sendall(KeyPrompt(prompt+' OR _'))
				k = conn.ReceiveKey(b'\r_')
				if conn.connected == False:
					conn.Sendall(TT.set_Window(0,24))
					return -1
				if k == b'_':
					conn.Sendall(TT.set_Window(0,24))
					return -1
				conn.Sendall(chr(P.DELETE)*13+rvs+color+TT.set_CRSR(cc,(22-lines)+ll-(lines*page)))
				page += 1
				pp = True
		if cc !=0:
			conn.Sendall('\r')
		if not pp:
			conn.Sendall(KeyPrompt(prompt))
			conn.ReceiveKey()
	return(0)

# Bidirectional scroll text display
# needs Turbo56K >= 0.7
def text_displayer(conn:Connection, text, lines, colors=default_style):
	#initialize line color list
	lcols = [P.PALETTE[colors.TxtColor]]*len(text)
	tcolor = lcols[0]

	#Display a whole text page
	def _page(start,l):
		nonlocal tcolor

		conn.Sendall(chr(P.CLEAR))
		tcolor = P.PALETTE[colors.TxtColor] if start == 0 else lcols[start-1]
		for i in range(start, start+min(lcount,len(text[start:]))):
			t = chr(tcolor) + text[i]
			conn.Sendall(t)
			tt = t.translate({ord(c):None for c in P.NONPRINTABLE})
			if len(tt) < 40 and t[-1]!='\r':
				conn.Sendall('\r')
			tcolor = lcols[i]
		return(i)

	if conn.QueryFeature(TT.SCROLL)< 0x80:
		#eliminate problematic control codes
		for i,t in enumerate(text):
			text[i] = t.translate({P.HOME:None,P.CLEAR:None,P.CRSR_LEFT:None,P.CRSR_UP:None})
		if isinstance(lines,tuple):
			lcount = lines[1]-lines[0]
		else:
			lcount = lines -1

		# Fill line color list
		for i,t in enumerate(text):
			tcolor = lastColor(t,tcolor)
			lcols[i] = tcolor

		# Render 1st page
		tcolor = P.PALETTE[colors.TxtColor]
		conn.Sendall(chr(tcolor))
		i = _page(0,lines)

		tline = 0
		bline = i+1
		if lcount < len(text):
			#scroll loop
			ldir = True	#Last scroll down?
			while conn.connected:
				k = conn.ReceiveKey(b'_'+bytes([P.CRSR_DOWN,P.CRSR_UP,P.F1,P.F7]))
				if k == b'_':
					break
				elif (k[0] == P.CRSR_UP) and (tline > 0):	#Scroll up
					tline -= 1
					bline -= 1
					if tline > 0:
						tcolor = lcols[tline-1]
					else:
						tcolor = P.PALETTE[colors.TxtColor]
					conn.Sendall(TT.scroll(-1)+chr(P.HOME)+chr(tcolor)+text[tline])
					ldir = False
				elif (k[0] == P.CRSR_DOWN) and (bline < len(text)-1):	#Scroll down
					tline += 1
					if bline > 0:
						tcolor = lcols[bline-1]
					else:
						tcolor = P.PALETTE[colors.TxtColor]
					conn.Sendall(TT.scroll(1))
					if ldir:
						conn.Sendall(TT.set_CRSR(0,lcount-1)+chr(tcolor)+text[bline])
					#lcols[bline] = lastColor(text[bline],tcolor)
					bline += 1
					ldir = True
				elif (k[0] == P.F1) and (tline > 0):	#Page up
					tline -= lcount
					if tline < 0:
						tline = 0
					bline = _page(tline,lcount)+1
					ldir = True
				elif (k[0] == P.F7) and (bline < len(text)-1):	#Page down
					bline += lcount
					if bline > len(text):
						bline = len(text)
					tline = bline-lcount
					_page(tline,lcount)
					ldir = True
				...
		else:
			conn.ReceiveKey(b'_')
		...

# Crop text to the desired length, adding ellipsis if needed
def crop(text, length):
	return text[:length-3] + '...' if len(text) > length else text


# Convert an int depicting a size in bytes to a rounded up to B/KB/MB/GB or TB (base 2) string
# https://stackoverflow.com/questions/12523586/python-format-size-application-converting-b-to-kb-mb-gb-tb
###########################################################################################################
def format_bytes(b:int):
	p = 2**10
	n = 0
	pl = {0 : '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
	while b > p:
		b /= p
		n += 1
	return str(round(b,1))+pl[n]+'B'