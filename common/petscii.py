import unicodedata
import re

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
CHECKMARK = 0xBA

PALETTE = (BLACK,WHITE,RED,CYAN,PURPLE,GREEN,BLUE,YELLOW,ORANGE,BROWN,PINK,GREY1,GREY2,LT_GREEN,LT_BLUE,GREY3)

#--Non printable characters grouped
NONPRINTABLE = [chr(i) for i in range(0,13)]+[chr(i) for i in range(14,32)]+[chr(i) for i in range(128,160)]


MAPPING = { '{WHITE}':0x05,'{CRSRD}':0x11,'{RVSON}':0x12,'{HOME}':0x13,
            '{DEL}':0x14,'{RED}':0x1c,'{CRSRR}':0x1d,'{GREEN}':0x1e,
            '{BLUE}':0x1f,'{POUND}':0x5c,'{LARROW}':0x5f,'{SHIFT*}':0x60,
            '{ORANGE}':0x81,'{BLACK}':0x90,'{CRSRU}':0x91,'{RVSOFF}':0x92,
            '{CLR}':0x93,'{INS}':0x94,'{BROWN}':0x95,'{PINK}':0x96,
            '{GREY1}':0x97,'{GREY2}':0x98,'{LTGREEN}':0x99,'{LTBLUE}':0x9a,
            '{GREY3}':0x9b,'{PURPLE}':0x9c,'{CRSRL}':0x9d,'{YELLOW}':0x9e,
            '{CYAN}':0x9f}

# Multiple replace
# https://stackoverflow.com/questions/6116978/how-to-replace-multiple-substrings-of-a-string
Urep = {'\u00d7':'x','\u00f7':'/','\u2014':'-','\u2013':'-','\u2019':"'",'\u2018':"'",'\u201c':'"','\u201d':'"'}
Urep = dict((re.escape(k), v) for k, v in Urep.items()) 

# Convert ASCII/unicode text to PETSCII
# full = True for aditional glyph visual conversion
#        False for simple upper-lower case swapping
def toPETSCII(text:str,full=True):
    if full:
        pattern = re.compile("|".join(Urep.keys()))
        text = pattern.sub(lambda m: Urep[re.escape(m.group(0))], text)
        text = (unicodedata.normalize('NFKD',text).encode('ascii','ignore')).decode('ascii')
        text = text.replace('|', chr(VLINE))
        text = text.replace('_', chr(164))
    text = ''.join(c.lower() if c.isupper() else c.upper() for c in text)
    return(text)

def toASCII(text):
    text = ''.join(chr(ord(c)-96) if ord(c)>192 else c for c in text)
    text = ''.join(c.lower() if c.isupper() else c.upper() for c in text)
    return(text)