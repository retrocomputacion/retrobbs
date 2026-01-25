import unicodedata
import re
from common.classes import Encoder
from common.imgcvt import gfxmodes
import os
from copy import deepcopy
import codecs

#Sinclair constants

#--Control codes
GRAPH = 0x01
STOP = 0x03
RETURN = 0x0D
FLASH   = 0x12
BRIGHT  = 0x13
INVERSE = 0x14
OVER    = 0x15

#--Special chars
POUND = 0x60

#--Editor
AT = 0x16
CRSR_LEFT = 0x08
CRSR_RIGHT = 0x09
CRSR_UP = 0x0B
CRSR_DOWN = 0x0A
CLEAR = 0xFD    #0xFB
HOME = 0x0B
DELETE = 0x08

#--Foreground Colors
BLACK = 0x00
BLUE = 0x01
RED = 0x02
PURPLE = 0x03
GREEN = 0x04
CYAN = 0x05
YELLOW = 0x06
WHITE = 0x07


#--GFX
UL_QUAD = 0x82  # Semigraphics
UR_QUAD = 0x81
LL_QUAD = 0x88
LR_QUAD = 0x84
L_HALF  = 0x8A
R_HALF  = 0x85
B_HALF  = 0x8C
U_HALF  = 0x83
UL_LR_QUAD = 0x86
LL_UR_QUAD = 0x89

VLINE = 0x7C

#--Characters used by the BBS
SPINNER = 0x86  # Character to use while waiting
BACK = 0x3D     # Character to go back/exit ('=')  

# Color code to palette index dictionary
PALETTE = {'\x10'+chr(BLACK):0,'\x10'+chr(BLUE):1,'\x10'+chr(RED):2,'\x10'+chr(PURPLE):3,
           '\x10'+chr(GREEN):4,'\x10'+chr(CYAN):5,'\x10'+chr(YELLOW):6,'\x10'+chr(WHITE):7}

#--Non printable characters grouped
NONPRINTABLE = [chr(i) for i in range(0,13)]+[chr(i) for i in range(14,32)]+[chr(127)]+[chr(1)+chr(i) for i in range(1,16)]

###########
# TML tags
###########
t_mono = 	{'ZXSTD':{'CLR':chr(CLEAR),'HOME':chr(AT)+'\x00\x00','RVSON':chr(INVERSE)+'\x01','RVSOFF':chr(INVERSE)+'\x00','BR':'\r',
            'BLACK':'\x10'+chr(BLACK),'WHITE':'\x10'+chr(WHITE),'RED':'\x10'+chr(RED),'CYAN':'\x10'+chr(CYAN),'PURPLE':'\x10'+chr(PURPLE),
            'GREEN':'\x10'+chr(GREEN),'\x10'+'BLUE':'\x10'+chr(BLUE),'YELLOW':'\x10'+chr(YELLOW),
            'SPINNER':(lambda conn:conn.SetHold(),[('conn','_C')]),'BACK':chr(BACK),
            'FLASHON':chr(FLASH)+'\x01','FLASHOFF':chr(FLASH)+'\x00',
            'AT':(lambda x,y:'\x16'+chr(y)+chr(x),[('_R','_C'),('x',0),('y',0)]),
            'PAPER':(lambda c:'\x11'+chr(c),[('_R','_C'),('c',7)])} #,'INK':(lambda c:'\x10'+chr(c),[('_R','_C'),('c',7)])}
}
t_multi =	{'ZXSTD':{'CRSRL':chr(CRSR_LEFT),'CRSRU':chr(CRSR_UP),'CRSRR':chr(CRSR_RIGHT),'CRSRD':chr(CRSR_DOWN),'DEL':chr(DELETE),
            'POUND':chr(POUND),'UARROW':'^','VLINE':chr(VLINE),
            'BLOCK':'\x8F',
            'UL-QUAD':chr(UL_QUAD),'UR-QUAD':chr(UR_QUAD),'LL-QUAD':chr(LL_QUAD),'LR-QUAD':chr(LR_QUAD),'UL-LR-QUAD':chr(UL_LR_QUAD),
            'L-HALF':chr(L_HALF),'B-HALF':chr(B_HALF),'U-HALF':chr(U_HALF),'R-HALF':chr(R_HALF),
            'UL-UR-LL-QUAD':chr(0x8B),'UL-UR-LR-QUAD':chr(0x87),'UL-LL-LR-QUAD':chr(0x8E),'LL-LR-UR-QUAD':chr(0x8D)
            }}


