import unicodedata
import re
from common.classes import Encoder
import os

#Plain ASCII CP437 encoder

#--Control codes
STOP = 0x03
RETURN = 0x0D
ESC = 0x1B

#--Special chars
POUND = 0x9C
LEFT_ARROW = 0x5F
PI = 0xE3

#--Editor
DELETE = 0x08

#--GFX
HLINE = 0xC4
CROSS = 0xC5
VLINE = 0xB3
HASH  = 0xB2
COMM_U = 0xDF
COMM_O = 0xDC
COMM_J = 0xDD
COMM_L = 0xDE
CHECKMARK = 0xFB

UL_CORNER = 0xDA     # Box corners
UR_CORNER = 0xBF
LL_CORNER = 0xC0
LR_CORNER = 0xD9
L_HALF  = 0xDD      # Semigraphics
R_HALF  = 0xDE
B_HALF  = 0xDF
T_HALF  = 0xDC

#--Non printable characters grouped
NONPRINTABLE = [chr(i) for i in range(0,10)]+[11]+[chr(i) for i in range(14,32)]+[127]

###########
# TML tags
###########
t_mono = 	{'BR':'\r\n','AT':'','CLR':'\r\n'*25}
t_multi =	{'DEL':chr(DELETE),
            'POUND':chr(POUND),'PI':chr(PI),'HASH':chr(HASH),'HLINE':chr(HLINE),'VLINE':chr(VLINE),'CROSS':chr(CROSS), 'CHECKMARK': chr(CHECKMARK),
            'LARROW':'_','UARROW':'^','CBM-U':chr(COMM_U),'CBM-O':chr(COMM_O),'CBM-J':chr(COMM_J),'CBM-L':chr(COMM_L)}

def toASCII(text:str, full=True):
    return text.encode('cp437').decode('latin1')

###################################
# Register with the encoder module
###################################
def _Register():
    e0 = Encoder('ASCII')
    e0.minT56Kver = 0
    e0.clients = {b'ASC':'Extended ASCII'}
    e0.encode = toASCII #lambda t,f:t.encode('cp437').decode('latin1')	#	Function to encode from Unicode to CP437
    e0.decode = lambda t:t.encode('latin1').decode('cp437')	#	Function to decode from CP437 to Unicode
    e0.non_printable = NONPRINTABLE	#	List of non printable characters
    e0.nl	= '\r'			#	New line string/character
    e0.nl_out = '\r\n'
    e0.bs = chr(DELETE)	    #	Backspace string/character
    e0.tml_mono  = t_mono
    e0.tml_multi = t_multi
    e0.bbuffer = 0x0000 #Bottom of the buffer
    e0.tbuffer = 0x0000 #Top of the buffer
    e0.palette = {}
    e0.colors  = {'BLACK':0, 'WHITE':0,  'RED':0,    'CYAN':0,   'PURPLE':0,'GREEN':0,   'BLUE':0,   'YELLOW':0,
                 'ORANGE':0,'BROWN':0,  'PINK':0,  'GREY1':0, 'GREY2':0,'LIGHT_GREEN':0, 'LIGHT_BLUE':0, 'GREY3':0,
                 'LIGHT_GREY':0,'DARK_GREY':0, 'MEDIUM_GREY':0, 'GREY':0}
    e0.def_gfxmode = None
    e0.gfxmodes = None
    e0.ctrlkeys = {'DELETE':DELETE}
    e0.features = { 'color':       False,  # Encoder supports color
                    'charsets':    1,      # Number if character sets supported
                    'reverse':     False,  # Encoder supports reverse video
                    'blink':       False,  # Encoder supports blink/flash text
                    'underline':   False,  # Encoder supports underlined text
                    'cursor':      False   # Encoder supports cursor movement/set. Including home position and screen clear
                    }
    return [e0]  #Each encoder module can return more than one encoder object. For example here it could also return ANSI.