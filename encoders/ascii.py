import unicodedata
import re
from common.classes import Encoder
import codecs
from copy import deepcopy

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
t_mono = 	{'BR':'\r\n','AT':'','CLR':'\x0c','BACK':'_'}
t_multi =	{'DEL':'\x08 \x08',
            'POUND':chr(POUND),'PI':chr(PI),'HASH':chr(HASH),'HLINE':chr(HLINE),'VLINE':chr(VLINE),'CROSS':chr(CROSS), 'CHECKMARK': chr(CHECKMARK),
            'LARROW':'_','UARROW':'^','CBM-U':'','CBM-O':'','CBM-J':'','CBM-L':'',
            'UR-CORNER':'+','UL-CORNER':'+','LR-CORNER':'+','LL-CORNER':'+','V-LEFT':'+','V-RIGHT':'+','H-UP':'+','H-DOWN':'+'}

Urep = {'\u00d7':'x','\u00f7':'/','\u2014':'-','\u2013':'-','\u2019':"'",'\u2018':"'",'\u201c':'"','\u201d':'"','\u2022':'*'}
Urep = dict((re.escape(k), v) for k, v in Urep.items())

def toASCII(text:str, full=True):
    pattern = re.compile("|".join(Urep.keys()))
    text = pattern.sub(lambda m: Urep[re.escape(m.group(0))], text)
    text = (unicodedata.normalize('NFKD',text).encode('cp437','asciispc')).decode('latin1')
    return text

# Replace unknowns with a space
def asciihandler(e):
    char = b''
    if type(e) == UnicodeEncodeError:
        if e.object[e.start] in '¿¡':
            char = b' '
    elif type(e) == UnicodeDecodeError:
        ...
    return (char,e.end)

######### VT52 encoder subclass #########
class ASCIIencoder(Encoder):
    def __init__(self, name:str) -> None:
        super().__init__(name)
        self.minT56Kver = 0
        self.encode = toASCII   #	Function to encode from ASCII/Unicode
        self.decode = lambda t:t.encode('latin1').decode('cp437')	#	Function to decode from CP437 to Unicode
        self.non_printable = NONPRINTABLE	#	List of non printable characters
        self.nl	= '\r'			#	New line string/character
        self.nl_out = '\r\n'      #   New line string/character (out)
        self.bs = chr(DELETE)	#	Backspace string/character
        self.txt_geo = (32,24)  #   Text screen dimensions
        self.ellipsis = '...'   # Ellipsis representation
        self.clients = {b'_default_':'ASCII', b'ASC':'Extended ASCII (CP437)'}
        self.back = '_'
        self.bbuffer = 0x0000   # Bottom of the buffer
        self.tbuffer = 0x0000   # Top of the buffer
        self.palette = {}
        self.gfxmodes = []
        self.def_gfxmode = None
        self.tml_mono  = t_mono
        self.tml_multi = t_multi
        self.ctrlkeys = {'DELETE':chr(DELETE)}

    def setup(self, conn, id):
        if id == b'ASC':
            _copy = deepcopy(self)
            conn.SendTML('Screen columns? (40): ')
            cols = conn.ReceiveInt(32,80,40)
            conn.SendTML('<BR>Screen lines? (25): ')
            lines = conn.ReceiveInt(16,25,25)
            _copy.txt_geo = (cols,lines)
            return _copy
        else:
            return None


###################################
# Register with the encoder module
###################################
def _Register():
    codecs.register_error('asciispc',asciihandler)  # Register encoder error handler. 
    e0 = ASCIIencoder('ASCII')
    e0.minT56Kver = 0
    # e0.colors  = {'BLACK':0, 'WHITE':0,  'RED':0,    'CYAN':0,   'PURPLE':0,'GREEN':0,   'BLUE':0,   'YELLOW':0,
    #              'ORANGE':0,'BROWN':0,  'PINK':0,  'GREY1':0, 'GREY2':0,'LIGHT_GREEN':0, 'LIGHT_BLUE':0, 'GREY3':0,
    #              'LIGHT_GREY':0,'DARK_GREY':0, 'MEDIUM_GREY':0, 'GREY':0}
    return [e0]  #Each encoder module can return more than one encoder object. For example here it could also return ANSI.