import unicodedata
import re
from common.classes import Encoder
import os
from copy import deepcopy
import codecs

#VT-52 and related encoders

#--Control codes
STOP = 0x03
RETURN = 0x0D
ESC = 0x1B

# #--Special chars
# POUND = 0x9C
# LEFT_ARROW = 0x5F
# PI = 0xE3

#--Editor
DELETE = 0x08

#--GFX
HLINE = 0x2D
CROSS = 0x2B
VLINE = 0x7C
# HASH  = 0xB2
# COMM_U = 0xDF
# COMM_O = 0xDC
# COMM_J = 0xDD
# COMM_L = 0xDE
# CHECKMARK = 0xFB

# UL_CORNER = 0xDA     # Box corners
# UR_CORNER = 0xBF
# LL_CORNER = 0xC0
# LR_CORNER = 0xD9
# L_HALF  = 0xDD      # Semigraphics
# R_HALF  = 0xDE
# B_HALF  = 0xDF
# T_HALF  = 0xDC

#--Characters used by the BBS
SPINNER = 0x25  # Character to use while waiting
BACK = 0x5F     # Character to go back/exit ('_')  

#--Non printable characters grouped
NONPRINTABLE = [chr(i) for i in range(0,10)]+[11]+[chr(i) for i in range(14,32)]+[127]

# Colors
GREEN  = 0
YELLOW = 1
BLUE   = 2
RED    = 3
WHITE  = 4
CYAN   = 5
PURPLE = 6
ORANGE = 7
BLACK  = 8

# Color code to palette index dictionary
PALETTE = {'\x1bk'+chr((j*16)+i):j for i in range(9) for j in range(9)}

###########
# TML tags
###########
t_mono =    {'VT52':{'BR':'\r\n','AT':(lambda x,y:chr(ESC)+'Y'+chr(y+32)+chr(x+32),[('_R','_C'),('x',0),('y',0)]),'CLR':chr(ESC)+'H'+chr(ESC)+'J','HOME':chr(ESC)+'H',
                     'BACK':chr(BACK),'SPINNER':chr(SPINNER)},
             'VidTex':{'BR':'\r\n','AT':(lambda x,y:chr(ESC)+'Y'+chr(y+32)+chr(x+32),[('_R','_C'),('x',0),('y',0)]),'CLR':chr(ESC)+'j','HOME':chr(ESC)+'H',
                       'BACK':chr(BACK),'TEXT':'\x1bGN','SPINNER':chr(SPINNER)}}
t_multi =	{'DEL':chr(DELETE),'CRSRR':chr(ESC)+'C','CRSRL':chr(ESC)+'D','CRSRU':chr(ESC)+'A','CRSRD':chr(ESC)+'B',
            'POUND':'','PI':'','HASH':'#','HLINE':chr(HLINE),'VLINE':chr(VLINE),'CROSS':chr(CROSS), 'CHECKMARK': '+',
            'LARROW':'_','UARROW':'^','CBM-U':'','CBM-O':'','CBM-J':'','CBM-L':'',
            'UR-CORNER':'+','UL-CORNER':'+','LR-CORNER':'+','LL-CORNER':'+','V-LEFT':'+','V-RIGHT':'+','H-UP':'+','H-DOWN':'+'}

vt_colors = {'BLACK':(lambda c,i:VT52encoder.SetColor(c.encoder,i),[('_R','_C'),('c','_C'),('i',8)]),'WHITE':(lambda c,i:VT52encoder.SetColor(c.encoder,i),[('_R','_C'),('c','_C'),('i',4)]),
             'RED':(lambda c,i:VT52encoder.SetColor(c.encoder,i),[('_R','_C'),('c','_C'),('i',3)]),'PURPLE':(lambda c,i:VT52encoder.SetColor(c.encoder,i),[('_R','_C'),('c','_C'),('i',6)]),
             'CYAN':(lambda c,i:VT52encoder.SetColor(c.encoder,i),[('_R','_C'),('c','_C'),('i',5)]),'GREEN':(lambda c,i:VT52encoder.SetColor(c.encoder,i),[('_R','_C'),('c','_C'),('i',0)]),
             'BLUE':(lambda c,i:VT52encoder.SetColor(c.encoder,i),[('_R','_C'),('c','_C'),('i',2)]),'YELLOW':(lambda c,i:VT52encoder.SetColor(c.encoder,i),[('_R','_C'),('c','_C'),('i',1)]),
             'ORANGE':(lambda c,i:VT52encoder.SetColor(c.encoder,i),[('_R','_C'),('c','_C'),('i',7)]),
             'INK':(lambda conn,c:VT52encoder.SetColor(conn.encoder,c),[('_R','_C'),('conn','_C'),('c',4)]),
             'TEXT':(lambda conn,page,border,background:'\x1bGN'+VT52encoder.SetBackground(conn.encoder,background),[('_R','_C'),('conn','_C'),('page',0),('border',0),('background',0)])}