######### Sinclair encoder subclass #########
class Sinclairencoder(Encoder):
    def __init__(self, name:str) -> None:
        super().__init__(name)
        self.encode = toSinclair    #	Function to encode from ASCII/Unicode
        self.decode = toASCII	#	Function to decode to ASCII/Unicode
        self.non_printable = NONPRINTABLE	#	List of non printable characters
        self.nl	= '\r'			#	New line string/character
        self.nl_out = '\r'      #   New line string/character (out)
        self.bs = chr(DELETE)	#	Backspace string/character
        self.txt_geo = (32,24)  #   Text screen dimensions
        self.back = chr(BACK)
        self.spinner = {'start':f'<CHR c={SPINNER}><CRSRL>',
                        'loop':None,
                        'stop':' <DEL>'}                          # Spinner sequence
        self.features = {'color':       True,   # Encoder supports color
                         'bgcolor':     2,      # Per character background color
                         'charsets':    1,      # Number if character sets supported
                         'reverse':     True,   # Encoder supports reverse video
                         'blink':       True,   # Encoder supports blink/flash text
                         'underline':   False,  # Encoder supports underlined text
                         'cursor':      True,   # Encoder supports cursor movement/set. Including home position and screen clear
                         'scrollback':  False,  # Encoder supports scrolling back (down) the screen
                         'windows':     0       # Encoder does not support screen windows
                         }

    def color_index(self, code):
        return self.palette.get(code,-1)

    ### Wordwrap text preserving control codes
    # def wordwrap(self,text,split=False):
    #     if self.nl_out == '\r\n':
    #         return super().wordwrap(text,split)
    #     codes = ''.join(chr(i) for i in range(1,16))+''.join(chr(i) for i in range(17,32))  #'\x01\x07\x08\x0b\x12\x19\x1a\x1c\x1d\x1e\x1f\x7f'

    #     out = ''
    #     extend = False

    #     # Replace Yellow color code before splitting by lines
    #     for c in text:
    #         if extend == False:
    #             if ord(c) == 1:
    #                extend = True
    #             out = out + c
    #         else:
    #             if c == '\r':
    #                 out = out  + '\xff'
    #             else:
    #                 out = out + c
    #             extend = False
    #     text = out

    #     if split:
    #         out = []
    #     else:
    #         out = ''

    #     lines = text.split('\r')
    #     extend = False
    #     for line in lines:
    #         line = line.replace('\x01\xff','\x01\x0a')  # replace back the YELLOW color code
    #         t_line = ''
    #         if len(line)!=0:
    #             space = 32  # Space left in line
    #             line = re.sub(r'(['+codes+r'])',r'\020\1\020', line)
    #             line = line if line[0]!='\x10' else line[1:]
    #             words = re.split(r'\020+| ',line) # words = line.split(' ')
    #             pword = False
    #             for word in words:
    #                 if len(word) == 0:
    #                     t_line = t_line + ' '   # out = out + ' ' # Add space if last item was a word or a space 
    #                     pword= False
    #                     space -=1
    #                 elif not extend:
    #                     if  (32 <= ord(word[0]) <= 126) or (128 <= ord(word[0]) <= 253):   # Normal Printable
    #                         if pword:
    #                             pword = False
    #                             space -= 1
    #                             t_line = t_line + ' '   # out = out + ' ' # Add space if last word was a _word_
    #                             if space == 0:
    #                                 space = 32
    #                         if space - len(word) < 0:
    #                             t_line = t_line + '\r'  # out = out + '\r' + word
    #                             if split:
    #                                 out.append(t_line)
    #                             else:
    #                                 out = out + t_line
    #                             t_line = word
    #                             space = 32 - len(word)
    #                         else:
    #                             t_line = t_line + word  # out = out + word
    #                             space -= len(word)
    #                         #Add space
    #                         if space != 0:
    #                             pword = True
    #                     elif word[0] == '\x01': #GRAPH
    #                         extend = True
    #                     elif word[0] in '\x1e\x1f\x19\x1a\x7f\x12': #crsr up/down, RVSON/OFF, INSERT, DEL
    #                         #just add the code
    #                         t_line = t_line + word  # out = out + word
    #                         pword = False
    #                     elif word[0] in '\x0b\x0c': #HOME CLR
    #                         t_line = t_line + word  # out = out + word
    #                         space = 32
    #                         pword = False
    #                     elif word[0] in '\x08\x1d': #BS, crsr left
    #                         t_line = t_line + word  # out = out + word
    #                         space = space+1 if space+1 <= 32 else 1 # <- take into account going around to the previous line (being already at home not taken into account)
    #                         pword = False
    #                     elif word[0] == '\x1c': #crsr right
    #                         t_line = t_line + word# out = out + word
    #                         space -= 1
    #                     else:
    #                         pword = False
    #                 else:
    #                     if 64 <= ord(word[0]) <= 97:    #Extended gfx
    #                         if pword:
    #                             pword = False
    #                             space -= 1
    #                             t_line = t_line + ' '   # out = out + ' ' # Add space if last word was a _word_
    #                             if space == 0:
    #                                 space = 32
    #                         if space - len(word) < 0:
    #                             t_line = t_line + '\r'  # out = out + '\r' + '\x01'+ word
    #                             if split:
    #                                 out.append(t_line)
    #                             else:
    #                                 out = out + t_line
    #                             t_line = '\x01' + word
    #                             space = 32 - len(word)
    #                         else:
    #                             t_line = t_line + '\x01' + word # out = out + '\x01' + word
    #                             space -= len(word)
    #                         #Add space
    #                         if space != 0:
    #                             pword = True
    #                         extend = False
    #                     elif (1 <= ord(word[0]) <= 15) or (17 <= ord(word[0]) <= 31):   #colors
    #                         #just add the code
    #                         t_line = t_line + '\x01' + word # out = out + '\x01' + word
    #                         pword = False
    #                         extend = False
    #                 if space == 0:
    #                     space = 32
    #                 last = word
    #             if space != 0:
    #                 t_line = t_line + '\r'  # out = out + '\r'
    #         else:
    #             t_line = t_line + '\r'  # out = out + '\r'
    #         if split:
    #             out.append(t_line)
    #         else:
    #             out = out + t_line
    #     return out

    # def check_fit(self, filename):
    #     size = os.stat(filename).st_size
    #     if size <= 32768:
    #         with open(filename,'rb') as f:
    #             header = f.read(16)
    #         if header[0:2] == b'AB':
    #             return True            # Correct ID
    #     return False

    # Sanitize a given filename for compatibility with the client's filesystem
    # Input and output strings are not encoded
    # outout 8.3 filename
    # def sanitize_filename(self, filename):
    #     def find_ext():
    #         nonlocal tmp,ext
    #         tl = len(tmp)-1
    #         for i in range(tl):
    #             tp = tmp.pop()
    #             if len(tp.replace(' ','')) > 0:
    #                 t_ext = tp.split(' ')
    #                 for j in range(len(t_ext)+1):
    #                     if len(t_ext[-j]) > 0:
    #                         ext = t_ext[-j][:3]
    #                         break
    #                 break

    #     filename = (unicodedata.normalize('NFKD',filename).encode('ascii','replace')).decode('ascii')
    #     filename = filename.translate({ord(i): '_' for i in ':*?"$,+;<=>/\\[]|'})
    #     tmp = filename.split('.')
    #     ext = ''
    #     if len(tmp) > 1:
    #         find_ext()
    #     else:
    #         tmp = tmp[0].split(' ')
    #         if len(tmp) > 1:
    #             find_ext()
    #     filename = '_'.join(tmp).replace(' ','_')[:8]
    #     if ext != '':
    #         filename += '.'+ext
    #     print(filename)
    #     return filename


    # def get_exec(self, filename):
    #     size = os.stat(filename).st_size
    #     la = 0
    #     bin = None
    #     if size <= 32768:
    #         with open(filename,'rb') as f:
    #             bin = f.read(-1)
    #             if bin[0:2] == b'AB':
    #                 init = bin[2]+(bin[3]*256)
    #                 statement = bin[4]+(bin[5]*256)
    #                 device = bin[6]+(bin[7]*256)
    #                 text = bin[8]+(bin[9]*256)
    #                 if init == 0:
    #                     if text != 0:
    #                         init = text
    #                     else:
    #                         return False
    #                 if size == 32768:
    #                     la = 0x4000
    #                 else:
    #                     if init > 0x8000:
    #                         la = 0x8000
    #                     else:
    #                         la = 0x4000
    #     return (la,bin)

    ### Encoder setup routine
    # Setup the required parameters for the given client id
    # Either automatically or by enquiring the user
    # Return None if no setup is necessary, or a customized
    # copy of the encoder object
    def setup(self, conn, id):
        if self.name == 'ZXstd':
            _copy = deepcopy(self)
            conn.SendTML('Timex 2068 mode (y/n):')
            if conn.ReceiveKey('yn') == 'y':
                _copy.name = 'TSstd'
                _copy.encode = toTimex
                _copy.tml_multi.pop('VLINE',None)
                conn.SendTML('<BR>Screen columns? (32): ')
                cols = conn.ReceiveInt(32,64,32)
                conn.SendTML('<BR>Screen lines? (22): ')
                _copy.txt_geo = (cols,conn.ReceiveInt(20,24,22))
            return _copy
        else:
            return None
        
    ### Sinclair ASCII SCROLL replacement
    # def _scroll(self,rows):
    #     if rows > 0:
    #         return chr(HOME)+(chr(ESC)+'M')*rows
    #     elif rows < 0:
    #         return chr(HOME)+(chr(ESC)+'L')*abs(rows)
    #     else:
    #         return ''

