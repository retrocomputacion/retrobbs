import unicodedata
import re
from common.classes import Encoder
from common.imgcvt import gfxmodes
import os
from copy import deepcopy

#MSX constants

#--Control codes
GRAPH = 0x01
STOP = 0x03
RETURN = 0x0D
SELECT = 0x18
RVS_ON = 0x19
RVS_OFF = 0x1A
ESC = 0x1B

#--Special chars
POUND = 0x9C
YEN = 0x9D
PI = 0xE3

#--Editor
TAB = 0x09
CRSR_LEFT = 0x1D
CRSR_RIGHT = 0x1C
CRSR_UP = 0x1E
CRSR_DOWN = 0x1F
CLEAR = 0x0C
INSERT = 0x12
HOME = 0x0B
DELETE = 0x08

#--Foreground Colors
BLACK = 0x01
GREEN = 0x02
LT_GREEN = 0x03
BLUE = 0x04
LT_BLUE = 0x05
DARK_RED = 0x06
CYAN = 0x07
RED = 0x08
PINK = 0x09
YELLOW = 0x0A
LT_YELLOW = 0x0B
DARK_GREEN = 0x0C
PURPLE = 0x0D
GREY = 0x0E
WHITE = 0x0F

#--Background Colors
# B_BLACK = 0x0101
# B_GREEN = 0x0102
# B_LT_GREEN = 0x0103
# B_BLUE = 0x0104
# B_LT_BLUE = 0x0105
# B_DARK_RED = 0x0106
# B_CYAN = 0x0107
# B_RED = 0x0108
# B_PINK = 0x0109
# B_YELLOW = 0x010A
# B_LT_YELLOW = 0x010B
# B_DARK_GREEN = 0x010C
# B_PURPLE = 0x010D
# B_GREY = 0x010E
# B_WHITE = 0x010F

#--F Keys
F1 = 0x02
F2 = 0x04
F3 = 0x05
F4 = 0x06
F5 = 0x0E
F6 = 0x0F
F7 = 0x10
F8 = 0x11
F9 = 0x13
F10= 0x14


#--GFX
HASH = 0xD7                         
HLINE = 0x57    #                    \
CROSS = 0x55    #                   -|-->  Extended graphics (substract 0x40 for use with line fill)
VLINE = 0x56    #                   -|
UL_CORNER = 0x58     # Box corners --| 
UR_CORNER = 0x59     #              -|
LL_CORNER = 0x5A     #              -|
LR_CORNER = 0x5B     #              -|
V_RIGHT = 0x54       # Box borders  -|
V_LEFT  = 0x53       #              -|
H_UP    = 0x51       #              -|
H_DOWN  = 0x52       #              /
UL_QUAD = 0xD3  # Semigraphics
UR_QUAD = 0xD5
LL_QUAD = 0xD6
LR_QUAD = 0xD4
L_HALF  = 0xDD
B_HALF  = 0xDC
UL_LR_QUAD = 0xC1
LL_UR_QUAD = 0xC7
L_NARROW = 0xC6
R_NARROW = 0xC9
B_NARROW = 0xC0
U_NARROW = 0xC3
TRI_LEFT = 0xCF     #Triangles
TRI_RIGHT = 0xD0
TRI_UP = 0xCD
TRI_DOWN = 0xCE

#--Characters used by the BBS
SPINNER = 0xD2  # Character to use while waiting
BACK = 0x5F     # Character to go back/exit ('_')  

# Color code to palette index dictionary
PALETTE = {chr(1)+chr(BLACK):1,chr(1)+chr(GREEN):2,chr(1)+chr(LT_GREEN):3,chr(1)+chr(BLUE):4,chr(1)+chr(LT_BLUE):5,chr(1)+chr(DARK_RED):6,chr(1)+chr(CYAN):7,
           chr(1)+chr(RED):8,chr(1)+chr(PINK):9,chr(1)+chr(YELLOW):10,chr(1)+chr(LT_YELLOW):11,chr(1)+chr(DARK_GREEN):12,chr(1)+chr(PURPLE):13,chr(1)+chr(GREY):14,
           chr(1)+chr(WHITE):15}

