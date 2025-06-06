import unicodedata
import re
from common.classes import Encoder
import os
from copy import deepcopy
import codecs
from common.imgcvt import gfxmodes

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
                     'BACK':chr(BACK),'SPINNER':(lambda conn:conn.SetHold(),[('conn','_C')])},
             'VidTex':{'BR':'\r\n','AT':(lambda x,y:chr(ESC)+'Y'+chr(y+32)+chr(x+32),[('_R','_C'),('x',0),('y',0)]),'CLR':chr(ESC)+'j','HOME':chr(ESC)+'H',
                       'BACK':chr(BACK),
                       'TEXT':(lambda conn,page,border,background:VT52encoder.SetVTMode(conn.encoder,'N'),[('_R','_C'),('conn','_C'),('page',0),('border',0),('background',0)]),
                       'SPINNER':(lambda conn:conn.SetHold(),[('conn','_C')])},
             'ST':{'RVSON':'\x1bp','RVSOFF':'\x1bq','CLR':'\x1bE','WROFF':'\x1bw','WRON':'\x1bv',
                   'PAPER':(lambda c:'\x1bc'+chr(32+c),[('_R','_C'),('c',0)]),
                   'CURSOR':(lambda enable: '\x1be' if enable else '\x1bf',[('_R','_C'),('enable',True)])}}

t_multi =	{'DEL':chr(DELETE),'CRSRR':chr(ESC)+'C','CRSRL':chr(ESC)+'D','CRSRU':chr(ESC)+'A','CRSRD':chr(ESC)+'B',
            'POUND':'','PI':'','HASH':'#','HLINE':chr(HLINE),'VLINE':chr(VLINE),'CROSS':chr(CROSS), 'CHECKMARK': '+',
            'LARROW':'_','UARROW':'^','CBM-U':'','CBM-O':'','CBM-J':'','CBM-L':'',
            'UR-CORNER':'+','UL-CORNER':'+','LR-CORNER':'+','LL-CORNER':'+','V-LEFT':'+','V-RIGHT':'+','H-UP':'+','H-DOWN':'+'}

st_colorsmed = {'WHITE':'\x1bb\x20','RED':'\x1bb\x21','GREEN':'\x1bb\x22','BLACK':'\x1bb\x23',
                'INK':(lambda c:'\x1bb'+chr(32+c),[('_R','_C'),('c',3)]),
                'TEXT':(lambda page,border,background:'\x1bq\x1bc'+chr(32+background)+'\x1bE',[('_R','_C'),('page',0),('border',3),('background',3)]),

}
st_colorslo = {'WHITE':'\x1bb\x20','DRED':'\x1bb\x21','GREEN':'\x1bb\x22','DYELLOW':'\x1bb\x23','DBLUE':'\x1bb\x24','DPURPLE':'\x1bb\x25','DCYAN':'\x1bb\x26','GREY3':'\x1bb\x27',
                'GREY2':'\x1bb\x28','RED':'\x1bb\x29','LTGREEN':'\x1bb\x2A','YELLOW':'\x1bb\x2B','BLUE':'\x1bb\x2C','PURPLE':'\x1bb\x2D','CYAN':'\x1bb\x2E','BLACK':'\x1bb\x2F',
                'INK':(lambda c:'\x1bb'+chr(32+c),[('_R','_C'),('c',3)]),
                'TEXT':(lambda page,border,background:'\x1bq\x1bc'+chr(32+background)+'\x1bE',[('_R','_C'),('page',0),('border',15),('background',15)]),
}


