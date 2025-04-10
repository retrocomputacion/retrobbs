import unicodedata
import re
from common.classes import Encoder
import codecs
from copy import deepcopy

# ASCII CP437 and ANSI encoder

#--Control codes
STOP = 0x03
RETURN = 0x0D
ESC = 0x1B

#--Special chars
POUND = 0x9C
PI = 0xE3

#--Editor
DELETE = 0x08

#--GFX
HLINE = 0xC4
CROSS = 0xC5
VLINE = 0xB3
HASH  = 0xB1
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
B_HALF  = 0xDC
T_HALF  = 0xDF

#--Non printable characters grouped
NONPRINTABLE = [chr(i) for i in range(0,10)]+[11]+[chr(i) for i in range(14,32)]+[127]

###########
# TML tags
###########
t_mono = 	{'ASCII':{'BR':'\r\n','AT':'','CLR':'\x0c','BACK':'_'},
             'ANSI':{'BR':'\r\n','CLR':'\x1b[2J\x1b[H','BACK':'_','HOME':'\x1b[H',
                     'RVSON':(lambda conn:ASCIIencoder.RVS(conn.encoder,conn,True),[('_R','_C'),('conn','_C')]),
                     'RVSOFF':(lambda conn:ASCIIencoder.RVS(conn.encoder,conn,False),[('_R','_C'),('conn','_C')]),
                     'FLASHON':(lambda conn:ASCIIencoder.BLINK(conn.encoder,conn,True),[('_R','_C'),('conn','_C')]),
                     'FLASHOFF':(lambda conn:ASCIIencoder.BLINK(conn.encoder,conn,False),[('_R','_C'),('conn','_C')]),
                     'CURSOR':(lambda enable: '\x1b[?25h' if enable else '\x1b[?25l',[('_R','_C'),('enable',True)]),
                     'CRSRR':(lambda n:f'\x1b[{n}C',[('_R','_C'),('n',1)]),'CRSRL':(lambda n:f'\x1b[{n}D',[('_R','_C'),('n',1)]),
                     'CRSRU':(lambda n:f'\x1b[{n}A',[('_R','_C'),('n',1)]),'CRSRD':(lambda n:f'\x1b[{n}B',[('_R','_C'),('n',1)]),
                     'AT':(lambda x,y:f'\x1b[{y+1};{x+1}H',[('_R','_C'),('x',0),('y',0)]),
                     'SCROLL':(lambda rows:f'\x1b[{rows}S'if rows > 0 else f'\x1b[{-rows}T',[('_R','_C'),('rows',1)])}}
# t_mono = 	{'ASCII':{'BR':'\r\n','AT':'','CLR':'\x0c','BACK':'_'},
#              'ANSI':{'BR':'\r\n','CLR':'\x1b[2J\x1b[H','BACK':'_','HOME':'\x1b[H','RVSON':'\x1b[7m','RVSOFF':'\x1b[27m',
#                      'FLASHON':'\x1b[5m','FLASHOFF':'\x1b[25m',
#                      'CURSOR':(lambda enable: '\x1b[?25h' if enable else '\x1b[?25l',[('_R','_C'),('enable',True)]),
#                      'CRSRR':(lambda n:f'\x1b[{n}C',[('_R','_C'),('n',1)]),'CRSRL':(lambda n:f'\x1b[{n}D',[('_R','_C'),('n',1)]),
#                      'CRSRU':(lambda n:f'\x1b[{n}A',[('_R','_C'),('n',1)]),'CRSRD':(lambda n:f'\x1b[{n}B',[('_R','_C'),('n',1)]),
#                      'AT':(lambda x,y:f'\x1b[{y+1};{x+1}H',[('_R','_C'),('x',0),('y',0)]),
#                      'SCROLL':(lambda rows:f'\x1b[{rows}S'if rows > 0 else f'\x1b[{-rows}T',[('_R','_C'),('rows',1)])}}
#
#  (lambda conn:ASCIIencoder.RVS(conn.encoder,conn,True),[('_R','_C'),('conn','_C')]),
                    #  'RVSOFF':(lambda conn:ASCIIencoder.RVS(conn.encoder,conn,False),[('_R','_C'),('conn','_C')])

t_multi =	{'ASCII':{'DEL':'\x08 \x08',
            'POUND':chr(POUND),'PI':chr(PI),'HASH':chr(HASH),'HLINE':chr(HLINE),'VLINE':chr(VLINE),'CROSS':chr(CROSS), 'CHECKMARK': chr(CHECKMARK),
            'LARROW':'_','UARROW':'^','CBM-U':'','CBM-O':'','CBM-J':'','CBM-L':'',
            'UR-CORNER':'+','UL-CORNER':'+','LR-CORNER':'+','LL-CORNER':'+','V-LEFT':'+','V-RIGHT':'+','H-UP':'+','H-DOWN':'+'},
            'CP437':{'DEL':'\x08 \x08',
            'POUND':chr(POUND),'PI':chr(PI),'HASH':chr(HASH),'HLINE':chr(HLINE),'VLINE':chr(VLINE),'CROSS':chr(CROSS), 'CHECKMARK': chr(CHECKMARK),
            'LARROW':'_','UARROW':'^','B-HALF':chr(B_HALF),'T-HALF':chr(B_HALF),'L-HALF':chr(L_HALF),'R-HALF':chr(R_HALF),'BLOCK':'\xDB',
            'UR-CORNER':'\xbf','UL-CORNER':'\xda','LR-CORNER':'\xd9','LL-CORNER':'\xc0','V-LEFT':'\xb4','V-RIGHT':'\xc3','H-UP':'\xc1','H-DOWN':'\xc2'}}

