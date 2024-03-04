import unicodedata
import re
from common.classes import Encoder
from common.imgcvt import gfxmodes
import os
import codecs

#PETSCII constants

#--Control codes
STOP = 0x03
DISABLE_CBMSHIFT = 0x08
ENABLE_CBMSHIFT = 0x09
RETURN = 0x0D
TOLOWER = 0x0E
RVS_ON = 0x12
RUN = 0x83
SH_RETURN = 0x8D
TOUPPER = 0x8E
RVS_OFF = 0x92
#--Plus/4
FLASH_ON = 0x82
FLASH_OFF = 0x84
ESC = 0x1B

#--Special chars
POUND = 0x5C
LEFT_ARROW = 0x5F
PI = 0x7E

#--Editor
CRSR_LEFT = 0x9D
CRSR_RIGHT = 0x1D
CRSR_UP = 0x91
CRSR_DOWN = 0x11
CLEAR = 0x93
INSERT = 0x94
HOME = 0x13
DELETE = 0x14

#--Colors
BLACK = 0x90
WHITE = 0x05
RED = 0x1C
CYAN = 0x9F
PURPLE = 0x9C
GREEN = 0x1E
BLUE = 0x1F
YELLOW = 0x9E
ORANGE = 0x81
BROWN = 0x95
PINK = 0x96
GREY1 = 0x97
GREY2 = 0x98
LT_GREEN = 0x99
LT_BLUE = 0x9A
GREY3 = 0x9B

#--F Keys
F1 = 0x85
F3 = 0x86
F5 = 0x87
F7 = 0x88
F2 = 0x89
F4 = 0x8A
F6 = 0x8B
F8 = 0x8C
#--Plus/4
HELP = 0x8C


#--GFX
HLINE = 0x60
CROSS = 0x7B
VLINE = 0x7D
LEFT_HASH = 0x7C
HASH = 0xA6
BOTTOM_HASH = 0xA8
COMM_B = 0xBF
COMM_U = 0xB8
COMM_O = 0xB9
COMM_J = 0xB5
COMM_L = 0xB6
CHECKMARK = 0xBA
UL_CORNER = 0xB0     # Box corners
UR_CORNER = 0xAE
LL_CORNER = 0xAD
LR_CORNER = 0xBD
V_RIGHT = 0xAB       # Box borders
V_LEFT  = 0xB3
H_UP    = 0xB1
H_DOWN  = 0xB2
UL_QUAD = 0xBE       # Semigraphics
UR_QUAD = 0xBC
LL_QUAD = 0xBB
LR_QUAD = 0xAC
L_HALF  = 0xA1
B_HALF  = 0xA2
UL_LR_QUAD = COMM_B
L_NARROW = 0xB5
R_NARROW = 0xB6
U_NARROW = 0xB8
B_NARROW = 0xB9

#-- Chars used by the BBS
SPINNER = COMM_B    # Character to use while waiting
BACK = LEFT_ARROW

# Color code to palette index dictionary
PALETTE = {BLACK:0,WHITE:1,RED:2,CYAN:3,PURPLE:4,GREEN:5,BLUE:6,YELLOW:7,ORANGE:8,BROWN:9,PINK:10,GREY1:11,GREY2:12,LT_GREEN:13,LT_BLUE:14,GREY3:15}
PALETTE264 = {BLACK:0x00,WHITE:0x71,RED:0x32,CYAN:0x63,PURPLE:0x34,GREEN:0x45,BLUE:0x26,YELLOW:0x67,
              ORANGE:0x48,BROWN:0x29,PINK:0x52,GREY1:0x31,GREY2:0x41,LT_GREEN:0x65,LT_BLUE:0x46,GREY3:0x51}

#--Non printable characters grouped
NONPRINTABLE = [chr(i) for i in range(0,13)]+[chr(i) for i in range(14,32)]+[chr(i) for i in range(128,160)]

###########
# TML tags
###########
t_mono = 	{'PET64':{'CLR':chr(CLEAR),'HOME':chr(HOME),'RVSON':chr(RVS_ON),'RVSOFF':chr(RVS_OFF),'BR':'\r',
            'CBMSHIFT-D':chr(DISABLE_CBMSHIFT),'CBMSHIFT-E':chr(ENABLE_CBMSHIFT),'UPPER':chr(TOUPPER),'LOWER':chr(TOLOWER),
            'BLACK':chr(BLACK),'WHITE':chr(WHITE),'RED':chr(RED),'CYAN':chr(CYAN),'PURPLE':chr(PURPLE),'GREEN':chr(GREEN),'BLUE':chr(BLUE),'YELLOW':chr(YELLOW),
            'ORANGE':chr(ORANGE),'BROWN':chr(BROWN),'PINK':chr(PINK),'GREY1':chr(GREY1),'GREY2':chr(GREY2),'LTGREEN':chr(LT_GREEN),'LTBLUE':chr(LT_BLUE),'GREY3':chr(GREY3),
            'LTGREY':chr(GREY3),'MGREY':chr(GREY2),'GREY':chr(GREY2),'DGREY':chr(GREY1)},
            'PET264':{'FLASHON':chr(FLASH_ON),'FLASHOFF':chr(FLASH_OFF)}}