vt_colors = {'BLACK':(lambda c,i:VT52encoder.SetColor(c.encoder,c,i),[('_R','_C'),('c','_C'),('i',8)]),'WHITE':(lambda c,i:VT52encoder.SetColor(c.encoder,c,i),[('_R','_C'),('c','_C'),('i',4)]),
             'RED':(lambda c,i:VT52encoder.SetColor(c.encoder,c,i),[('_R','_C'),('c','_C'),('i',3)]),'PURPLE':(lambda c,i:VT52encoder.SetColor(c.encoder,c,i),[('_R','_C'),('c','_C'),('i',6)]),
             'CYAN':(lambda c,i:VT52encoder.SetColor(c.encoder,c,i),[('_R','_C'),('c','_C'),('i',5)]),'GREEN':(lambda c,i:VT52encoder.SetColor(c.encoder,c,i),[('_R','_C'),('c','_C'),('i',0)]),
             'BLUE':(lambda c,i:VT52encoder.SetColor(c.encoder,c,i),[('_R','_C'),('c','_C'),('i',2)]),'YELLOW':(lambda c,i:VT52encoder.SetColor(c.encoder,c,i),[('_R','_C'),('c','_C'),('i',1)]),
             'ORANGE':(lambda c,i:VT52encoder.SetColor(c.encoder,c,i),[('_R','_C'),('c','_C'),('i',7)]),
             'INK':(lambda conn,c:VT52encoder.SetColor(conn.encoder,conn,c),[('_R','_C'),('conn','_C'),('c',4)]),
             'TEXT':(lambda conn,page,border,background:VT52encoder.SetVTMode(conn.encoder,'N')+VT52encoder.SetBackground(conn.encoder,background),[('_R','_C'),('conn','_C'),('page',0),('border',8),('background',8)])}

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

# Multiple replace
# https://stackoverflow.com/questions/6116978/how-to-replace-multiple-substrings-of-a-string
Urep = {'\u00d7':'x','\u00f7':'/','\u2014':'-','\u2013':'-','\u2019':"'",'\u2018':"'",'\u201c':'"','\u201d':'"','\u2022':'*'}
Urep = dict((re.escape(k), v) for k, v in Urep.items())
UrepST = {'\u00d7':'x','\u2014':'-','\u2013':'-','\u2019':"'",'\u2018':"'",'\u201c':'"','\u201d':'"','\u2022':'*','\u00df':'\u20a7',
          '\u00e3':'\u2591','\u00f5':'\u2592','\u00d8':'\u2593','\u00f8':'\u2502','\u0153':'\u2524','\u0152':'\u2561','\u00c0':'\u2562','\u00c3':'\u2556',
          '\u00d5':'\u2555','\u00a8':'\u2563','\u00b4':'\u2551','\u2020':'\u2557','\u00b6':'\u255d','\u00a9':'\u255c','\u00ae':'\u255b','\u2122':'\u2510',
          '\u0133':'\u2514','\u0132':'\u2534','\u05d0':'\u252c','\u05d1':'\u251c','\u05d2':'\u2500','\u05d3':'\u253c','\u05d4':'\u255e','\u05d5':'\u255f',
          '\u05d6':'\u255a','\u05d7':'\u2554','\u05d8':'\u2569','\u05d9':'\u2566','\u05db':'\u2560','\u05dc':'\u2550','\u05de':'\u256c','\u05e0':'\u2567',
          '\u05e1':'\u2568','\u05e2':'\u2564','\u05e4':'\u2565','\u05e6':'\u2559','\u05e7':'\u2558','\u05e8':'\u2552','\u05e9':'\u2553','\u05ea':'\u256b',
          '\u05df':'\u256a','\u05da':'\u2518','\u05dd':'\u250c','\u05e3':'\u2588','\u05e5':'\u2584','\u09a7':'\u258c','\u2227':'\u2590','\u221e':'\u2580',
          '\u03b2':'\u00df','\u222e':'\u221e','\u03d5':'\u03c6','\u2208':'\u03b5'}
UrepST = dict((re.escape(k), v) for k, v in UrepST.items())

def toASCII(text:str, full=True):
    pattern = re.compile("|".join(Urep.keys()))
    text = pattern.sub(lambda m: Urep[re.escape(m.group(0))], text)
    text = (unicodedata.normalize('NFKD',text).encode('ascii','vtspc')).decode('latin1')
    return text

def fromASCII(text:str, full=True):
    return text

