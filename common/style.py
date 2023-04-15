########### Style ############
# Quite lean for now
from common.connection import Connection
from common import petscii as P
from common import turbo56k as TT
from common import helpers as H

class bbsstyle:
	def __init__(self):
		pass

default_style = bbsstyle()

# Default colors (in c64 palette index)
default_style.BgColor		= P.PALETTE.index(P.BLACK)		#Background color
default_style.BoColor		= P.PALETTE.index(P.BLACK)		#Border color
default_style.TxtColor		= P.PALETTE.index(P.GREY3)		#Main text color
default_style.HlColor		= P.PALETTE.index(P.WHITE)		#Highlight text color
### Menu specific colors ###
default_style.OoddColor		= P.PALETTE.index(P.LT_BLUE)	#Odd option key color
default_style.ToddColor		= P.PALETTE.index(P.GREY3)		#Odd option text color
default_style.OevenColor	= P.PALETTE.index(P.CYAN)		#Even option key color
default_style.TevenColor	= P.PALETTE.index(P.YELLOW)		#Even option text color
default_style.MenuTColor1	= P.PALETTE.index(P.CYAN)		#Menu title border color 1
default_style.MenuTColor2	= P.PALETTE.index(P.LT_GREEN)	#Menu title border color 2
default_style.SBorderColor1	= P.PALETTE.index(P.LT_GREEN)	#Section border color 1
default_style.SBorderColor2	= P.PALETTE.index(P.GREEN)		#Section border color 1
### [Prompt] ###
default_style.PbColor		= P.PALETTE.index(P.YELLOW)		#Key prompt brackets color
default_style.PtColor		= P.PALETTE.index(P.LT_BLUE)	#Key prompt text color

def RenderMenuTitle(conn:Connection,title):
	if type(title) == tuple:
		title = title[0]
	# Clear screen
	#conn.Sendall(chr(P.CLEAR))
	# Lower/uppercase charset
	#conn.Sendall(chr(P.TOLOWER))
	tml = '<CLR><LOWER>'
	# Send menu title
	if conn.QueryFeature(TT.LINE_FILL) < 0x80:
		tml += '''<LTGREEN><LFILL row=0 code=64><LFILL row=2 code=64><RVSON><CYAN><CBM-U><RVSOFF><LET _R=_I x=0><WHILE c='_I<19'><CRSRR><HLINE><INC></WHILE><LTGREEN><RVSON><CBM-U>'''
	else:
		tml += '''<RVSON><CYAN><CBM-U><RVSOFF><LET _R=_I x=0><WHILE c='_I<19'><LTGREEN><HLINE><CYAN><HLINE><INC></WHILE><LTGREEN><RVSON><CBM-U>'''
	tml += f''' <RVSOFF><WHITE> {(conn.bbs.name[:19]+" - "+ title+(" "*33)[:37]+"  ")[:36]} <RVSON><CYAN> '''
	if conn.QueryFeature(TT.LINE_FILL) < 0x80:
		tml += '''<RVSON><CYAN><CBM-O><RVSOFF><LET _R=_I x=0><WHILE c='_I<19'><CRSRR><HLINE><INC></WHILE><LTGREEN><RVSON><CBM-O><RVSOFF>'''
	else:
		tml += '''<RVSON><CYAN><CBM-U><RVSOFF><LET _R=_I x=0><WHILE c='_I<19'><LTGREEN><HLINE><CYAN><HLINE><INC></WHILE><LTGREEN><RVSON><CBM-O><RVSOFF>'''
	conn.SendTML(tml)

# Returns '[text]' prompt string in the selected style
def KeyPrompt(text,style=default_style):
	return(chr(P.PALETTE[style.PbColor])+'['+chr(P.PALETTE[style.PtColor])+P.toPETSCII(text,False)+chr(P.PALETTE[style.PbColor])+']')

# Renders a menu option in the selected style  
def KeyLabel(conn:Connection, key, label, toggle, style=default_style):
	c1 = style.OevenColor if toggle else style.OoddColor
	c2 = style.TevenColor if toggle else style.ToddColor
	tml = ''
	if key >= '\r':
		if key == '_':		# FIXME: Workaround for PETSCII left arrow character
			key = '<LARROW>'
		tml += f'<INK c={c1}><RVSON><CHR c=181>{key.lower()}<CHR c=182><RVSOFF>'
		#conn.Sendall(chr(P.PALETTE[c1])+chr(P.RVS_ON)+chr(181)+key+chr(182)+chr(P.RVS_OFF))
	tml += f'<INK c={c2}>{label}'
	#conn.Sendall(chr(P.PALETTE[c2])+P.toPETSCII(label))
	conn.SendTML(tml)
	#if key < '\r':
	#	conn.Sendall('  ')
	return not toggle

# Render 'file' dialog background
def RenderDialog(conn:Connection,height,title=None):
	conn.Sendall(chr(P.CLEAR)+chr(P.GREY3)+chr(P.RVS_ON))
	if conn.QueryFeature(TT.LINE_FILL) < 0x80:
		conn.Sendall(chr(TT.CMDON))
		for y in range(0,height):
			conn.Sendall(chr(TT.LINE_FILL)+chr(y)+chr(160))
		conn.Sendall(chr(TT.CMDOFF)+chr(P.GREY1)+TT.Fill_Line(height,226)+chr(P.GREY3))
	else:
		conn.Sendall((' '*(40*height))+chr(P.GREY1)+(chr(162)*40)+chr(P.HOME)+chr(P.GREY3))
	if title != None:
		conn.Sendall(H.crop(conn.encoder.encode(title),38).center(40,chr(P.HLINE))+'\r')

################################################################
# TML tags
t_mono = {	'MTITLE':(lambda c,t:RenderMenuTitle(c,t),[('c','_C'),('t','')]),
	  		'KPROMPT':(KeyPrompt,[('_R','_C'),('t','RETURN')]),
			'DIALOG':(lambda c,h,t:RenderDialog(c,h,t),[('c','_C'),('h',4),('t','')])}