vt_semi = {'G4':(lambda conn,m:VT52encoder.SetVTMode(conn.encoder,m),[('_R','_C'),('conn','_C'),('m','4')]),
           'GN':(lambda conn,m:VT52encoder.SetVTMode(conn.encoder,m),[('_R','_C'),('conn','_C'),('m','N')]),
           'UL-QUAD':(lambda conn,c,n:VT52encoder.SemiChar(conn.encoder,c,n),[('_R','_C'),('conn','_C'),('c',0b1000),('n',1)]),
           'UR-QUAD':(lambda conn,c,n:VT52encoder.SemiChar(conn.encoder,c,n),[('_R','_C'),('conn','_C'),('c',0b0100),('n',1)]),
           'LL-QUAD':(lambda conn,c,n:VT52encoder.SemiChar(conn.encoder,c,n),[('_R','_C'),('conn','_C'),('c',0b0010),('n',1)]),
           'LR-QUAD':(lambda conn,c,n:VT52encoder.SemiChar(conn.encoder,c,n),[('_R','_C'),('conn','_C'),('c',0b0001),('n',1)]),
           'UL-LR-QUAD':(lambda conn,c,n:VT52encoder.SemiChar(conn.encoder,c,n),[('_R','_C'),('conn','_C'),('c',0b1001),('n',1)]),
           'UR-LL-QUAD':(lambda conn,c,n:VT52encoder.SemiChar(conn.encoder,c,n),[('_R','_C'),('conn','_C'),('c',0b0110),('n',1)]),
           'L-HALF':(lambda conn,c,n:VT52encoder.SemiChar(conn.encoder,c,n),[('_R','_C'),('conn','_C'),('c',0b1010),('n',1)]),
           'R-HALF':(lambda conn,c,n:VT52encoder.SemiChar(conn.encoder,c,n),[('_R','_C'),('conn','_C'),('c',0b0101),('n',1)]),
           'U-HALF':(lambda conn,c,n:VT52encoder.SemiChar(conn.encoder,c,n),[('_R','_C'),('conn','_C'),('c',0b1100),('n',1)]),
           'B-HALF':(lambda conn,c,n:VT52encoder.SemiChar(conn.encoder,c,n),[('_R','_C'),('conn','_C'),('c',0b0011),('n',1)]),
           'UL-UR-LL-QUAD':(lambda conn,c,n:VT52encoder.SemiChar(conn.encoder,c,n),[('_R','_C'),('conn','_C'),('c',0b1110),('n',1)]),
           'UL-UR-LR-QUAD':(lambda conn,c,n:VT52encoder.SemiChar(conn.encoder,c,n),[('_R','_C'),('conn','_C'),('c',0b1101),('n',1)]),
           'UL-LL-LR-QUAD':(lambda conn,c,n:VT52encoder.SemiChar(conn.encoder,c,n),[('_R','_C'),('conn','_C'),('c',0b1011),('n',1)]),
           'LL-LR-UR-QUAD':(lambda conn,c,n:VT52encoder.SemiChar(conn.encoder,c,n),[('_R','_C'),('conn','_C'),('c',0b0111),('n',1)]),
           'BLOCK':(lambda conn,c,n:VT52encoder.SemiChar(conn.encoder,c,n),[('_R','_C'),('conn','_C'),('c',0b1111),('n',1)])}

def toASCII(text:str, full=True):
    text = (unicodedata.normalize('NFKD',text).encode('ascii','vtspc')).decode('latin1')
    return text

def fromASCII(text:str, full=True):
    return text

######### VT52 ASCII codec error handler #########
# Replace unknowns with a space
def vthandler(e):
    char = b''
    if type(e) == UnicodeEncodeError:
        if e.object[e.start] in '¿¡':
            char = b' '
    elif type(e) == UnicodeDecodeError:
        ...
    return (char,e.end)