def toATRST(text:str, full=True):
    pattern = re.compile("|".join(UrepST.keys()))
    text = pattern.sub(lambda m: UrepST[re.escape(m.group(0))], text)
    text = (unicodedata.normalize('NFKD',text).encode('cp437','vtspc')).decode('latin1')
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
        self.gfxmodes = []
        self.def_gfxmode = None
        self.black_replace = False  # Workaround for black color in Compuserve's VidTex terminals
        self.vt_mode = 'N'      # VidTex current graphic mode: possible values: N,4,H,M

    def color_index(self, code):
        return self.palette.get(code,-1)

    def SetColor(self,conn,c):
        c &= 15
        # c = c if c < 9 else c & 7
        if self.black_replace and c == 8:
            c = 7
        self.fgcolor = c
        conn.parser.color = c
        return f'\x1bk{chr((c*16)+self.bgcolor)}'
    
    def SetVTMode(self,m:str):
        m = str(m)
        if m.upper() not in ['N','4','H','M']:
            m = 'N'
        if m != self.vt_mode:           # CBTerm stops rendering text if the GN escape code is sent while the terminal is already in text mode
            self.vt_mode = m.upper()
            return f'\x1bG{m.upper()}'
        else:
            return ''
    
    def SetBackground(self,c):
        c &= 15
        # c = c if c < 9 else c & 7
        self.bgcolor = c
        self.palette = {'\x1bk'+chr((j*16)+c):j for j in range(9)}  # Refresh Palette
        if self.black_replace:
            self.palette['\x1bk'+chr((8*16)+c)] = 7   # Replace black with orange in VidTex terminal
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

    def _scroll(self,rows):
        if rows > 0:
            return '\x1bH'+(chr(ESC)+'M')*rows
        elif rows < 0:
            return '\x1bH'+(chr(ESC)+'L')*abs(rows)
        else:
            return ''

    # Sanitize a given filename for compatibility with the client's filesystem
    # Input and output strings are not encoded
    # outout 8.3 filename
    def sanitize_filename(self, filename):
        def find_ext():
            nonlocal tmp,ext
            tl = len(tmp)-1
            for i in range(tl):
                tp = tmp.pop()
                if len(tp.replace(' ','')) > 0:
                    t_ext = tp.split(' ')
                    for j in range(len(t_ext)+1):
                        if len(t_ext[-j]) > 0:
                            ext = t_ext[-j][:3]
                            break
                    break

        filename = (unicodedata.normalize('NFKD',filename).encode('ascii','replace')).decode('ascii')
        filename = filename.translate({ord(i): '_' for i in ':*?"$,+;<=>/\\[]|'})
        tmp = filename.split('.')
        ext = ''
        if len(tmp) > 1:
            find_ext()
        else:
            tmp = tmp[0].split(' ')
            if len(tmp) > 1:
                find_ext()
        filename = '_'.join(tmp).replace(' ','_')[:8]
        if ext != '':
            filename += '.'+ext
        print(filename)
        return filename



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
                _copy.gfxmodes = []
                for opt in options:
                    if 'SS' in opt: #Screen size
                        lines = ord(opt[2])-31
                        cols = ord(opt[3])-31
                    if opt == 'G4': #Semigraphics support
                        _copy.tml_mono.update(vt_semi)
                    if opt == 'GM': #MedRes RLE
                        _copy.gfxmodes.append(gfxmodes.VTMED)
                    if opt == 'GH': #HiRes RLE
                        _copy.gfxmodes.append(gfxmodes.VTHI)
                if len(_copy.gfxmodes) != 0:
                    if gfxmodes.VTHI in _copy.gfxmodes:
                        _copy.def_gfxmode = gfxmodes.VTHI
                    else:
                        _copy.def_gfxmode = gfxmodes.VTMED
                    _copy.tml_mono['GRAPHIC']=(lambda mode,page,border,background: self.SetVTMode('H' if mode==gfxmodes.VTHI else 'M'),[('_R','_C'),('mode',False),('page',0),('border',0),('background',0)])
                if lines == 0 or cols == 0:
                    conn.SendTML('Screen columns? (40): ')
                    cols = conn.ReceiveInt(32,80,40)
                    conn.SendTML('<BR>Screen lines? (25): ')
                    lines = conn.ReceiveInt(16,25,25)
                elif cols <= 40:
                    # Only CBTerm seems to be missing screen dimensions, and it also doesnt support color
                    # Add color for any other terminal, but only if in 40 column mode
                    _copy.tml_mono.update(vt_colors)
                    _copy.features['color'] = True
                    _copy.features['bgcolor'] = 1
                    # _copy.palette = PALETTE
                    _copy.colors={'GREEN':0, 'YELLOW':1, 'BLUE':2, 'RED':3, 'WHITE':4, 'CYAN': 5, 'PURPLE':6, 'ORANGE':7, 'BLACK':8}
                    if len(options[0]) > 3: # Compuserve's VidTex uses Green instead of Black, we'll replace Black with Orange
                        _copy.black_replace = True
                        _copy.tml_mono['BLACK'] = (lambda c,i:VT52encoder.SetColor(c.encoder,c,i),[('_R','_C'),('c','_C'),('i',7)])
                    _copy.SetBackground(8)
                    conn.SendTML('<FORMAT>Please disable wordwrapping!</FORMAT>')
                _copy.txt_geo = (cols,lines)
                conn.SendTML('<PAUSE n=1.5>')
                return _copy
        conn.SendTML('<BR><BR>Screen columns? (40): ')
        cols = conn.ReceiveInt(32,80,40)
        conn.SendTML('<BR>Screen lines? (25): ')
        _copy.txt_geo = (cols,conn.ReceiveInt(16,25,25))
        conn.SendTML('<BR>Atari ST mode (Y/N):')
        if conn.ReceiveKey('yn') == 'y':
            # Atari ST modes
            _copy.tml_mono.update(t_mono['ST'])
            _copy.tml_mono['SCROLL'] = (self._scroll ,[('_R','_C'),('rows',1)])
            conn.Sendallbin(b'\x1bv\x1bq')   #Enable wordwrap, normal video
            _copy.features['color'] = True
            _copy.features['bgcolor'] = 2
            _copy.features['scrollback'] = True
            _copy.encode = toATRST
            _copy.decode = lambda t:t.encode('latin1').decode('cp437')	#	Function to decode from CP437 to Unicode
            _copy.ctrlkeys.update({'CRSRU':'\x1bA','CRSRD':'\x1bB','CRSRR':'\x1bC','CRSRL':'\x1bD'})
            _copy.tml_multi['CHECKMARK']='\xfb'
            if _copy.txt_geo[0] > 40:   #Assume hi/medres
                conn.SendTML('<BR>(M)edium or (H)i-Res?')
                if conn.ReceiveKey('mhMH').lower() == 'm':
                    _copy.name = 'ATRSTM'
                    _copy.colors={'WHITE':0, 'RED':1, 'GREEN':2, 'BLACK':3}
                    _copy.palette = {'\x1bb'+chr(32+j):j for j in range(4)}  # Refresh Palette
                    _copy.tml_mono.update(st_colorsmed)
                else:
                    _copy.features['color'] = False
                    _copy.name = 'ATRSTH'
            else:   # Assume lores
                _copy.name = 'ATRSTL'
                _copy.colors={'WHITE':0,'DKRED':1,'GREEN':2, 'DKYELLOW':3,'DKBLUE':4,'DKPURPLE': 5,'DKCYAN':6,'GREY3':7,
                              'GREY2':8,'RED':9,'LTGREEN':10,'YELLOW':11,'BLUE':12,'PURPLE':13,'CYAN':14,'BLACK':15,
                              'DRED':1,'DYELLOW':3,'DBLUE':4,'DPURPLE':5,'DCYAN':6,'LIGHT_GREEN':10,'LIGHT_GREY':7,'GREY':8,'MEDIUM_GREY':8}
                _copy.palette = {'\x1bb'+chr(32+j):j for j in range(16)}  # Refresh Palette
                _copy.tml_mono.update(st_colorslo)
            _copy.tml_multi['DEL'] = '\x08 \x08'
        return _copy

###################################
# Register with the encoder module
###################################
def _Register():
    codecs.register_error('vtspc',vthandler)  # Register encoder error handler. 
    e0 = VT52encoder('VT52')
    e0.minT56Kver = 0
    e0.clients = {b'VT52':'VT52/VidTex compatible/Atari ST'}
    e0.tml_mono  = t_mono['VT52']
    e0.tml_multi = t_multi
    e0.def_gfxmode = None
    e0.gfxmodes = ()
    e0.ctrlkeys = {'DELETE':chr(DELETE)}
    return [e0]