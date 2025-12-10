#####################
#Turbo56K - Protocol#
#####################

#Constants
CMDON = 0xFF    # Enters command mode
CMDOFF = 0xFE   # Exits command mode

LADDR       = 0x80  # Transfer Address - Parameters: addr-lo, addr-hi
PRADDR      = 0x81  # Preset Transfer Address - Parameter: Preset number
BLKTR       = 0x82  # Transfer block - Parameters: lenght-lo, lenght-hi
STREAM      = 0x83  # Audio Stream, byte 0 stops the stream
SIDSTREAM   = 0x84  # SID Stream (Chiptune stream alias)
CHIPSTREAM  = 0x84  # Chiptune Stream
SIDORD      = 0x85  # Set the register write order for the SID Stream
FILETR      = 0x86  # File Transfer

TEXT        = 0x90  # Set Text mode - Parameters: page, border, background
HIRES       = 0x91  # Set Hi-Res bitmap mode - Parameters: page, border
MULTI       = 0x92  # Set Multicolor bitmap mode - Parameters: page, border, background

SCNCLR      = 0x98  # Clear graphic screen
PENCOLOR    = 0x99  # Set Pen color
PLOT        = 0x9A  # Plot point
LINE        = 0x9B  # Draw line
BOX         = 0x9C  # Draw (filled) box
CIRCLE      = 0x9D  # Draw circle
FILL        = 0x9E  # Flood fill

SCREEN      = 0xA0  # Set the screen as output device, exits command mode
SPEECH      = 0xA1  # Set the speech synthetizer as output device, exits command mode.

VERSION     = 0xA2  # Queries de client for ID and version
QUERYCMD    = 0xA3  # Queries the client if a given command exists
QUERYCLIENT = 0xA4  # Queries the client's setup

SET_CRSR    = 0xB0  # Sets cursor position, exits command mode: Parameters: column, row
LINE_FILL   = 0xB1
CURSOR_EN   = 0xB2  # Enables or disables cursor blink - Paramater: cursor enable
SPLIT_SCR   = 0xB3  # Splits screen - Parameters: split line/graphic mode, background colors
GET_CRSR    = 0xB4  # Get cursor position, exits command mode
SET_WIN     = 0xB5  # Sets Text window limits - Parameters: window top and window bottom lines
SCROLL      = 0xB6  # Scroll text window - Parameter: number of rows to scroll, signed
INK         = 0xB7  # Set ink color - Parameter: Color index

TURBO56K_LCMD = 0xB7 # Highest CMD number implemented

# Command descriptors
T56K_CMD = {0x80:'Custom transfer address', 0x81:'Preset transfer address', 0x82:'Block transfer', 0x83:'PCM audio stream', 0x84:'Chiptune stream', 0x85:'SID register write order', 0x86:'File transfer',
            0x90:'Set text mode', 0x91:'Set Hi-Res bitmap mode', 0x92:'Set multicolor bitmap mode',
            0x98:'Clear graphic screen',0x99:'Set pen color',0x9A:'Plot point',0x9B:'Line',0x9C:'Box',0x9D:'Circle/Ellipse',0x9E:'Fill',
            0xA0:'Set screen as output', 0xA1:'Set voice synth as output', 0xA2:'Terminal ID', 0xA3:'Command query', 0xA4:'Query setup',
            0xB0:'Set cursor', 0xB1:'Line fill', 0XB2:'Cursor enable', 0xB3:'Split screen', 0xB4:'Get cursor', 0xB5:'Set window', 0xB6:'Scroll window', 0xB7:'Set ink color'}

# Old Turbo56K <v0.6 feature matrix
T56Kold =  [b'\x02',b'\x01',b'\x02',b'\x00',b'\x00',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',
            b'\x03',b'\x02',b'\x03',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',
            b'\x00',b'\x00',b'\x00',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',
            b'\x02',b'\x02',b'\x01',b'\x02',b'\x80',b'\x02',b'\x80',b'\x80']

###################################################

def to_Text(page, border, background, bin = False):
    if bin == True:
        return bytes([0x00,CMDON,TEXT,page,border,background,CMDOFF])
    else:
        return chr(0)+chr(CMDON)+chr(TEXT)+chr(page)+chr(border)+chr(background)+chr(CMDOFF)

def to_Hires(page,border, bin = False):
    if bin == True:
        return bytes([0x00,CMDON,HIRES,page,border,CMDOFF])
    else:
        return chr(0)+chr(CMDON)+chr(HIRES)+chr(page)+chr(border)+chr(CMDOFF)

def to_Multi(page, border, background, bin = False):
    if bin == True:
        return bytes([0x00,CMDON,MULTI,page,border,background,CMDOFF])
    else:
        return chr(0)+chr(CMDON)+chr(MULTI)+chr(page)+chr(border)+chr(background)+chr(CMDOFF)

