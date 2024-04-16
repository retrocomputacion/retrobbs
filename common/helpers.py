############## Helpers ##############
# BBS stuff needed by external  	#
# modules that dont belong anywhere #
# else								#
#############################################################################
# Changelog:																#
#																			#
#	April  6-2021:	More() can now correctly print text with color codes	#
#					and a few other PETSCII control codes					#
#############################################################################


import textwrap
import itertools
import os
import re

from common.connection import Connection
from common import turbo56k as TT
from common.style import KeyPrompt
from html import unescape, escape
from PIL import ImageFont


# Bitmap Fonts
font_bold = ImageFont.truetype("common/karen2blackint.ttf", 16)
font_big = ImageFont.truetype("common/karen2blackint.ttf", 24)
font_text = ImageFont.truetype("common/BetterPixels.ttf",16)

# Valid keys for menu entries
valid_keys = 'abcdefghijklmnopqrstuvwxyz1234567890\\*;/'

# Date format strings
date_strings = [["%d/%m/%Y","dd/mm/yyyy"],["%m/%d/%Y","mm/dd/yyyy"],["%Y/%m/%d","yyyy/mm/dd"]]

# convert int to Byte
_byte = lambda i: i.to_bytes(1,'little')

###################################
# Paginate current menu
###################################
def SetPage(conn:Connection,page):
    if conn.MenuParameters != {}:
        conn.MenuParameters['current'] = page


################################
# Go back to previous/main menu
################################
def MenuBack(conn:Connection):
    conn.MenuDefs,conn.menu = conn.MenuStack[-1]#0
    conn.MenuStack.pop()
    conn.waitkey = False
    #reset menuparameters
    conn.MenuParameters = {}

#########################################################################
# Format text to X columns with wordwrapping
# Returns a list of text lines
# New in v0.5:	No encoding conversion is ever performed
#########################################################################
def formatX(text, columns = 40, convert = True):
    output = []
    text = unescape(text)
    for i in text.replace('\r','\n').split('\n'):
        if i != '':
            output.extend(textwrap.wrap(i,width=columns))
        else:
            output.extend([''])
    for i in range(len(output)):
        if len(output[i])<columns:
            output[i] = escape(output[i])
            output[i] += '<BR>'
        else:
            output[i] = escape(output[i])
    return(output)

#####################################################
# Text pagination
#####################################################
def More(conn:Connection, text, lines, colors=None):

    if colors == None:
        colors = conn.style
    conn.SendTML(f'<INK c={colors.TxtColor}>')
    ckeys = conn.encoder.ctrlkeys
    scwidth,scheight = conn.encoder.txt_geo
    if isinstance(text, list):
        l = 0
        tcolor = colors.TxtColor
        for t in text:
            conn.SendTML(t)
            # Find last text color
            tcolor = conn.parser.color
            l+=1
            if l==(lines-1):
                k= conn.SendTML(f'''<INK c={colors.PbColor}>[<INK c={colors.PtColor}>RETURN or <BACK><INK c={colors.PbColor}>]
<INKEYS k="&#13;_" _R=_S><IF c="_S=='&#13;'"><DEL n=13><INK c={tcolor}></IF>''')
                if conn.connected == False:
                    return(-1)
                if k['_S'] == '_':
                    return(-1)
                l = 0
        conn.SendTML(f'<INK c={colors.PbColor}>[<INK c={colors.PtColor}>RETURN<INK c={colors.PbColor}>]<INKEYS>')
    else:
        prompt='RETURN'
        cc=0
        ll=0
        page = 0
        rvs = ''
        color = ''
        pp = False
        for char in text:
            pp = False
            conn.Sendall(char)
            #Keep track of cursor position
            if ord(char) in itertools.chain(range(32,128),range(160,256)): #Printable chars
                cc += 1
            elif char == chr(ckeys['CRSRR']):
                cc += 1
            elif ord(char) in [ckeys['CRSRL'], ckeys['DELETE']]:
                cc -= 1
            elif char == chr(ckeys['CRSRU']):
                ll -= 1
            elif char == chr(ckeys['CRSRD']):
                ll += 1
            elif char == conn.encoder.nl:
                ll += 1
                cc = 0
                rvs = ''
            elif ord(char) == [ckeys['HOME'], ckeys['CLEAR']]:
                ll = 0
                page = 0
                cc = 0
            elif ord(char) in conn.encoder.palette:
                color = conn.encoder.palette[ord(char)]	#char
            elif char == chr(ckeys['RVSON']):
                rvs = '<RVSON>'
            elif char == chr(ckeys['RVSOFF']):
                rvs = ''
            elif char == chr(ckeys.get('LOWER',0)):
                prompt = 'RETURN'
            elif char == chr(ckeys.get('UPPER',0)):
                prompt = 'return'
            if cc == scwidth:
                cc = 0
                ll += 1
            elif cc < 0:
                if ll!=lines*page:
                    cc = scheight-1
                    ll -= 1
                else:
                    cc = 0
            if ll < lines*page:
                ll = lines*page
            elif ll >= (lines*page)+(lines-1):
                if cc !=0:
                    conn.Sendall('\r')
                conn.SendTML(KeyPrompt(conn,prompt+' OR <BACK>',TML=True))
                k = conn.ReceiveKey(b'\r_')
                if (conn.connected == False) or (k == b'_'):
                    conn.Sendall(TT.set_Window(0,scheight-1))
                    return -1
                conn.SendTML(f'<DEL n=13>{rvs}<INK c={color}><AT x={cc} y={(22-lines)+ll-(lines*page)}>')
                page += 1
                pp = True
        if cc !=0:
            conn.Sendall('\r')
        if not pp:
            conn.SendTML(f'<KPROMPT t={prompt}>')
            conn.ReceiveKey()
    return(0)