####################################################
# Convert ASCII/unicode text to Sinclair
####################################################
# Multiple replace
# https://stackoverflow.com/questions/6116978/how-to-replace-multiple-substrings-of-a-string
Urep = {'\u00d7':'x','\u00f7':'/','\u2014':'-','\u2013':'-','\u2019':"'",'\u2018':"'",'\u201c':'"','\u201d':'"','\u2022':'*','\u00A3':'\x60','\u00A9':'\x7F'}
UrepTS = Urep.copy()
UrepTS['|'] = 'I'
UrepTS['~'] = ' '
Urep = dict((re.escape(k), v) for k, v in Urep.items())

def toSinclair(text:str,full=True):
    pattern = re.compile("|".join(Urep.keys()))
    text = pattern.sub(lambda m: Urep[re.escape(m.group(0))], text)
    text = (unicodedata.normalize('NFKD',text).encode('ascii','zxspc')).decode('latin1')
    return(text)

def toTimex(text:str,full=True):
    pattern = re.compile("|".join(Urep.keys()))
    text = pattern.sub(lambda m: Urep[re.escape(m.group(0))], text)
    text = (unicodedata.normalize('NFKD',text).encode('ascii','zxspc')).decode('latin1')
    return(text)


###########################
# Convert Sinclair to UTF8
###########################
def toASCII(text):
    return(text.encode('latin1').decode('ascii'))