Urep = {'\u00d7':'x','\u00f7':'/','\u2014':'-','\u2013':'-','\u2019':"'",'\u2018':"'",'\u201c':'"','\u201d':'"','\u2022':'*'}
Urep = dict((re.escape(k), v) for k, v in Urep.items())

ansi_fgidx = ['2;30','2;31','2;32','2;33','2;34','2;35','2;36','2;37','1;30','1;31','1;32','1;33','1;34','1;35','1;36','1;37']
ansi_bgidx = ['2;40','2;41','2;42','2;43','2;44','2;45','2;46','2;47','1;40','1;41','1;42','1;43','1;44','1;45','1;46','1;47']

ansi_colors = { 'BLACK':(lambda c:ASCIIencoder.SetColor(c.encoder,c,0),[('_R','_C'),('c','_C')]),'DRED':(lambda c:ASCIIencoder.SetColor(c.encoder,c,1),[('_R','_C'),('c','_C')]),
                'GREEN':(lambda c:ASCIIencoder.SetColor(c.encoder,c,2),[('_R','_C'),('c','_C')]),'DYELLOW':(lambda c:ASCIIencoder.SetColor(c.encoder,c,3),[('_R','_C'),('c','_C')]),
                'BLUE':(lambda c:ASCIIencoder.SetColor(c.encoder,c,4),[('_R','_C'),('c','_C')]),'PURPLE':(lambda c:ASCIIencoder.SetColor(c.encoder,c,5),[('_R','_C'),('c','_C')]),
                'DCYAN':(lambda c:ASCIIencoder.SetColor(c.encoder,c,6),[('_R','_C'),('c','_C')]),'GREY3':(lambda c:ASCIIencoder.SetColor(c.encoder,c,7),[('_R','_C'),('c','_C')]),
                'GREY2':(lambda c:ASCIIencoder.SetColor(c.encoder,c,8),[('_R','_C'),('c','_C')]),'RED':(lambda c:ASCIIencoder.SetColor(c.encoder,c,9),[('_R','_C'),('c','_C')]),
                'LTGREEN':(lambda c:ASCIIencoder.SetColor(c.encoder,c,10),[('_R','_C'),('c','_C')]),'YELLOW':(lambda c:ASCIIencoder.SetColor(c.encoder,c,11),[('_R','_C'),('c','_C')]),
                'LTBLUE':(lambda c:ASCIIencoder.SetColor(c.encoder,c,12),[('_R','_C'),('c','_C')]),'LTPURPLE':(lambda c:ASCIIencoder.SetColor(c.encoder,c,13),[('_R','_C'),('c','_C')]),
                'CYAN':(lambda c:ASCIIencoder.SetColor(c.encoder,c,14),[('_R','_C'),('c','_C')]),'WHITE':(lambda c:ASCIIencoder.SetColor(c.encoder,c,15),[('_R','_C'),('c','_C')]),
                'GREY':(lambda c:ASCIIencoder.SetColor(c.encoder,c,8),[('_R','_C'),('c','_C')]),
                'INK':(lambda conn,c:ASCIIencoder.SetColor(conn.encoder,conn,c),[('_R','_C'),('conn','_C'),('c',7)]),
                'PAPER':(lambda conn,c:ASCIIencoder.SetBackground(conn.encoder,conn,c),[('_R','_C'),('conn','_C'),('c',3)]),
                'TEXT':(lambda conn,page,border,background:f'{ASCIIencoder.RVS(conn.encoder, conn, False)}\x1b[0m{ASCIIencoder.SetBackground(conn.encoder,conn,background)}\x1b[2J',[('_R','_C'),('conn','_C'),('page',0),('border',0),('background',0)])}


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

