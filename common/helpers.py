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
from common.style import bbsstyle, default_style


#Valid keys for menu entries
valid_keys = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890\\*;/'


#Menu alternating colors
menu_colors = [[P.LT_BLUE,P.GREY3],[P.CYAN,P.YELLOW]]

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

	l = 0
	conn.Sendall(chr(P.PALETTE[colors.TxtColor]))
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
	return(0)

# Bidirectional scroll text display
# needs Turbo56K >= 0.7
def text_displayer(conn:Connection, text, lines, colors=default_style):
	if conn.QueryFeature(TT.SCROLL)< 0x80:
		#initialize line color list
		lcols = [P.PALETTE[colors.TxtColor]]*len(text)
		#eliminate problematic control codes
		for i,t in enumerate(text):
			text[i] = t.translate({P.HOME:None,P.CLEAR:None,P.CRSR_LEFT:None,P.CRSR_UP:None})
		if isinstance(lines,tuple):
			lcount = lines[1]-lines[0]
		else:
			lcount = lines -1
		#first fill text window
		tcolor = P.PALETTE[colors.TxtColor]
		conn.Sendall(chr(tcolor))
		for i in range(min(lcount,len(text))):
			t = text[i]
			conn.Sendall(t)
			tt = t.translate({ord(c):None for c in P.NONPRINTABLE})
			if len(tt) < 40 and t[-1]!='\r':
				conn.Sendall('\r')
			# Find last text color
			tcolor = lastColor(t,tcolor)
			# pos = -1
			# for c in P.PALETTE:
			# 	x = t.rfind(chr(c))
			# 	if x > pos:
			# 		pos = x
			# 		tcolor = c
			# if i+1 < len(text):
			lcols[i] = tcolor

		tline = 0
		bline = i+1
		if lcount < len(text):
			#scroll loop
			ldir = True	#Last scroll down?
			while conn.connected:
				k = conn.ReceiveKey(b'_'+bytes([P.CRSR_DOWN,P.CRSR_UP]))
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
					lcols[bline] = lastColor(text[bline],tcolor)
					bline += 1
					ldir = True
				...
		else:
			conn.ReceiveKey(b'_')
		...

# Crop text to the desired length, adding ellipsis if needed
def crop(text, length):
	return text[:length-3] + '...' if len(text) > length else text