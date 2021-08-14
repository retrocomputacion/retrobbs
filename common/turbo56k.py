#####################
#Turbo56K - Protocol#
#####################

#Constants

CMDON = 0xFF    #Enters command mode
CMDOFF = 0xFE   #Exits command mode

LADDR = 0x80    #Transfer Address - Parameters: addr-lo, addr-hi
PRADDR = 0x81   #Preset Transfer Address - Parameter: Preset number
BLKTR = 0x82    #Transfer block - Parameters: lenght-lo, lenght-hi
STREAM = 0x83   #Audio Stream, byte 0 stops the stream
SIDSTREAM = 0x84 #SID Stream

TEXT = 0x90     #Set Text mode - Parameters: page, border, background
HIRES = 0x91    #Set Hi-Res bitmap mode - Parameters: page, border
MULTI = 0x92    #Set Multicolor bitmap mode - Parameters: page, border, background

SCREEN = 0xA0   #Set the screen as output device, exits command mode
SPEECH = 0xA1   #Set the speech synthetizer as output device, exits command mode.

VERSION = 0xA2  #Queries de client for ID and version

SET_CRSR = 0xB0 #Sets cursor position, exits command mode: Parameters: column, row

LINE_FILL = 0xB1

CURSOR_EN = 0xB2 #Enables or disables cursor blink - Paramater: cursor enable

SPLIT_SCR = 0xB3 #Splits screen - Parameters: split line/graphic mode, background colors

SET_WIN = 0xB5 #Sets Text window limits - Parameters: window top and window bottom lines


def to_Text(page, border, background, bin = False):
    if bin == True:
        return(bytes([CMDON,TEXT,page,border,background,CMDOFF]))
    else:
        return(chr(CMDON)+chr(TEXT)+chr(page)+chr(border)+chr(background)+chr(CMDOFF))

def to_Hires(page,border, bin = False):
    if bin == True:
        return(bytes([CMDON,HIRES,page,border,CMDOFF]))
    else:
        return(chr(CMDON)+chr(HIRES)+chr(page)+chr(border)+chr(CMDOFF))

def to_Multi(page, border, background, bin = False):
    if bin == True:
        return(bytes([CMDON,MULTI,page,border,background,CMDOFF]))
    else:
        return(chr(CMDON)+chr(MULTI)+chr(page)+chr(border)+chr(background)+chr(CMDOFF))

def customTransfer(address, bin = False):
    if bin == True:
        return(bytes([CMDON,LADDR,address & 256,address // 256,CMDOFF]))
    else:
        return(chr(CMDON)+chr(LADDR)+chr(address & 256)+chr(address // 256)+chr(CMDOFF))

def presetTransfer(preset, bin= False):
    if bin == True:
        return(bytes([CMDON,PRADDR,preset,CMDOFF]))
    else:
        return(chr(CMDON)+chr(PRADDR)+chr(preset)+chr(CMDOFF))

def blockTransfer(data):    #Only as binary
    return(bytes([CMDON,BLKTR,len(data),data,CMDOFF]))

def to_Screen(bin = False):
    if bin == True:
        return(bytes([CMDON,SCREEN]))
    else:
        return(chr(CMDON)+chr(SCREEN))

def to_Speech(bin = False):
    if bin == True:
        return(bytes([CMDON,SPEECH]))
    else:
        return(chr(CMDON)+chr(SPEECH))

def set_CRSR(column, row, bin= False):
    if column > 39:
        column = 39
    if row > 24:
        row = 24
    if bin == True:
        return(bytes([CMDON,SET_CRSR,column,row]))
    else:
        return(chr(CMDON)+chr(SET_CRSR)+chr(column)+chr(row))

def Fill_Line(row, char, bin= False):
    if row > 24:
        row = 24
    if bin == True:
        return(bytes([CMDON,LINE_FILL,row,char,CMDOFF]))
    else:
        return(chr(CMDON)+chr(LINE_FILL)+chr(row)+chr(char)+chr(CMDOFF))

def enable_CRSR(bin = False):
    if bin == True:
        return(bytes([CMDON,CURSOR_EN,1,CMDOFF]))
    else:
        return(chr(CMDON)+chr(CURSOR_EN)+chr(1)+chr(CMDOFF))

def disable_CRSR(bin = False):
    if bin == True:
        return(bytes([CMDON,CURSOR_EN,0,CMDOFF]))
    else:
        return(chr(CMDON)+chr(CURSOR_EN)+chr(0)+chr(CMDOFF))

def split_Screen(line, multi, bgtop, bgbottom, bin = False):
    if line < 0:
        line = 1
    elif line > 24:
        line = 24
    if line != 0 and multi == True:
        line += 128
    par2 = bgtop+(16*bgbottom)
    if bin == True:
        return(bytes([CMDON,SPLIT_SCR,line,par2,CMDOFF]))
    else:
        return(chr(CMDON)+chr(SPLIT_SCR)+chr(line)+chr(par2)+chr(CMDOFF))

def set_Window(top, bottom,bin = False):
    if bin == True:
        return(bytes([CMDON,SET_WIN,top,bottom,CMDOFF]))
    else:
        return(chr(CMDON)+chr(SET_WIN)+chr(top)+chr(bottom)+chr(CMDOFF))