######### ASCII encoder subclass #########
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
        self.clients = {b'_default_':'ASCII', b'ASC':'Extended ASCII (CP437)',b'ANS':'ANSI'}
        self.back = '_'
        self.bbuffer = 0x0000   # Bottom of the buffer
        self.tbuffer = 0x0000   # Top of the buffer
        self.palette = {}
        self.gfxmodes = []
        self.def_gfxmode = None
        self.tml_mono  = t_mono['ASCII']
        self.tml_multi = t_multi['ASCII']
        self.ctrlkeys = {'DELETE':chr(DELETE)}
        self.bgcolor = 0   # current ANSI background color (39 = Default)
        self.fgcolor = 1   # current ANSI foreground color (39 = Default)
        self.rvs = False   # reverse mode?
        self.blink = False # blink mode?

    def SetColor(self,conn,c):
        c &= 15
        # if not self.rvs:
        self.fgcolor = c
        f = ansi_fgidx[c]
        # b = ansi_bgidx[self.bgcolor]
        conn.parser.color = c
        # else:
        #     self.bgcolor = c
        #     b = ansi_bgidx[c]
        #     f = ansi_fgidx[self.fgcolor]
        return f'\x1b[{f}m'

    def SetBackground(self,conn,c):
        c &= 15
        # if not self.rvs:
        self.bgcolor = c
        b = ansi_bgidx[c]
        # f = ansi_fgidx[self.fgcolor]
        # else:
        #     self.fgcolor = c
        #     f = ansi_fgidx[c]
        #     conn.parser.color = c
        #     b = ansi_bgidx[self.bgcolor]
        return f'\x1b[{b}m'

    def RVS(self,conn, v=True):
        res = ''
        if self.rvs != v:
            if not v:
            # bg = self.bgcolor
            # self.bgcolor = self.fgcolor
            # self.fgcolor = bg
            # conn.parser.color = bg
                cb = ansi_bgidx[self.bgcolor]
                cf = ansi_fgidx[self.fgcolor]
                res = f'\x1b[27m\x1b[m\x1b[{cf};{cb}{";5" if self.blink else ""}m'
            else:
                res = '\x1b[7m'
        self.rvs = v
        return res

    def BLINK(self,conn, v=True):
        res = ''
        if self.blink != v:
            if not v:
            # bg = self.bgcolor
            # self.bgcolor = self.fgcolor
            # self.fgcolor = bg
            # conn.parser.color = bg
                cb = ansi_bgidx[self.bgcolor]
                cf = ansi_fgidx[self.fgcolor]
                res = f'\x1b[25m\x1b[m\x1b[{cf};{cb}{";7" if self.rvs else ""}m'
            else:
                res = '\x1b[5m'
        self.blink = v
        return res


    def setup(self, conn, id):
        if id == b'ASC':
            _copy = deepcopy(self)
            _copy.name = 'CP437'
            conn.SendTML('Screen columns? (40): ')
            cols = conn.ReceiveInt(32,80,40)
            conn.SendTML('<BR>Screen lines? (25): ')
            lines = conn.ReceiveInt(16,25,25)
            _copy.txt_geo = (cols,lines)
            _copy.tml_multi = t_multi['CP437']
            return _copy
        elif id == b'ANS':
            _copy = deepcopy(self)
            _copy.name = 'ANSI'
            _copy.tml_multi = t_multi['CP437']
            _copy.tml_mono = t_mono['ANSI']
            _copy.features['cursor'] = True
            _copy.features['color'] = True
            _copy.features['bgcolor'] = 2
            _copy.features['scrollback'] = True
            _copy.ctrlkeys.update({'CRSRU':'\x1b[A','CRSRD':'\x1b[B','CRSRR':'\x1b[C','CRSRL':'\x1b[D'})
            # Try to detect screen size
            conn.SendTML('...<BR>')
            conn.Sendallbin(b'\x1b[999;999H')    # Move cursor to the extreme lower right
            conn.Sendallbin(b'\x1b[6n')          # Device status report
            cursor = conn.NBReceive(10,3.5).decode('latin1')
            if cursor != '':
                if cursor[0:2] == '\x1b[' and cursor[-1] == 'R' and ';' in cursor:
                    cursor = cursor.split(';')
                    _copy.txt_geo= (int(cursor[1][:-1]),int(cursor[0][2:]))
                    conn.SendTML(f'<BR><FORMAT>Detected screen: {cursor[1][:-1]}x{cursor[0][2:]}</FORMAT><BR><PAUSE n=1>')
            else:
                conn.SendTML('Screen columns? (80): ')
                cols = conn.ReceiveInt(32,80,80)
                conn.SendTML('<BR>Screen lines? (25): ')
                _copy.txt_geo = (cols,conn.ReceiveInt(8,25,25))
            _copy.colors={'BLACK':0,'DKRED':1,'GREEN':2,'DKYELLOW':3,'BLUE':4,'PURPLE':5,'DKCYAN':6,'GREY3':7,
                          'GREY2':8,'RED':9,'LTGREEN':10,'YELLOW':11,'LTBLUE':12,'LTPURPLE':13,'CYAN':14,'WHITE':15,
                          'DARK_RED':1,'MEDIUM_GREY':8,'GREY':8,'LIGHT_BLUE':12,'LIGHT_PURPLE':13,'LIGHT_GREEN':10,
                          'DARK_YELLOW':3,'DARK_CYAN':6,'LIGHT_GREY':7,'DRED':1, 'DCYAN':6, 'DYELLOW':3}
            _copy.palette = {f'\x1b[{c}m':j for j,c in enumerate(ansi_fgidx)}  # Refresh Palette
            _copy.tml_mono.update(ansi_colors)

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
    return [e0]  #Each encoder module can return more than one encoder object. For example here it could also return ANSI.