t_multi =	{'PET64':{'CRSRL':chr(CRSR_LEFT),'CRSRU':chr(CRSR_UP),'CRSRR':chr(CRSR_RIGHT),'CRSRD':chr(CRSR_DOWN),'DEL':chr(DELETE),'INS':chr(INSERT),
            'POUND':chr(POUND),'PI':chr(PI),'HASH':chr(HASH),'HLINE':chr(HLINE),'VLINE':chr(VLINE),'CROSS':chr(CROSS),'LEFT-HASH':chr(LEFT_HASH), 'CHECKMARK': chr(CHECKMARK),
            'BOTTOM-HASH':chr(BOTTOM_HASH),'LARROW':'_','UARROW':'^','CBM-U':chr(COMM_U),'CBM-O':chr(COMM_O),'CBM-B':chr(COMM_B),'CBM-J':chr(COMM_J),'CBM-L':chr(COMM_L),
            'UL-CORNER':chr(UL_CORNER),'UR-CORNER':chr(UR_CORNER),'LL-CORNER':chr(LL_CORNER),'LR-CORNER':chr(LR_CORNER),
            'V-RIGHT':chr(V_RIGHT),'V-LEFT':chr(V_LEFT),'H-UP':chr(H_UP),'H-DOWN':chr(H_DOWN),
            'UL-QUAD':chr(UL_QUAD),'UR-QUAD':chr(UR_QUAD),'LL-QUAD':chr(LL_QUAD),'LR-QUAD':chr(LR_QUAD),'UL-LR-QUAD':chr(UL_LR_QUAD),
            'L-HALF':chr(L_HALF),'B-HALF':chr(B_HALF),'L-NARROW':chr(L_NARROW),'R-NARROW':chr(R_NARROW),'U-NARROW':chr(U_NARROW),'B-NARROW':chr(B_NARROW),
            'SPINNER':chr(SPINNER),'BACK':chr(BACK)}}

t_mono['PET264'].update(t_mono['PET64'])
t_multi['PET264'] = t_multi['PET64']

# Multiple replace
# https://stackoverflow.com/questions/6116978/how-to-replace-multiple-substrings-of-a-string
Urep = {'\u00d7':'x','\u00f7':'/','\u2014':'-','\u2013':'-','\u2019':"'",'\u2018':"'",'\u201c':'"','\u201d':'"','\u2022':'*'}
Urep = dict((re.escape(k), v) for k, v in Urep.items())

######### Petscii ASCII codec error handler #########
# Replace unknowns with a space
def pethandler(e):
    char = b''
    if type(e) == UnicodeEncodeError:
        if e.object[e.start] in '¿¡':
            char = b' '
    elif type(e) == UnicodeDecodeError:
        ...
    return (char,e.end)


######### Petscii encoder subclass #########
class PETencoder(Encoder):
    def __init__(self, name:str) -> None:
        super().__init__(name)
        self.encode = toPETSCII	#	Function to encode from ASCII/Unicode
        self.decode = toASCII	#	Function to decode to ASCII/Unicode
        self.non_printable = NONPRINTABLE	#	List of non printable characters
        self.nl	= '\r'			#	New line string/character
        self.bs = chr(DELETE)	#	Backspace string/character
        self.back = chr(BACK)

    def check_fit(self, filename):
        size = os.stat(filename).st_size-2
        with open(filename,'rb') as f:
            la = f.read(2)
            la = la[0]|(la[1]<<8)
        if la < self.bbuffer or la > self.tbuffer:
            return False
        elif la + size > self.tbuffer:
            return False
        return True

####################################################
# Convert ASCII/unicode text to PETSCII
# full = True for aditional glyph visual conversion
#        False for simple upper-lower case swapping
####################################################
def toPETSCII(text:str,full=True):
    if full:
        pattern = re.compile("|".join(Urep.keys()))
        text = pattern.sub(lambda m: Urep[re.escape(m.group(0))], text)
        text = (unicodedata.normalize('NFKD',text).encode('ascii','spaces')).decode('ascii')
        text = text.replace('|', chr(VLINE))
        text = text.replace('_', chr(164))
    text = ''.join(c.lower() if c.isupper() else c.upper() for c in text)
    return(text)