#--Non printable characters grouped
NONPRINTABLE = [chr(i) for i in range(0,13)]+[chr(i) for i in range(14,32)]+[chr(127)]+[chr(1)+chr(i) for i in range(1,16)]

###########
# TML tags
###########
t_mono = 	{'MSX1':{'CLR':chr(CLEAR),'HOME':chr(HOME),'RVSON':chr(RVS_ON),'RVSOFF':chr(RVS_OFF),'BR':'\r',
            'BLACK':chr(1)+chr(BLACK),'WHITE':chr(1)+chr(WHITE),'RED':chr(1)+chr(RED),'CYAN':chr(1)+chr(CYAN),'PURPLE':chr(1)+chr(PURPLE),
            'GREEN':chr(1)+chr(GREEN),'BLUE':chr(1)+chr(BLUE),'YELLOW':chr(1)+chr(YELLOW),'PINK':chr(1)+chr(PINK),'GREY':chr(1)+chr(GREY),
            'LTGREEN':chr(1)+chr(LT_GREEN),'LTBLUE':chr(1)+chr(LT_BLUE),'DRED':chr(1)+chr(DARK_RED),'DGREEN':chr(1)+chr(DARK_GREEN),
            'LTYELLOW':chr(1)+chr(LT_YELLOW),
            'SPINNER':(lambda conn:conn.SetHold(),[('conn','_C')]),'BACK':chr(BACK),
            'PAPER':(lambda c:'\x01'+chr(c+0x10),[('_R','_C'),('c',1)])},
            'MSXSTD':{'CLR':chr(CLEAR),'HOME':chr(HOME),'BR':'\r\n','AT':(lambda x,y:chr(ESC)+'Y'+chr(y+32)+chr(x+32),[('_R','_C'),('x',0),('y',0)]),
                      'CURSOR':(lambda enable: '\x1by5' if enable else '\x1bx5',[('_R','_C'),('enable',True)]),
                      'SPINNER':(lambda conn:conn.SetHold(),[('conn','_C')]),'BACK':chr(BACK)}}
t_multi =	{'MSX1':{'CRSRL':chr(CRSR_LEFT),'CRSRU':chr(CRSR_UP),'CRSRR':chr(CRSR_RIGHT),'CRSRD':chr(CRSR_DOWN),'DEL':chr(DELETE),'INS':chr(INSERT),
            'POUND':chr(POUND),'PI':chr(PI),'HASH':chr(HASH),'HLINE':chr(1)+chr(HLINE),'VLINE':chr(1)+chr(VLINE),'CROSS':chr(1)+chr(CROSS),'UARROW':'^',
            'CHECKMARK':'\x01\x41',
            'UL-CORNER':chr(1)+chr(UL_CORNER),'UR-CORNER':chr(1)+chr(UR_CORNER),'LL-CORNER':chr(1)+chr(LL_CORNER),'LR-CORNER':chr(1)+chr(LR_CORNER),
            'V-RIGHT':chr(1)+chr(V_RIGHT),'V-LEFT':chr(1)+chr(V_LEFT),'H-UP':chr(1)+chr(H_UP),'H-DOWN':chr(1)+chr(H_DOWN),'BLOCK':'\xDB',
            'UL-QUAD':chr(UL_QUAD),'UR-QUAD':chr(UR_QUAD),'LL-QUAD':chr(LL_QUAD),'LR-QUAD':chr(LR_QUAD),'UL-LR-QUAD':chr(UL_LR_QUAD),
            'L-HALF':chr(L_HALF),'B-HALF':chr(B_HALF),'L-NARROW':chr(L_NARROW),'R-NARROW':chr(R_NARROW),'U-NARROW':chr(U_NARROW),'B-NARROW':chr(B_NARROW),
            'U-HALF':'\xDF','R-HALF':'\xDE',
            'TRI-LEFT':chr(TRI_LEFT),'TRI-RIGHT':chr(TRI_RIGHT),'TRI-UP':chr(TRI_UP),'TRI-DOWN':chr(TRI_DOWN)}}