def customTransfer(address, bin = False):
    if bin == True:
        return bytes([CMDON,LADDR,address & 256,address // 256,CMDOFF])
    else:
        return(chr(CMDON)+chr(LADDR)+chr(address & 256)+chr(address // 256)+chr(CMDOFF))

def presetTransfer(preset, bin= False):
    if bin == True:
        return bytes([CMDON,PRADDR,preset,CMDOFF])
    else:
        return chr(CMDON)+chr(PRADDR)+chr(preset)+chr(CMDOFF)

def blockTransfer(data):    #Only as binary
    return bytes([CMDON,BLKTR,len(data),data,CMDOFF])

def to_Screen(bin = False):
    if bin == True:
        return(bytes([CMDON,SCREEN]))
    else:
        return chr(CMDON)+chr(SCREEN)

# Reset some Turbo56K parameters: cursor, split screen and text window
def reset_Turbo56K(bin = False):
    if bin == True:
        return bytes([CMDON,CURSOR_EN,1,CMDOFF,CMDON,SPLIT_SCR,0,0,CMDOFF,CMDON,SET_WIN,0,24,CMDOFF,CMDON,SCREEN])
    else:
        return chr(CMDON)+chr(CURSOR_EN)+chr(1)+chr(CMDOFF)+chr(CMDON)+chr(SPLIT_SCR)+chr(0)+chr(0)+chr(CMDOFF)+chr(CMDON)+chr(SET_WIN)+chr(0)+chr(24)+chr(CMDOFF)+chr(CMDON)+chr(SCREEN)

def to_Speech(bin = False):
    if bin == True:
        return bytes([CMDON,SPEECH])
    else:
        return chr(CMDON)+chr(SPEECH)

def set_CRSR(column, row, bin= False):
    if column > 39:
        column = 39
    if row > 24:
        row = 24
    if bin == True:
        return bytes([0x00,CMDON,SET_CRSR,column,row])
    else:
        return chr(0)+chr(CMDON)+chr(SET_CRSR)+chr(column)+chr(row)

def Fill_Line(row, char, bin= False):
    if row > 24:
        row = 24
    if bin == True:
        return bytes([CMDON,LINE_FILL,row,char,CMDOFF])
    else:
        return chr(CMDON)+chr(LINE_FILL)+chr(row)+chr(char)+chr(CMDOFF)

def enable_CRSR(bin = False):
    if bin == True:
        return bytes([CMDON,CURSOR_EN,1,CMDOFF])
    else:
        return chr(CMDON)+chr(CURSOR_EN)+chr(1)+chr(CMDOFF) 

def disable_CRSR(bin = False):
    if bin == True:
        return bytes([CMDON,CURSOR_EN,0,CMDOFF])
    else:
        return chr(CMDON)+chr(CURSOR_EN)+chr(0)+chr(CMDOFF) 

def split_Screen(line, multi, bgtop, bgbottom, mctop = 0, bin = False, mode:str='PET64'):
    if line < 0:
        line = 1
    elif line > 24:
        line = 24
    if line != 0 and multi == True:
        line += 128
    if line != 0: 
        if mode != 'PET264':
            par2 = bgtop+(16*bgbottom)
        else:
            line += 32
            par2 = bgtop
    else:
        par2 = 0
    if bin == True:
        ret = bytes([CMDON,SPLIT_SCR,line,par2])
        if line != 0 and mode == 'PET264':
            ret += bytes([bgbottom,mctop])
        ret += bytes([CMDOFF])
    else:
        ret = chr(CMDON)+chr(SPLIT_SCR)+chr(line)+chr(par2)
        if line !=0 and mode == 'PET264':
            ret += chr(bgbottom)+chr(mctop)
        ret += chr(CMDOFF)
    return ret

def set_Window(top, bottom,bin = False):
    if bin == True:
        return bytes([CMDON,SET_WIN,top,bottom,CMDOFF])
    else:
        return chr(CMDON)+chr(SET_WIN)+chr(top)+chr(bottom)+chr(CMDOFF) 

def scroll(rows,bin = False):
    rows = ord(max(min(127,rows),-128).to_bytes(1,'little',signed=True))
    if bin:
        return bytes([CMDON,SCROLL,rows,CMDOFF])
    else:
        return chr(CMDON)+chr(SCROLL)+chr(rows)+chr(CMDOFF) 
    
def set_ink(color, bin= False):
    if bin:
        return bytes([CMDON,INK,color])
    else:
        return chr(CMDON)+chr(INK)+chr(color) 
    
def screen_clear(bin=False):
    if bin:
        return bytes([CMDON,SCNCLR,CMDOFF])
    else:
        return chr(CMDON)+chr(SCNCLR)+chr(CMDOFF) 

def pen_color(pen,color,bin = False):
    pen &= 255
    color &= 255
    if bin:
        return bytes([CMDON,PENCOLOR,pen,color,CMDOFF])
    else:
        return chr(CMDON)+chr(PENCOLOR)+chr(pen)+chr(color)+chr(CMDOFF)
    
def plot(pen,x,y,bin = False):
    pen &= 255
    x = x.to_bytes(2,'little',signed=True)
    y = y.to_bytes(2,'little',signed=True)
    if bin:
        return bytes([CMDON,PLOT,pen,x[0],x[1],y[0],y[1],chr(CMDOFF)])
    else:
        return chr(CMDON)+chr(PLOT)+chr(pen)+x.decode('latin1')+y.decode('latin1')+chr(CMDOFF)

def line(pen,x1,y1,x2,y2,bin = False):
    pen &= 255
    x1 = x1.to_bytes(2,'little',signed=True)
    y1 = y1.to_bytes(2,'little',signed=True)
    x2 = x2.to_bytes(2,'little',signed=True)
    y2 = y2.to_bytes(2,'little',signed=True)
    if bin:
        return bytes([CMDON,LINE,pen,x1[0],x1[1],y1[0],y1[1],x2[0],x2[1],y2[0],y2[1],chr(CMDOFF)])
    else:
        return chr(CMDON)+chr(LINE)+chr(pen)+x1.decode('latin1')+y1.decode('latin1')+x2.decode('latin1')+y2.decode('latin1')+chr(CMDOFF)

def box(pen,x1,y1,x2,y2,fill = False,bin = False):
    pen &= 255
    fill = (1 if fill else 0)
    x1 = x1.to_bytes(2,'little',signed=True)
    y1 = y1.to_bytes(2,'little',signed=True)
    x2 = x2.to_bytes(2,'little',signed=True)
    y2 = y2.to_bytes(2,'little',signed=True)
    if bin:
        return bytes([CMDON,BOX,pen,x1[0],x1[1],y1[0],y1[1],x2[0],x2[1],y2[0],y2[1],fill,chr(CMDOFF)])
    else:
        return chr(CMDON)+chr(BOX)+chr(pen)+x1.decode('latin1')+y1.decode('latin1')+x2.decode('latin1')+y2.decode('latin1')+chr(fill)+chr(CMDOFF)

def circle(pen,x,y,rx,ry,bin = False):
    pen &= 255
    x = x.to_bytes(2,'little',signed=True)
    y = y.to_bytes(2,'little',signed=True)
    rx = (rx & 65535).to_bytes(2,'little')
    ry = (ry & 65535).to_bytes(2,'little')
    if bin:
        return bytes([CMDON,CIRCLE,pen,x[0],x[1],y[0],y[1],rx[0],rx[1],ry[0],ry[1],chr(CMDOFF)])
    else:
        return chr(CMDON)+chr(CIRCLE)+chr(pen)+x.decode('latin1')+y.decode('latin1')+rx.decode('latin1')+ry.decode('latin1')+chr(CMDOFF)

def fill(pen,x,y,bin = False):
    pen &= 255
    x = x.to_bytes(2,'little',signed=True)
    y = y.to_bytes(2,'little',signed=True)
    if bin:
        return bytes([CMDON,FILL,pen,x[0],x[1],y[0],y[1],chr(CMDOFF)])
    else:
        return chr(CMDON)+chr(FILL)+chr(pen)+x.decode('latin1')+y.decode('latin1')+chr(CMDOFF)

#################################################################################
# TML tags (Added at TML parser creation time only if the client supports them)
#################################################################################
turbo_tags = {'SETOUTPUT':(lambda o: to_Screen() if o else to_Speech(),[('_R','_C'),('o',True)]),
          'TEXT':(to_Text,[('_R','_C'),('page',0),('border',0),('background',0)]),
          'GRAPHIC':(lambda mode,page,border,background: to_Multi(page,border,background) if mode else to_Hires(page,border),[('_R','_C'),('mode',False),('page',0),('border',0),('background',0)]),
          'RESET':(reset_Turbo56K,[('_R','_C')]),
          'LFILL':(Fill_Line,[('_R','_C'),('row',0),('code',0)]),
          'CURSOR':(lambda enable: enable_CRSR() if enable else disable_CRSR(),[('_R','_C'),('enable',True)]),
          'WINDOW':(set_Window,[('_R','_C'),('top',0),('bottom',24)]),
          'SPLIT':(split_Screen,[('_R','_C'),('row',0),('multi',False),('bgtop',0),('bgbottom',0),('mctop',0),('bin',False),('mode','PET64')]),
          'SCROLL':(scroll,[('_R','_C'),('rows',0)]),
          'AT':(set_CRSR,[('_R','_C'),('x',0),('y',0)]),
          'SCNCLR':(screen_clear,[('_R','_C')]),
          'PENCOLOR':(pen_color,[('_R','_C'),('pen',1),('color',0)]),
          'PLOT':(plot,[('_R','_C'),('pen',1),('x',0),('y',0)]),
          'LINE':(line,[('_R','_C'),('pen',1),('x1',0),('y1',0),('x2',0),('y2',0)]),
          'BOX':(box,[('_R','_C'),('pen',1),('x1',0),('y1',0),('x2',0),('y2',0),('fill',False)]),
          'CIRCLE':(circle,[('_R','_C'),('pen',1),('x',0),('y',0),('rx',0),('ry',0)]),
          'FILL':(fill,[('_R','_C'),('pen',1),('x',0),('y',0)])
         }