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
default_style.BgColor		= 0		#Background color
default_style.BoColor		= 0		#Border color
default_style.TxtColor		= 15	#Main text color
default_style.HlColor		= 1		#Highlight text color

default_style.OoddColor		= 14	#Odd option key color
default_style.ToddColor		= 15	#Odd option text color
default_style.OevenColor	= 3		#Even option key color
default_style.TevenColor	= 7		#Even option text color

	### [Prompt] ###
default_style.PbColor		= 7		#Key prompt brackets color
default_style.PtColor		= 14	#Key prompt text color


def RenderMenuTitle(conn,title):

	# Clear screen
	conn.Sendall(chr(P.CLEAR))
	# Lower/uppercase charset
	conn.Sendall(chr(P.TOLOWER))
	# Send menu title
	conn.Sendall(chr(P.LT_GREEN)+chr(TT.CMDON)+chr(TT.LINE_FILL)+chr(0)+chr(64)+chr(TT.LINE_FILL)+chr(2)+chr(64)+chr(TT.CMDOFF))
	conn.Sendall(chr(P.RVS_ON)+chr(P.CYAN)+chr(P.COMM_U)+chr(P.RVS_OFF)+chr(P.CYAN)+(chr(P.CRSR_RIGHT)+chr(P.HLINE))*19+chr(P.LT_GREEN)+chr(P.RVS_ON)+chr(P.COMM_U))
	conn.Sendall(" "+chr(P.RVS_OFF)+chr(P.WHITE)+" "+(conn.bbs.name[:19]+" - "+title+(" "*33)[:37]+"  ")[:36]+" "+chr(P.RVS_ON)+chr(P.CYAN)+" ")
	conn.Sendall(chr(P.RVS_ON)+chr(P.CYAN)+chr(P.COMM_O)+chr(P.RVS_OFF)+chr(P.CYAN)+(chr(P.CRSR_RIGHT)+chr(P.HLINE))*19+chr(P.LT_GREEN)+chr(P.RVS_ON)+chr(P.COMM_O)+chr(P.RVS_OFF))
	#conn.Sendall(chr(P.RVS_ON)+chr(P.CYAN)+chr(P.COMM_O)+chr(P.RVS_OFF)+(chr(P.LT_GREEN)+chr(P.HLINE)+chr(P.CYAN)+chr(P.HLINE))*19+chr(P.LT_GREEN)+chr(P.RVS_ON)+chr(P.COMM_O)+chr(P.RVS_OFF))

def KeyPrompt(text,style=default_style):
	return(chr(P.PALETTE[style.PbColor])+'['+chr(P.PALETTE[style.PtColor])+text+chr(P.PALETTE[style.PbColor])+']')