######### MSX encoder subclass #########
class MSXencoder(Encoder):
    def __init__(self, name:str) -> None:
        super().__init__(name)
        self.encode = toMSX	    #	Function to encode from ASCII/Unicode
        self.decode = toASCII	#	Function to decode to ASCII/Unicode
        self.non_printable = NONPRINTABLE	#	List of non printable characters
        self.nl	= '\r'			#	New line string/character
        self.nl_out = '\r'      #   New line string/character (out)
        self.bs = chr(DELETE)	#	Backspace string/character
        self.txt_geo = (32,24)  #   Text screen dimensions
        self.ellipsis = '\u00bb'   # Ellipsis representation
        self.back = chr(BACK)
        self.spinner = {'start':f'<CHR c={SPINNER}><CRSRL>',
                        'loop':None,
                        'stop':' <DEL>'}                          # Spinner sequence
        self.features = {'color':       True,  # Encoder supports color
                         'bgcolor':     2,      # Per character background color
                         'charsets':    1,      # Number if character sets supported
                         'reverse':     False,  # Encoder supports reverse video
                         'blink':       False,  # Encoder supports blink/flash text
                         'underline':   False,  # Encoder supports underlined text
                         'cursor':      True,   # Encoder supports cursor movement/set. Including home position and screen clear
                         'scrollback':  True,    # Encoder supports scrolling back (down) the screen
                         'windows':     1       # Encoder support full width screen slice windows
                         }

    def color_index(self, code):
        return self.palette.get(code,-1)

    ### Wordwrap text preserving control codes
    def wordwrap(self,text,split=False):
        if self.nl_out == '\r\n':
            return super().wordwrap(text,split)
        codes = ''.join(chr(i) for i in range(1,16))+''.join(chr(i) for i in range(17,32))  #'\x01\x07\x08\x0b\x12\x19\x1a\x1c\x1d\x1e\x1f\x7f'

        out = ''
        extend = False

        # Replace Yellow color code before splitting by lines
        for c in text:
            if extend == False:
                if ord(c) == 1:
                   extend = True
                out = out + c
            else:
                if c == '\r':
                    out = out  + '\xff'
                else:
                    out = out + c
                extend = False
        text = out

        if split:
            out = []
        else:
            out = ''

        lines = text.split('\r')
        extend = False
        for line in lines:
            line = line.replace('\x01\xff','\x01\x0a')  # replace back the YELLOW color code
            t_line = ''
            if len(line)!=0:
                space = 32  # Space left in line
                line = re.sub(r'(['+codes+r'])',r'\020\1\020', line)
                line = line if line[0]!='\x10' else line[1:]
                words = re.split(r'\020+| ',line) # words = line.split(' ')
                pword = False
                for word in words:
                    if len(word) == 0:
                        t_line = t_line + ' '   # out = out + ' ' # Add space if last item was a word or a space 
                        pword= False
                        space -=1
                    elif not extend:
                        if  (32 <= ord(word[0]) <= 126) or (128 <= ord(word[0]) <= 253):   # Normal Printable
                            if pword:
                                pword = False
                                space -= 1
                                t_line = t_line + ' '   # out = out + ' ' # Add space if last word was a _word_
                                if space == 0:
                                    space = 32
                            if space - len(word) < 0:
                                t_line = t_line + '\r'  # out = out + '\r' + word
                                if split:
                                    out.append(t_line)
                                else:
                                    out = out + t_line
                                t_line = word
                                space = 32 - len(word)
                            else:
                                t_line = t_line + word  # out = out + word
                                space -= len(word)
                            #Add space
                            if space != 0:
                                pword = True
                        elif word[0] == '\x01': #GRAPH
                            extend = True
                        elif word[0] in '\x1e\x1f\x19\x1a\x7f\x12': #crsr up/down, RVSON/OFF, INSERT, DEL
                            #just add the code
                            t_line = t_line + word  # out = out + word
                            pword = False
                        elif word[0] in '\x0b\x0c': #HOME CLR
                            t_line = t_line + word  # out = out + word
                            space = 32
                            pword = False
                        elif word[0] in '\x08\x1d': #BS, crsr left
                            t_line = t_line + word  # out = out + word
                            space = space+1 if space+1 <= 32 else 1 # <- take into account going around to the previous line (being already at home not taken into account)
                            pword = False
                        elif word[0] == '\x1c': #crsr right
                            t_line = t_line + word# out = out + word
                            space -= 1
                        else:
                            pword = False
                    else:
                        if 64 <= ord(word[0]) <= 97:    #Extended gfx
                            if pword:
                                pword = False
                                space -= 1
                                t_line = t_line + ' '   # out = out + ' ' # Add space if last word was a _word_
                                if space == 0:
                                    space = 32
                            if space - len(word) < 0:
                                t_line = t_line + '\r'  # out = out + '\r' + '\x01'+ word
                                if split:
                                    out.append(t_line)
                                else:
                                    out = out + t_line
                                t_line = '\x01' + word
                                space = 32 - len(word)
                            else:
                                t_line = t_line + '\x01' + word # out = out + '\x01' + word
                                space -= len(word)
                            #Add space
                            if space != 0:
                                pword = True
                            extend = False
                        elif (1 <= ord(word[0]) <= 15) or (17 <= ord(word[0]) <= 31):   #colors
                            #just add the code
                            t_line = t_line + '\x01' + word # out = out + '\x01' + word
                            pword = False
                            extend = False
                    if space == 0:
                        space = 32
                    last = word
                if space != 0:
                    t_line = t_line + '\r'  # out = out + '\r'
            else:
                t_line = t_line + '\r'  # out = out + '\r'
            if split:
                out.append(t_line)
            else:
                out = out + t_line
        return out

    def check_fit(self, filename):
        if self.name != 'MSXstd':
            size = os.stat(filename).st_size
            if size <= 32768:
                with open(filename,'rb') as f:
                    header = f.read(16)
                if header[0:2] == b'AB':
                    return True            # Correct ID
        return False

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
        return filename


    def get_exec(self, filename):
        size = os.stat(filename).st_size
        la = 0
        bin = None
        if size <= 32768:
            with open(filename,'rb') as f:
                bin = f.read(-1)
                if bin[0:2] == b'AB':
                    init = bin[2]+(bin[3]*256)
                    statement = bin[4]+(bin[5]*256)
                    device = bin[6]+(bin[7]*256)
                    text = bin[8]+(bin[9]*256)
                    if init == 0:
                        if text != 0:
                            init = text
                        else:
                            return False
                    if size == 32768:
                        la = 0x4000
                    else:
                        if init > 0x8000:
                            la = 0x8000
                        else:
                            la = 0x4000
        return (la,bin)

    ### Encoder setup routine
    # Setup the required parameters for the given client id
    # Either automatically or by enquiring the user
    # Return None if no setup is necessary, or a customized
    # copy of the encoder object
    def setup(self, conn, id):
        if self.name == 'MSXstd':
            _copy = deepcopy(self)
            conn.SendTML('Screen columns? (37): ')
            cols = conn.ReceiveInt(29,80,37)
            conn.SendTML('<BR>Screen lines? (23): ')
            _copy.txt_geo = (cols,conn.ReceiveInt(20,24,23))
            _copy.tml_mono['SCROLL'] = (self._scroll ,[('_R','_C'),('rows',0)])
            _copy.spinner = {'start':f'<UL-CORNER>',
                'loop':['<DEL><UR-CORNER>','<DEL><LR-CORNER>','<DEL><LL-CORNER>','<DEL><UL-CORNER>'],
                'stop':'<DEL>'}                          # Spinner sequence
            return _copy
        else:
            return None
        
    ### MSX ASCII SCROLL replacement
    def _scroll(self,rows):
        if rows > 0:
            return chr(HOME)+(chr(ESC)+'M')*rows
        elif rows < 0:
            return chr(HOME)+(chr(ESC)+'L')*abs(rows)
        else:
            return ''