######### Sinclair ASCII codec error handler #########
# Replace unknowns with a space
def zxhandler(e):
    char = b''
    if type(e) == UnicodeEncodeError:
        if e.object[e.start] in '¿¡':
            char = b' '
    elif type(e) == UnicodeDecodeError:
        ...
    return (char,e.end)

###################################
# Register with the encoder module
###################################
def _Register():
    codecs.register_error('zxspc',zxhandler)  # Register encoder error handler. 
    # e0 = Sinclairencoder('ZX1')
    # e0.clients = {b'Z1':'Retroterm ZX',b'TS':'Retroterm 2048'}
    # e0.tml_mono  = t_mono['ZX1']
    # e0.tml_multi = t_multi['ZX1']
    # e0.bbuffer = 0x02ed #Bottom of the buffer
    # e0.tbuffer = 0xbfff #Top of the buffer
    # e0.palette = PALETTE
    # e0.colors = {'BLACK':1,'GREEN':2,'LTGREEN':3,'BLUE':4,'LTBLUE':5,'DARK_RED':6,'CYAN':7,'RED':8,'PINK':9,'YELLOW':10,
    #              'LTYELLOW':11,'DARK_GREEN':12,'PURPLE':13,'GREY':14,'WHITE':15,'LIGHT_GREY':14,'DARK_GREY':14,'GREY1':14,
    #              'GREY2':14,'MEDIUM_GREY':14,'ORANGE':9,'BROWN':6, 'GREY3':14,'LIGHT_BLUE':5,'LIGHT_GREEN':3,
    #              'DGREEN':12,'DRED':6,'DKRED':6,'DGREEN':12}
    # # e0.def_gfxmode = gfxmodes.MSXSC2
    # # e0.gfxmodes = (gfxmodes.MSXSC2,)
    # e0.ctrlkeys = {'CRSRU':chr(CRSR_UP),'CRSRD':chr(CRSR_DOWN),'CRSRL':chr(CRSR_LEFT),'CRSRR':chr(CRSR_RIGHT),
    #                'HOME':chr(HOME),'CLEAR':chr(CLEAR),'DELETE':chr(DELETE)}
    # e0.features['color']  = True
    # e0.features['reverse'] = True

    # Non-Turbo56K encoders
    e1 = Sinclairencoder('ZXstd')
    e1.minT56Kver = 0
    e1.palette = PALETTE
    e1.colors = {'BLACK':0,'BLUE':1,'RED':2,'PURPLE':3,'GREEN':4,'CYAN':5,'YELLOW':6,'WHITE':7}
    e1.clients = {b'ZX0':'Sinclair ASCII'}
    e1.tml_mono  = t_mono['ZXSTD']
    e1.tml_multi = t_multi['ZXSTD']
    # e1.tml_multi['DEL'] = chr(0x7f)
    e1.ctrlkeys = {'CRSRU':chr(CRSR_UP),'CRSRD':chr(CRSR_DOWN),'CRSRL':chr(CRSR_LEFT),'CRSRR':chr(CRSR_RIGHT),
                   'HOME':chr(HOME),'CLEAR':chr(CLEAR),'DELETE':chr(DELETE)}
    e1.features['windows'] = 0
    e1.features['bgcolor'] = 0
    e1.features['color'] = True
    e1.features['reverse'] = True

    return [e1]  #Each encoder module can return more than one encoder object.