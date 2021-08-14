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

# Go back to previous/main menu
def MenuBack(conn):

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

#Text pagination
def More(conn, text, lines, colors=default_style):

	l = 0
	conn.Sendall(chr(P.PALETTE[colors.TxtColor]))
	tcolor = colors.TxtColor
	for t in text:
		conn.Sendall(t)
		tt = t.translate({ord(c):None for c in P.NONPRINTABLE})
		if len(tt) < 40 and t[-1]!='\r':
			conn.Sendall('\r')
		# Find last text color
		pos = -1
		for c in P.PALETTE:
			x = t.rfind(chr(c))
			if x > pos:
				pos = x
				tcolor = P.PALETTE.index(c)
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