####################################################
# Convert ASCII/unicode text to MSX
####################################################
Urep = {'\u2014':'-','\u2013':'\u2500','\u2019':"'",'\u2018':"'",'\u201c':'"','\u201d':'"','\u2022':'\u2219',
        '\u00c3':'\u2591','\u00e3':'\u2592','\u0128':'\u2593','\u0129':'\u2502','\u00d5':'\u2524','\u00f5':'\u2561','\u0170':'\u2562','\u0171':'\u2556',
        '\u0132':'\u2555','\u0133':'\u2563','\u00be':'\u2551','\u223d':'\u2557','\u25ca':'\u255d','\u2030':'\u255c','\u00b6':'\u255b','\u00a7':'\u2510',
        '\u2300':'\u03c6','\u2208':'\u03b5'}
Urep = dict((re.escape(k), v) for k, v in Urep.items())


def toMSX(text:str,full=True):
    pattern = re.compile("|".join(Urep.keys()))
    text = pattern.sub(lambda m: Urep[re.escape(m.group(0))], text)
    text = (unicodedata.normalize('NFKC',text).encode('cp437','ignore')).decode('latin1')
    return(text)

###########################
# Convert MSX to UTF8
###########################
def toASCII(text):
    return(text.encode('latin1').decode('cp437'))