##########################################################################################
# Bidirectional scroll text display
# needs Turbo56K >= 0.7 for single line scroll up/down. Otherwise just whole page up/down
##########################################################################################
def text_displayer(conn:Connection, text, lines, colors=None, ekeys=''):

    if colors == None:
        colors = conn.style
    #initialize line color list
    lcols = [colors.TxtColor]*len(text)
    tcolor = lcols[0]

    ekeys = bytes(conn.encoder.encode(ekeys,False),'latin1')
    #Problematic TML tags
    rep = {'<HOME>':'','<CLR>':'','<CRSRL>':'','<CRSRU>':''}
    #This connection ctrl keys
    ckeys = conn.encoder.ctrlkeys

    #Display a whole text page
    def _page(start,l):
        nonlocal tcolor, lcols

        conn.SendTML('<CLR>')
        tcolor = colors.TxtColor if start == 0 else lcols[start-1]
        for i in range(start, start+min(lcount,len(text[start:]))):
            t = f'<INK c={tcolor}>' + text[i]
            conn.SendTML(t)
            tcolor = lcols[i] = conn.parser.color
        return(i)
    
    rep = dict((re.escape(k), v) for k, v in rep.items())
    pattern = re.compile("|".join(rep.keys()))
    if conn.QueryFeature(TT.SCROLL)< 0x80:
        keys = bytes([ckeys['CRSRD'],ckeys['CRSRU'],ckeys['F1'],ckeys['F3']])
    else:
        keys = bytes([ckeys['F1'],ckeys['F3']])
    #eliminate problematic control codes
    for i,t in enumerate(text):
        text[i] = pattern.sub(lambda m: rep[re.escape(m.group(0))], t)
    if isinstance(lines,tuple):
        lcount = lines[1]-lines[0]
    else:
        lcount = lines -1
    # Render 1st page
    tcolor = colors.TxtColor
    conn.SendTML(f'<INK c={tcolor}>')
    i = _page(0,lines)
    tline = 0
    bline = i+1
    #scroll loop
    ldir = True	#Last scroll down?
    while conn.connected:
        k = conn.ReceiveKey(b'_'+keys+ekeys)
        if k == b'_':
            ret = k.decode("latin1")
            break
        elif (k[0] == ckeys['CRSRU']) and (tline > 0):	#Scroll up
            tline -= 1
            bline -= 1
            if tline > 0:
                tcolor = lcols[tline-1]
            else:
                tcolor = colors.TxtColor
            conn.SendTML(f'<SCROLL rows=-1><HOME><INK c={tcolor}>{text[tline]}')
            ldir = False
        elif (k[0] == ckeys['CRSRD']) and (bline < len(text)):	#Scroll down
            tline += 1
            if bline > 0:
                tcolor = lcols[bline-1]
            else:
                tcolor = colors.TxtColor
            conn.Sendall(TT.scroll(1)+chr(0))
            if ldir:
                conn.SendTML(f'<AT x=0 y={lcount-1}><INK c={tcolor}>{text[bline]}')
                lcols[bline] = conn.parser.color
            bline += 1
            ldir = True
        elif (k[0] == ckeys['F1']) and (tline > 0):	#Page up
            tline -= lcount
            if tline < 0:
                tline = 0
            bline = _page(tline,lcount)+1
            ldir = True
        elif (k[0] == ckeys['F3']) and (bline < len(text)):	#Page down
            bline += lcount
            if bline > len(text):
                bline = len(text)
            tline = bline-lcount
            _page(tline,lcount)
            ldir = True
        elif k in ekeys:
            ret = k.decode("utf-8")
            break
    # else:
    #     conn.ReceiveKey(b'_')
    return ret

#############################################################
# Crop text to the desired length, adding ellipsis if needed
#############################################################
def crop(text, length, ellipsis='...'):
    return text[:length-len(ellipsis)] + ellipsis if len(text) > length else text

##################################################################
# Crop text to the desired pixel width, adding ellipsis if needed
##################################################################
def gfxcrop(text, width, font = font_text):
    x = 2
    while font.getlength(text) > width:
        text = text[:-x]+'...'
        x = 4
    return text

##########################################################################################################
# Convert an int depicting a size in bytes to a rounded up to B/KB/MB/GB or TB (base 2) string
# https://stackoverflow.com/questions/12523586/python-format-size-application-converting-b-to-kb-mb-gb-tb
##########################################################################################################
def format_bytes(b:int):
    p = 2**10
    n = 0
    pl = {0 : '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while b > p:
        b /= p
        n += 1
    return str(round(b,1))+pl[n]+'B'

#############################################################################
# Return a list of files (and subdirectories) in the specified top directory
# path: top directory path
# dirs: include subdirectories in list?
# full: add the full path to the resulting list
#############################################################################
def catalog(path, dirs=False, full=True):
    files = []
    for entries in os.walk(path):
        files.extend(entries[2])
        if dirs:
            files.extend(entries[1])
        break
    if full:
        for i in range(len(files)):
            files[i] = os.path.join(path,files[i])
    return files

###########
# TML tags
###########
t_mono = {'CAT':(catalog,[('_R','_A'),('path','.'),('d',False),('f',True)])}
