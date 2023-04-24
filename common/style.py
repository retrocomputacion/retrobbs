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
# TML: True to return TML sequence
# TML output will become the default behaviour in the future
def KeyPrompt(text,style=default_style, TML=False):
	if TML:
		return(f'<INK c={style.PbColor}>[<INK c={style.PtColor}>{text}<INK c={style.PbColor}>]')
	else:
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
	tml += f'<INK c={c2}>{label}'
	conn.SendTML(tml)
	return not toggle

# Render 'file' dialog background
def RenderDialog(conn:Connection,height,title=None):
	conn.SendTML('<CLR><GREY3><RVSON>')
	if conn.QueryFeature(TT.LINE_FILL) < 0x80:
		conn.SendTML('<LFILL row=0 code=192>')
		conn.Sendall(chr(TT.CMDON))
		for y in range(1,height):
			conn.Sendall(chr(TT.LINE_FILL)+chr(y)+chr(160))
		conn.Sendall(chr(TT.CMDOFF))
		conn.SendTML(f'<GREY1><LFILL row={height} code=226><GREY3>')
	else:
		conn.SendTML(f'<HLINE n=40><SPC n={40*height-1}><GREY1>{chr(162)*40}<HOME><GREY3>')
	if title != None:
		ctt = H.crop(title,38)
		conn.SendTML(f'<AT x={1+(38-len(ctt))/2} y=0>{ctt}<BR>')

################################################################
# TML tags
t_mono = {	'MTITLE':(lambda c,t:RenderMenuTitle(c,t),[('c','_C'),('t','')]),
	  		'KPROMPT':(KeyPrompt,[('_R','_C'),('t','RETURN')]),
			'DIALOG':(lambda c,h,t:RenderDialog(c,h,t),[('c','_C'),('h',4),('t','')])}