###################################
# Register with the encoder module
###################################
def _Register():
    e0 = MSXencoder('MSX1')
    e0.clients = {b'M1':'Retroterm MSX1',b'M138':'Retroterm MSX1-38K'}
    e0.tml_mono  = t_mono['MSX1']
    e0.tml_multi = t_multi['MSX1']
    e0.bbuffer = 0x02ed #Bottom of the buffer
    e0.tbuffer = 0xbfff #Top of the buffer
    e0.palette = PALETTE
    e0.colors = {'BLACK':1,'GREEN':2,'LTGREEN':3,'BLUE':4,'LTBLUE':5,'DARK_RED':6,'CYAN':7,'RED':8,'PINK':9,'YELLOW':10,
                 'LTYELLOW':11,'DARK_GREEN':12,'PURPLE':13,'GREY':14,'WHITE':15,'LIGHT_GREY':14,'DARK_GREY':14,'GREY1':14,
                 'GREY2':14,'MEDIUM_GREY':14,'ORANGE':9,'BROWN':6, 'GREY3':14,'LIGHT_BLUE':5,'LIGHT_GREEN':3,
                 'DGREEN':12,'DRED':6,'DKRED':6,'DGREEN':12}
    e0.def_gfxmode = gfxmodes.MSXSC2
    e0.gfxmodes = (gfxmodes.MSXSC2,)
    e0.ctrlkeys = {'CRSRU':chr(CRSR_UP),'CRSRD':chr(CRSR_DOWN),'CRSRL':chr(CRSR_LEFT),'CRSRR':chr(CRSR_RIGHT),
                   'F1':chr(F1),'F2':chr(F2),'F3':chr(F3),'F4':chr(F4),'F5':chr(F5),'F6':chr(F6),'F7':chr(F7),'F8':chr(F8),'F9':chr(F9),'F10':chr(F10),
                   'HOME':chr(HOME),'CLEAR':chr(CLEAR),'DELETE':chr(DELETE),'INSERT':chr(INSERT),'RVSON':chr(RVS_ON),'RVSOFF':chr(RVS_OFF)}
    e0.features['color']  = True
    e0.features['reverse'] = True

    # Non-Turbo56K encoders
    e1 = MSXencoder('MSXstd')
    e1.minT56Kver = 0
    e1.nl_out = '\r'
    e1.clients = {b'MSX0':'MSX ASCII'}
    e1.tml_mono  = t_mono['MSXSTD']
    e1.tml_multi = t_multi['MSX1'].copy()
    e1.tml_multi['DEL'] = chr(0x7f)
    e1.ctrlkeys = {'CRSRU':chr(CRSR_UP),'CRSRD':chr(CRSR_DOWN),'CRSRL':chr(CRSR_LEFT),'CRSRR':chr(CRSR_RIGHT),
                   'HOME':chr(HOME),'CLEAR':chr(CLEAR),'DELETE':chr(DELETE),'INSERT':chr(INSERT)}
    e1.features['windows'] = 0
    e1.features['bgcolor'] = 0
    e1.features['color'] = False
    e1.nl_out = '\r\n'

    return [e0,e1]  #Each encoder module can return more than one encoder object. For example here it could also return MSX2.