###########################
# Convert PETSCII to ASCII
###########################
def toASCII(text):
    text = ''.join(chr(ord(c)-96) if ord(c)>192 else c for c in text)
    text = ''.join(c.lower() if c.isupper() else c.upper() for c in text)
    return(text)

###################################
# Register with the encoder module
###################################
def _Register():
    codecs.register_error('spaces',pethandler)  # Register encoder error handler. This might be more useful if global 
    e0 = PETencoder('PET64')
    e0.tml_mono  = t_mono['PET64']
    e0.tml_multi = t_multi['PET64']
    e0.bbuffer = 0x02ed #Bottom of the buffer
    e0.tbuffer = 0xbfff #Top of the buffer
    #e0.encode = toPETSCII
    #e0.decode = toASCII
    e0.palette = PALETTE
    e0.colors = {'BLACK':0, 'WHITE':1,  'RED':2,    'CYAN':3,   'PURPLE':4,'GREEN':5,   'BLUE':6,   'YELLOW':7,
                 'ORANGE':8,'BROWN':9,  'PINK':10,  'GREY1':11, 'GREY2':12,'LIGHT_GREEN':13, 'LIGHT_BLUE':14, 'GREY3':15,
                 'LIGHT_GREY':15,'DARK_GREY':11, 'MEDIUM_GREY':12, 'GREY':12}
    #e0.non_printable = NONPRINTABLE
    #e0.nl = '\r' # New line string
    #e0.bs = chr(DELETE)
    e0.def_gfxmode = gfxmodes.C64MULTI
    e0.gfxmodes = (gfxmodes.C64HI,gfxmodes.C64MULTI)
    e0.ctrlkeys = {'CRSRU':CRSR_UP,'CRSRD':CRSR_DOWN,'CRSRL':CRSR_LEFT,'CRSRR':CRSR_RIGHT,'F1':F1,'F2':F2,'F3':F3,'F4':F4,'F5':F5,'F6':F6,'F7':F7,'F8':F8,
                   'HOME':HOME,'CLEAR':CLEAR,'DELETE':DELETE,'INSERT':INSERT,'RVSON':RVS_ON,'RVSOFF':RVS_OFF,'UPPER':TOUPPER,'LOWER':TOLOWER}

    e1 = PETencoder('PET264')
    e1.tml_mono  = t_mono['PET264']
    e1.tml_multi = t_multi['PET264']
    e1.bbuffer = 0x0800 #Bottom of the buffer
    e1.tbuffer = 0x6fff #Top of the buffer
    #e1.encode = toPETSCII
    #e1.decode = toASCII
    e1.palette = PALETTE264
    e1.colors = {'BLACK':0,    'WHITE':0x71,  'RED':0x32  ,'CYAN':0x63 ,'PURPLE':0x34,'GREEN':0x45 ,'BLUE':0x26 ,'YELLOW':0x67,
                 'ORANGE':0x48,'BROWN':0x29,  'PINK':0x52 ,'GREY1':0x31,'GREY2':0x41 ,'LIGHT_GREEN':0x65,'LIGHT_BLUE':0x46,'GREY3':0x51,
                 'LIGHT_GREY':0x51 ,'DARK_GREY':0x31,  'MEDIUM_GREY':0x41,'GREY':0x41,
                 'DARK_GREEN':0x2F,'MAGENTA':0x4B,'DARK_RED':0x12}
    #e1.non_printable = NONPRINTABLE
    #e1.nl = '\r' # New line string
    #e1.bs = chr(DELETE)
    e1.def_gfxmode = gfxmodes.P4HI
    e1.gfxmodes = (gfxmodes.P4HI,gfxmodes.P4MULTI)
    e1.ctrlkeys = {'CRSRU':CRSR_UP,'CRSRD':CRSR_DOWN,'CRSRL':CRSR_LEFT,'CRSRR':CRSR_RIGHT,'F1':F1,'F2':F2,'F3':F3,'F4':F4,'F5':F5,'F6':F6,'F7':F7,'HELP':HELP,
                   'HOME':HOME,'CLEAR':CLEAR,'DELETE':DELETE,'INSERT':INSERT,'RVSON':RVS_ON,'RVSOFF':RVS_OFF,'UPPER':TOUPPER,'LOWER':TOLOWER, 'ESC':ESC}
    return [e0,e1]  #Each encoder module can return more than one encoder object. For example here it could also return PET128.