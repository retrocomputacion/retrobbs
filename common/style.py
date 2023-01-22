########### Style ############
# Quite lean for now
from common.connection import Connection
from common import petscii as P
from common import turbo56k as TT

class bbsstyle:
	def __init__(self):
		pass

default_style = bbsstyle()

	# Default colors (in c64 palette index)
default_style.BgColor		= P.PALETTE.index(P.BLACK)		#Background color
default_style.BoColor		= P.PALETTE.index(P.BLACK)		#Border color
default_style.TxtColor		= P.PALETTE.index(P.GREY3)		#Main text color
default_style.HlColor		= P.PALETTE.index(P.WHITE)		#Highlight text color

default_style.OoddColor		= P.PALETTE.index(P.LT_BLUE)	#Odd option key color
default_style.ToddColor		= P.PALETTE.index(P.GREY3)		#Odd option text color
default_style.OevenColor	= P.PALETTE.index(P.CYAN)		#Even option key color
default_style.TevenColor	= P.PALETTE.index(P.YELLOW)		#Even option text color

	### [Prompt] ###
default_style.PbColor		= P.PALETTE.index(P.YELLOW)		#Key prompt brackets color
default_style.PtColor		= P.PALETTE.index(P.LT_BLUE)	#Key prompt text color


def RenderMenuTitle(conn:Connection,title):
	if type(title) == tuple:
		title = title[0]
	# Clear screen
	conn.Sendall(chr(P.CLEAR))
	# Lower/uppercase charset
	conn.Sendall(chr(P.TOLOWER))
	# Send menu title
	conn.Sendall(chr(P.LT_GREEN)+chr(TT.CMDON)+chr(TT.LINE_FILL)+chr(0)+chr(64)+chr(TT.LINE_FILL)+chr(2)+chr(64)+chr(TT.CMDOFF))
	conn.Sendall(chr(P.RVS_ON)+chr(P.CYAN)+chr(P.COMM_U)+chr(P.RVS_OFF)+chr(P.CYAN)+(chr(P.CRSR_RIGHT)+chr(P.HLINE))*19+chr(P.LT_GREEN)+chr(P.RVS_ON)+chr(P.COMM_U))
	conn.Sendall(" "+chr(P.RVS_OFF)+chr(P.WHITE)+" "+(P.toPETSCII(conn.bbs.name[:19])+" - "+P.toPETSCII(title)+(" "*33)[:37]+"  ")[:36]+" "+chr(P.RVS_ON)+chr(P.CYAN)+" ")
	conn.Sendall(chr(P.RVS_ON)+chr(P.CYAN)+chr(P.COMM_O)+chr(P.RVS_OFF)+chr(P.CYAN)+(chr(P.CRSR_RIGHT)+chr(P.HLINE))*19+chr(P.LT_GREEN)+chr(P.RVS_ON)+chr(P.COMM_O)+chr(P.RVS_OFF))
	#conn.Sendall(chr(P.RVS_ON)+chr(P.CYAN)+chr(P.COMM_O)+chr(P.RVS_OFF)+(chr(P.LT_GREEN)+chr(P.HLINE)+chr(P.CYAN)+chr(P.HLINE))*19+chr(P.LT_GREEN)+chr(P.RVS_ON)+chr(P.COMM_O)+chr(P.RVS_OFF))

# Returns '[text]' prompt string in the selected style
def KeyPrompt(text,style=default_style):
	return(chr(P.PALETTE[style.PbColor])+'['+chr(P.PALETTE[style.PtColor])+P.toPETSCII(text,False)+chr(P.PALETTE[style.PbColor])+']')

# Renders a menu option in the selected style  
def KeyLabel(conn:Connection, key, label, toggle, style=default_style):
	c1 = style.OevenColor if toggle else style.OoddColor
	c2 = style.TevenColor if toggle else style.ToddColor
	if key >= '\r':
		conn.Sendall(chr(P.PALETTE[c1])+chr(P.RVS_ON)+chr(181)+key+chr(182)+chr(P.RVS_OFF))
	conn.Sendall(chr(P.PALETTE[c2])+P.toPETSCII(label))
	#if key < '\r':
	#	conn.Sendall('  ')
	return not toggle