######### VT52 encoder subclass #########
class VT52encoder(Encoder):
    def __init__(self, name:str) -> None:
        super().__init__(name)
        self.encode = toASCII   #	Function to encode from ASCII/Unicode
        self.decode = fromASCII	#	Function to decode to ASCII/Unicode
        self.non_printable = NONPRINTABLE	#	List of non printable characters
        self.nl	= '\r'			#	New line string/character
        self.nl_out = '\r\n'      #   New line string/character (out)
        self.bs = chr(DELETE)	#	Backspace string/character
        self.txt_geo = (32,24)  #   Text screen dimensions
        self.ellipsis = '...'   # Ellipsis representation
        self.back = chr(BACK)
        self.features = {'color':       False,  # Encoder supports color
                         'bgcolor':     0,      # Fixed background color
                         'charsets':    1,      # Number if character sets supported
                         'reverse':     False,  # Encoder supports reverse video
                         'blink':       False,  # Encoder supports blink/flash text
                         'underline':   False,  # Encoder supports underlined text
                         'cursor':      True,   # Encoder supports cursor movement/set. Including home position and screen clear
                         'scrollback':  False,  # Encoder supports scrolling back (down) the screen
                         'windows':     0       # Encoder does not support screen windows
                         }
        self.bbuffer = 0x0000   # Bottom of the buffer
        self.tbuffer = 0x0000   # Top of the buffer
        self.palette = {}
        self.bgcolor = 8        # Background color for VidTex mode (default Black)
        self.fgcolor = 2
        self.black_replace = False  # Workaround for black color in Compuserve's VidTex terminals
        self.vt_mode = 'N'      # VidTex current graphic mode: possible values: N,4,H,M

    def color_index(self, code):
        return self.palette.get(code,-1)

    def SetColor(self,c):
        c &= 15
        # c = c if c < 9 else c & 7
        self.fgcolor = c
        return f'\x1bk{chr((c*16)+self.bgcolor)}'
    
    def SetVTMode(self,m:str):
        m = str(m)
        if m.upper() not in ['N','4','H','M']:
            m = 'N'
        self.vt_mode = m.upper()
        return f'\x1bG{m.upper()}'
    
    def SetBackground(self,c):
        c &= 15
        # c = c if c < 9 else c & 7
        self.bgcolor = c
        self.palette = {'\x1bk'+chr((j*16)+c):j for j in range(9)}  # Refresh Palette
        if self.black_replace:
            self.palette['\x1bk'+chr((8*16)+c)] = 7   # Replace black with orange in
        return f'\x1bk{chr((self.fgcolor*16)+c)}'

    def SemiChar(self,sg,n):
        cc = (self.fgcolor if self.fgcolor != 8 else 7) | 8
        char = chr((cc*16)+sg)
        if self.vt_mode == '4':
            return char*n
        elif self.black_replace:
            return f'\x1bG4{char*n}\x1bGN'
        else:
            return char*n


    ### Encoder setup routine
    # Setup the required parameters for the given client id
    # Either automatically or by enquiring the user
    # Return None if no setup is necessary, or a customized
    # copy of the encoder object
    def setup(self, conn, id):
        _copy = deepcopy(self)
        conn.SendTML('...<BR>')
        conn.Sendallbin(b'\x1bI')   # VidTex detection
        idstring = conn.NBReceive(80,3.5).decode('latin1')
        if idstring != '':
            if idstring[0] == '#' and idstring[-1] == '\r':
                lines = 0
                cols = 0
                _copy.tml_mono = deepcopy(t_mono['VidTex'])
                _copy.name = 'VidTex'
                options = idstring[1:-1].split(',')
                conn.SendTML('<FORMAT>VidTex compatible terminal detected</FORMAT>')
                for opt in options:
                    if 'SS' in opt: #Screen size
                        lines = ord(opt[2])-31
                        cols = ord(opt[3])-31
                    if opt == 'G4': #Semigraphics support
                        _copy.tml_mono.update(vt_semi)
                if lines == 0 or cols == 0:
                    conn.SendTML('Screen columns? (40): ')
                    cols = conn.ReceiveInt(32,80,40)
                    conn.SendTML('<BR>Screen lines? (25): ')
                    lines = conn.ReceiveInt(16,25,25)
                elif cols <= 40:
                    # Only CBTerm seems to miss screen dimensions, and it also doesnt support color
                    # Add color for any other terminal, but only if in 40 column mode
                    _copy.tml_mono.update(vt_colors)
                    _copy.features['color'] = True
                    _copy.features['bgcolor'] = 1
                    # _copy.palette = PALETTE
                    _copy.colors={'GREEN':0, 'YELLOW':1, 'BLUE':2, 'RED':3, 'WHITE':4, 'CYAN': 5, 'PURPLE':6, 'ORANGE':7, 'BLACK':8}
                    if len(options[0]) > 3: # Compuserve's VidTex II and Compuserve Executive uses Green instead of Black, we'll replace Black with Orange
                        _copy.black_replace = True
                        _copy.tml_mono['BLACK'] = (lambda c,i:VT52encoder.SetColor(c.encoder,i),[('_R','_C'),('c','_C'),('i',7)])
                    _copy.SetBackground(8)
                    conn.SendTML('<FORMAT>Please disable wordwrapping!</FORMAT>')
                _copy.txt_geo = (cols,lines)
                conn.SendTML('<PAUSE n=1.5>')
                return _copy
        conn.SendTML('<BR>Screen columns? (40): ')
        cols = conn.ReceiveInt(32,80,40)
        conn.SendTML('<BR>Screen lines? (25): ')
        _copy.txt_geo = (cols,conn.ReceiveInt(16,25,25))
        return _copy

###################################
# Register with the encoder module
###################################
def _Register():
    codecs.register_error('vtspc',vthandler)  # Register encoder error handler. 
    e0 = VT52encoder('VT52')
    e0.minT56Kver = 0
    e0.clients = {b'VT52':'VT52 or VidTex compatible'}
    e0.tml_mono  = t_mono['VT52']
    e0.tml_multi = t_multi
    e0.def_gfxmode = None
    e0.gfxmodes = None
    e0.ctrlkeys = {'DELETE':DELETE}
    return [e0]  #Each encoder module can return more than one encoder object. For example here it could also return ANSI.