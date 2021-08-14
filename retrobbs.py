#################################################################################################
# RetroBBS 0.10 (compatible with TURBO56K 0.5 and retroterm 0.13                              	#
#                                                                                           	#
# Coded by pastbytes and Durandal, from retrocomputacion.com                                  	#
#################################################################################################
#																								#
# October    7 - 2020:	Translation of console messages and code comments						#
# October    8 - 2020:	SendBitmap() code cleanup												#
# 					  	Function name translation 												#
#					  	Added _LOG() to replace most of the print calls							#
# October   12 - 2020:	Started config.ini implementation										#
# October   13 - 2020:	Added Slideshow()														#
# October   14 - 2020:	Slideshow() now can display .seq and .bin files							#
# October	15 - 2020:	Start cleanup of AudioList()											#
# 					  	Added PlayAudio()														#
#					  	First work into MenuStack implementation								#
#					  	Menu functions now return both the Menu Dictionary and a Parameters		#
#					  	Dictionary. Menu display functions must accept a Parameters Dictionary	#
#					  	as input parameter														#
#					  	While the Menu Dictionary provides the key binding->function pairing,	#
#					  	the Parameters Dictionary provides data that should survive in between	#
#					  	calls to the Menu display function										#
# October   16 - 2020:	ANSI colors on LOG messages												#
# November  25 - 2020:	Slideshow() accepts optional paramaters, delay time and waitkey boolean	#
#					  	opciones renamed valid_keys												#
#					  	old global variables cleanup											#
# November	26 - 2020:	More code cleanup, only one unused variable warning left at this point	#
#					  	Some advances in ConfigRead()											#
# November	27 - 2020:	Added SendRAWFile()														#
# November  29 - 2020:	Added waitkey parameter to SendRAWFile()								#
#						Fixed some menu handling in FileList(), AudioList and the main loop		#
#					  	Now you cant select a new file/picture/audio while displaying/playing	#
#					  	the current one															#
# November	30 - 2020:	Menudef dictionary entry now includes _waitkey status					#
#						entry = (_function,(parameters),_key,_showmenu,_waitkey)				#
#						ReceiveStr now checks if connection is active							#
#						Added cursor enable control												#
# December	 7 - 2020:	Initial SIDstream support												#
# December	 9 - 2020:	Added support for SID files to AudioList, uses HVSC .ssl files for		#
#						play length																#
# December	10 - 2020:	SIDStream() now supports abort from client side.						#
# December	19 - 2020:	Fixed bugs in AudioList() regarding file type detection					#
# February	21 - 2021:	SIDStream() protocol modified, more robust against net/modem latency	#
# February	22 - 2021:	SendBitmap() added lines parameter										#
# March		03 - 2021:	Further SIDStream protocol modifications								#
# March		04 - 2021:	Adapted to multiuser													#
# March		05 - 2021:	Text translation to English												#
# March		09 - 2021:	PlayAudio support for stream cancellation								#
# March		10 - 2021:	ImageDialog added, selection of HIRES/MULTI graphics modes				#
# March		11 - 2021:	ID3v2 TAG support for PCM audio info/AudioDialog added					#
# March		14 - 2021:	Advances in ConfigRead()												#
#						SendMenu() added, renders menus from MenuList structure					#
# March		15 - 2021:	SendText() added, renders txt through More() or seq CG petscii files	#
# March		16 - 2021:	SendCPetscii() and SendPETPetscii() added, suppor for .c and .pet files	#
# March		17 - 2021:	Slideshow() support for PCM audio										#
# March		18 - 2021:	New menu system integrated to main bbs loop								#
# April		 3 - 2021:	WikiSearch() now shows the first image in the article (if any) before	#
# 						showing the article text.												#
# 						SendBitmap() now can accept an Image object or a ByteIO object as input	#
# April		 4 - 2021:	PlayAudio() checks if metadata is available before showing dialog		#
# April		 5 - 2021:	Version changed to 0.10													#
#						Implementation of plugin system and moving common routines to their own	#
#						modules/namespace														#
# April		 6 - 2021:	Starting modifications for fully OOP socket routines					#
# April		 7 - 2021:	Starting migration of file transfer functions to their own module		#
# April		 7 - 2021:	ShowYT moved to its own plugin											#
# April		 7 - 2021:	WikiSearch moved to its own plugin										#
#################################################################################################


from __future__ import print_function

import time
import socket
import sys
import select
import os
import errno
import re
from os import walk
import random
import datetime
import signal
import numpy
import warnings
import math
import unicodedata
import string
import itertools
import configparser #INI file parser
import threading
from io import BytesIO

from PIL import Image

#Petscii constants
import common.petscii as P

#Turbo56K constants and helper routines
#import common.turbo56k as TT
from common import turbo56k as TT

from common.classes import BBS
from common.connection import Connection
from common.bbsdebug import _LOG, bcolors
from common.helpers import MenuBack, valid_keys, formatX, More
from common.style import bbsstyle, default_style, RenderMenuTitle

#File transfer functions
import common.filetools as FT
#Audio
try:
    import librosa
    _LOG('Audio fileformats available')
    wavs = True
except:
    wavs = False
    _LOG('Audio fileformats not available!')
#Audio Metadata
try:
    import mutagen
    _LOG('Audio Metadata available')
    meta = True
except:
    _LOG('Audio Metadata not available!')
    meta = False

#SIDStreaming
import common.siddumpparser as sd

import importlib
import pkgutil


#Import plugins ******************************
import plugins

def iter_namespace(ns_pkg):
    # Specifying the second argument (prefix) to iter_modules makes the
    # returned name an absolute name instead of a relative one. This allows
    # import_module to work without having to do additional modification to
    # the name.
    return pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + ".")


#Threads running flag
_run = True

#Timeout default value (secs)
_tout = 60.0*5



#Plugins dictionary
PlugDict = {}

#Reads Config file
def ConfigRead():
    global bbs_instance
    global PlugDict

    #Function dictionary
    func_dic = {'IMAGEGALLERY': FileList,	#+
                'AUDIOLIBRARY': AudioList,	#+
                'FILES': FileList,			#+
                'SENDRAW': SendRAWFile,
                'SWITCHMENU': SwitchMenu,	#+
                'SLIDESHOW': SlideShow,		#+
                'SIDPLAY': SIDStream,
                'PCMPLAY': PlayAudio,		#+
                'TEXT': SendText,
                'SHOWPIC': FT.SendBitmap,
                'EXIT': LogOff,				#+
                'BACK': MenuBack}			#+

    config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
    config.read('config.ini')

    #MAIN variables

    bbs_instance.name = config['MAIN']['bbsname']
    bbs_instance.ip = config['MAIN']['ip']
    bbs_instance.port = config['MAIN'].getint('port')
    bbs_instance.lang = config['MAIN']['language']
    bbs_instance.WMess = config['MAIN'].get('welcome', fallback='wELCOME!')
    bbs_instance.GBMess = config['MAIN'].get('goodbye', fallback='gOODBYE!')

    #Parse Menues
    mcount = config['MAIN'].getint('menues')								#Number of menues

    #print("Menues:", mcount)

    _bbs_menues = [None] * mcount

    for m in range(0, mcount):		#Iterate menues
        if m == 0:
            tmenu = config['MAINMENU']['title']								#MainMenu title
            scount = config['MAINMENU'].getint('sections')					#MainMenu number of sections
            tkey = 'MAINMENUSECTION'
            prompt = config['MAINMENU'].get('prompt', fallback='sELECTION:')
        else:
            tmenu = config['MENU'+str(m+1)]['title']						#Menu title
            scount = config['MENU'+str(m+1)].getint('sections')				#Menu number of sections
            prompt = config['MENU'+str(m+1)].get('prompt', fallback='sELECTION:')
            tkey = 'MENU'+str(m+1)+'SECTION'

        _bbs_menues[m] = {'title':tmenu, 'sections':scount, 'prompt':prompt, 'entries':[{}]*scount}
        for s in range(0, scount):		#Iterate menu sections
            tsection = config[tkey+str(s+1)]['title']						#Section Title
            ecount = config[tkey+str(s+1)].getint('entries')				#Section number of entries
            scolumns = config[tkey+str(s+1)].getint('columns', fallback= 2)
            _bbs_menues[m]['entries'][s] = {'title':tsection,'entries':ecount,'columns':scolumns,'entrydefs':{}}
            for e in range(0,ecount):	#Iterate section entries
                tentry = config[tkey+str(s+1)]['entry'+str(e+1)+'title']	#Entry Title
                if scolumns < 2:
                    dentry = config.get(tkey+str(s+1),'entry'+str(e+1)+'desc', fallback = '')
                    if dentry != '':
                        tentry = (tentry,dentry)
                ekey = bytes(config[tkey+str(s+1)]['entry'+str(e+1)+'key'],'ascii')		#Entry Key binding
                efunc = config[tkey+str(s+1)]['entry'+str(e+1)+'func']		#Entry Internal function
                if efunc in func_dic:
                    _bbs_menues[m]['entries'][s]['entrydefs'][ekey] = [func_dic[efunc],None,tentry,True,False]
                elif efunc in PlugDict:
                    _bbs_menues[m]['entries'][s]['entrydefs'][ekey] = [PlugDict[efunc][0],None,tentry,True,False]
                else:
                    raise Exception('config.ini - Unknown function at: '+'entry'+str(e+1)+'func')
                #Parse parameters
                parms = []
                if efunc == 'IMAGEGALLERY':		#Show image file list
                    p = config.get(tkey+str(s+1), 'entry'+str(e+1)+'path', fallback='images')
                    parms= [tentry,'','Displaying image list',p,('.art','.ocp','.koa','.kla','.ART','.OCP','.KOA','.KLA','.gif','jpg','png','.GIF','.JPG','PNG'),FT.SendBitmap]
                elif efunc == 'SWITCHMENU':		#Switch menu
                    parms = [config[tkey+str(s+1)].getint('entry'+str(e+1)+'id')]
                elif efunc == 'FILES':			#Show file list
                    exts = tuple((config.get(tkey+str(s+1),'entry'+str(e+1)+'ext', fallback='.prg,.PRG')).split(','))
                    p = config.get(tkey+str(s+1), 'entry'+str(e+1)+'path', fallback='programs')
                    parms = [tentry,'','Displaying file list',p,exts,SendProgram]
                elif efunc == 'AUDIOLIBRARY':	#Show audio file list
                    p = config.get(tkey+str(s+1), 'entry'+str(e+1)+'path', fallback='sound')	#config[tkey+str(s+1)]['entry'+str(e+1)+'path']
                    parms = [tentry,'','Displaying audio list',p]
                elif efunc == 'PCMPLAY':		#Play PCM audio
                    parms = [config.get(tkey+str(s+1), 'entry'+str(e+1)+'path', fallback='bbsfiles/bbsintroaudio-eng11K8b.wav')]
                elif efunc == 'SLIDESHOW':		#Iterate through and show all supported files in a directory
                    parms = [tentry,config.get(tkey+str(s+1), 'entry'+str(e+1)+'path', fallback='bbsfiles/pictures')]
                # elif efunc == 'GRABYT':			#Grab and show a YouTube frame
                # 	url = config.get(tkey+str(s+1), 'entry'+str(e+1)+'url', fallback="https://www.youtube.com/watch?v=XBPjVzSoepo")
                # 	crop = config.get(tkey+str(s+1), 'entry'+str(e+1)+'crop', fallback=None)
                # 	if crop != None:
                # 		crop = tuple([int(e) if e.isdigit() else 0 for e in crop.split(',')])
                # 	parms = [url,crop,1]
                elif efunc == 'BACK' or efunc == 'EXIT':
                    parms = []
                elif efunc in PlugDict:			#Plugin function
                    parms = []
                    for p in PlugDict[efunc][1]:	#Iterate parameters
                        ep = config.get(tkey+str(s+1), 'entry'+str(e+1)+p[0], fallback=p[1])
                        if isinstance(p[1],tuple) ==True and isinstance(ep,tuple) == False:
                            ep = tuple([int(e) if e.isdigit() else 0 for e in ep.split(',')])
                        parms.append(ep)

                # This tuple need to be added to one (conn,) on each connection instance when calling func
                # also needs conn.MenuParameters added to this
                # finaltuple = (conn,)+ _parms_
                _bbs_menues[m]['entries'][s]['entrydefs'][ekey][1] = tuple(parms) 
        _bbs_menues[m]['entries'][0]['entrydefs'][b'\r']=[SendMenu,(),'',False,False]
    #print(_bbs_menues)
    bbs_instance.MenuList = _bbs_menues

    #Get any plugin config options
    try:
        bbs_instance.PlugOptions = dict(config.items('PLUGINS'))
    except:
        bbs_instance.PlugOptions = {}


#Handles CTRL-C
def signal_handler(sig, frame):
    global _run
    global conlist
    global conthread

    _LOG('Ctrl+C! Bye!')
    _run = False

    for t in range(1,6):
        if t in conlist:				#Find closed connections
            conlist[t][0].join()
    conthread.join()

    try:
        sock.shutdown(socket.SHUT_RDWR)
        sock.close()
    except:
        pass
    sys.exit(0)


def FileList(conn,title,speech,logtext,path,ffilter,fhandler):

    if conn.menu != -1:
        conn.MenuStack.append([conn.MenuDefs,conn.menu])
        conn.menu = -1
    # Init Menu parameter dictionary if needed
    if conn.MenuParameters == {}:
        conn.MenuParameters['current'] = 0

    print(conn.MenuParameters['current'])

    # Start with barebones MenuDic
    MenuDic = { 
                b'_': (MenuBack,(conn,),"pREVIOUS mENU",True,False),
                b'\r': (FileList,(conn,title,speech,logtext,path,ffilter,fhandler),title,False,False)
              }	

    _LOG(logtext,id=conn.id)
    # Send speech message
    conn.Sendall(TT.to_Speech() + speech)
    time.sleep(1)
    # Select screen output
    conn.Sendall(TT.to_Screen())
    # Sync
    conn.Sendall(chr(0)*2)
    # # Text mode
    conn.Sendall(TT.to_Text(0,0,0))

    RenderMenuTitle(conn,title)

    # Send menu options
    files = []	#all files
    programs = []	#filtered list
    #Read all files from 'path'
    for entries in walk(path):
        files.extend(entries[2])
        break

    #Filter out all files not matching 'filter'
    for f in files:
        if f.endswith(ffilter):
            programs.append(f)


    programs.sort()	#Sort list

    pages = int((len(programs)-1) / 40) + 1
    count = len(programs)
    start = conn.MenuParameters['current'] * 40
    end = start + 39
    if end >= count:
        end = count - 1

    #Add pagination keybindings to MenuDic
    if pages > 1:
        if conn.MenuParameters['current'] == 0:
            page = pages-1
        else:
            page = conn.MenuParameters['current']-1
        MenuDic[b'<'] = (SetPage,(conn,page),'pREVIOUS pAGE',True,False)
        if conn.MenuParameters['current'] == pages-1:
            page = 0
        else:
            page = conn.MenuParameters['current']+1
        MenuDic[b'>'] = (SetPage,(conn,page),'nEXT pAGE',True,False)

    if fhandler == SendProgram:
        keywait = False
    else:
        keywait = True

    x = 0

    for x in range(start, end + 1):
        if x % 4 == 0 or x % 4 == 1:
            color1 = P.LT_BLUE
            color2 = P.GREY3
        if x % 4 == 2 or x % 4 == 3:
            color1 = P.CYAN
            color2 = P.YELLOW
        if x % 2 == 0:
            conn.Sendall(chr(P.RVS_ON)+chr(color1)+chr(181)+valid_keys[x-start]+chr(182)+chr(P.RVS_OFF)+chr(color2)+(P.toPETSCII(programs[x])[:len(programs[x])-4]+' '*16)[:16]+chr(31)+' ')
        else:
            conn.Sendall(chr(P.RVS_ON)+chr(color1)+chr(181)+valid_keys[x-start]+chr(182)+chr(P.RVS_OFF)+chr(color2)+(P.toPETSCII(programs[x])[:len(programs[x])-4]+' '*16)[:16]+chr(31)+'\r')
        #Add keybinding to MenuDic
        if fhandler == SendProgram:
            parameters = (conn,path+programs[x],)
        else:
            parameters = (conn,path+programs[x],25,True,True,)
        MenuDic[valid_keys[x-start].encode('ascii','ignore')] = (fhandler,parameters,valid_keys[x-start],True,keywait)
    else:
        if x % 2 == 0 and x != start:
            conn.Sendall('\r')
        lineasimpresas = int(((end - start + 1) / 2.0) + 0.5)
        if lineasimpresas < 20:
            for x in range(20 - lineasimpresas):
                conn.Sendall('\r')


    conn.Sendall(' '+chr(P.GREY3)+chr(P.RVS_ON)+'_ '+chr(P.LT_GREEN)+'pREV. mENU '+chr(P.GREY3)+'< '+chr(P.LT_GREEN)+'pREV.pAGE '+chr(P.GREY3)+'> '+chr(P.LT_GREEN)+'nEXT pAGE  '+chr(P.RVS_OFF)+'\r')
    conn.Sendall(chr(P.WHITE)+' ['+str(conn.MenuParameters['current']+1)+'/'+str(pages)+']'+chr(P.CYAN)+' sELECTION:'+chr(P.WHITE)+' ')
    conn.Sendall(chr(255) + chr(161) + 'seleksioneunaopsion,')
    time.sleep(1)
    # Select screen output
    conn.Sendall(TT.to_Screen())
    return MenuDic

#################################################
# Render Menu from MenuList structure           #
#################################################
def SendMenu(conn):
    if conn.menu < 0:
        return()
    conn.Sendall(TT.to_Text(0,0,0)+TT.to_Screen())	#Set Screen Text mode output
    tmenu = bbs_instance.MenuList[conn.menu]	#Change to simply tmenu = conn.MenuDefs
    _LOG("Sending menu: "+tmenu['title'],id=conn.id)
    RenderMenuTitle(conn,tmenu['title'])
    conn.Sendall('\r')
    for s in tmenu['entries']:
        #Sections
        conn.Sendall(' '+chr(P.WHITE)+s['title']+'\r')
        conn.Sendall(chr(P.LT_GREEN)+chr(176)+38*chr(P.HLINE)+chr(174))

        #Items
        count = 0
        toggle = False
        line = ''
        if s['columns'] < 2:
            sw = 1
            tw = 37
        else:
            sw = 2
            tw = 17
        for i in s['entrydefs']:
            if i == b'\r':
                continue
            #print(s['entrydefs'][i])
            if count % sw == 0:
                conn.Sendall(line)
                toggle = not toggle
                line = 39*' '+chr(P.GREEN)+chr(P.VLINE)

            if not toggle:
                c1 = P.LT_BLUE
                c2 = P.GREY3
            else:
                c1 = P.CYAN
                c2 = P.YELLOW
            if isinstance(s['entrydefs'][i][2],tuple):
                t = s['entrydefs'][i][2][0]
                #print('#####')
                desc = formatX(s['entrydefs'][i][2][1],columns=36)
            else:
                t = s['entrydefs'][i][2]
                desc =''
            title = t if len(t)<tw else t[0:tw-4]+'...'
            #print(title)
            entry = chr(c1)+chr(P.RVS_ON)+chr(181)+chr(i[0])+chr(182)+chr(P.RVS_OFF)+chr(c2)+title
            if count % sw == 0:
                line = entry + line[len(entry)-4:]
            else:
                line = line[0:20+4]+ entry + line[20+4+len(entry)-4:]
            if desc != '':
                tdesc = ''
                for l in desc:
                    tdesc += chr(P.LT_GREEN)+chr(P.VLINE)+chr(P.WHITE)+'  '+l+((36-len(l))*' ')+chr(P.GREEN)+chr(P.VLINE)
                line += tdesc
            count += 1
        #if (count % 2 != 0 or sw == 1) and line != '':
        conn.Sendall(line)


        conn.Sendall(chr(173)+38*chr(P.HLINE)+chr(189))
    ####
    conn.Sendall(TT.set_CRSR(0,24)+chr(P.WHITE)+' '+tmenu['prompt']+' ')
    #WaitRETURN(conn)


def SendText(conn, filename, title=''):
    colors = (P.BLACK,P.WHITE,P.RED,P.PURPLE,P.CYAN,P.GREEN,P.BLUE,P.YELLOW,P.BROWN,P.PINK,P.ORANGE,P.GREY1,P.GREY2,P.LT_BLUE,P.LT_GREEN,P.GREY3)
    if title != '':
        RenderMenuTitle(conn, title)
        l = 22
        conn.Sendall(TT.set_Window(3,24))
    else:
        l = 25
        conn.Sendall(chr(P.CLEAR))

    if filename.endswith(('.txt','.TXT')):
        #Convert plain text to PETSCII and display with More
        tf = open(filename,"r")
        ot = tf.read()
        tf.close()
        text = formatX(ot)

        More(conn,text,l)

    elif filename.endswith(('.seq','.SEQ')):
        prompt='return'
        tf = open(filename,"rb")
        text = tf.read()
        cc=0
        ll=0
        page = 0
        rvs = ''
        color = ''
        for c in text:
            char = c.to_bytes(1,'big')
            conn.Sendallbin(char)
            #Keep track of cursor position
            if char[0] in itertools.chain(range(32,128),range(160,256)): #Printable chars
                cc += 1
                #print('cc')
            elif char[0] == P.CRSR_RIGHT:
                cc += 1
            elif char[0] == P.CRSR_LEFT or char == P.DELETE:
                cc -= 1
            elif char[0] == P.CRSR_UP:
                ll -= 1
                #print(ll)
            elif char[0] == P.CRSR_DOWN:
                ll += 1
                #print('d',ll)
            elif char == b'\x0d':
                ll += 1
                #print('r',ll)
                cc = 0
                rvs = ''
            elif char[0] == P.HOME or char[0] == P.CLEAR:
                ll = 0
                page = 0
                #print(ll)
                cc = 0
            elif char[0] in colors:
                color = chr(char[0])
            elif char[0] == P.RVS_ON:
                rvs = chr(P.RVS_ON)
            elif char[0] == P.RVS_OFF:
                rvs = ''
            elif char[0] == P.TOLOWER:
                prompt = 'return'
            elif char[0] == P.TOUPPER:
                prompt = 'RETURN'
            if cc == 40:
                cc = 0
                ll += 1
                #print('>',ll)
            elif cc < 0:
                if ll!=l*page:
                    cc = 39
                    ll -= 1
                    #print('<',ll)
                else:
                    cc = 0
            if ll < l*page:
                ll = l*page
                #print(ll)
            elif ll >= (l*page)+(l-1):
                if cc !=0:
                    conn.Sendall('\r')
                conn.Sendall(chr(P.RVS_OFF)+chr(P.YELLOW)+'['+chr(P.LT_BLUE)+prompt+' OR _'+chr(P.YELLOW)+']')
                k = conn.ReceiveKey(b'\r_')
                if conn.connected == False:
                    conn.Sendall(TT.set_Window(0,24))
                    return -1
                if k == b'_':
                    conn.Sendall(TT.set_Window(0,24))
                    return -1
                conn.Sendall(chr(P.DELETE)*13+rvs+color+TT.set_CRSR(cc,(22-l)+ll-(l*page)))
                page += 1
        if cc !=0:
            conn.Sendall('\r')
        #print(ll)
        conn.Sendall(chr(P.YELLOW)+'['+chr(P.LT_BLUE)+prompt+chr(P.YELLOW)+']')
        conn.ReceiveKey()

    conn.Sendall(TT.set_Window(0,24))
    return -1
#######

def SendCPetscii(conn,filename,pause=0):
    try:
        fi = open(filename,'r')
    except:
        return()
    text = fi.read()
    #print(text)
    fi.close
    #### Falta fijarse si es upper o lower
    if text.find('upper') != -1:
        conn.Sendall(chr(P.TOUPPER))
    else:
        conn.Sendall(chr(P.TOLOWER))
    frames = text.split('unsigned char frame')
    #print(frames)
    for f in frames:
        if f == '':
            continue
        binary = b''
        fr = re.sub('(?:[0-9]{4})*\[\]={// border,bg,chars,colors\n','',f)
        fl = fr.split('\n')
        #print(f,'\n',fr,'\n',fl)
        scc = fl[0].split(',')
        bo = int(scc[0]).to_bytes(1,'big') #border
        bg = int(scc[1]).to_bytes(1,'big') #background
        binary += b'\xff\xb2\x00\x90\x00'+bo+bg+b'\x81\x00\x82\xe8\x03'
        i = 0
        for line in fl[1:26]:
            for c in line.split(','):	#Screen codes
                if c.isnumeric():
                    binary += int(c).to_bytes(1,'big')
                    i += 1
        #print(hex(i))
        binary+= b'\x81\x20\x82\xe8\x03'
        i = 0
        for line in fl[26:52]:
            for c in line.split(','):	#Color RAM
                if c.isnumeric():
                    binary += int(c).to_bytes(1,'big')
                    i+=1
        #print(i)
        binary+= b'\xfe'
        conn.Sendallbin(binary)
        if pause > 0:
            time.sleep(pause)
        else:
            conn.ReceiveKey()
    conn.Sendall(TT.enable_CRSR())
    if pause == 0:
        return 0
    else:
        return -1

def SendPETPetscii(conn,filename):
    try:
        f = open(filename,'rb')
    except:
        return -1
    pet = f.read()
    bo = pet[2].to_bytes(1,'big')
    bg = pet[3].to_bytes(1,'big')
    if pet[4] == 1:
        conn.Sendall(chr(P.TOUPPER))
    else:
        conn.Sendall(chr(P.TOLOWER))
    binary = b'\xff\xb2\x00\x90\x00'+bo+bg+b'\x81\x00\x82\xe8\x03'
    binary += pet[5:1005]
    #print(len(pet[5:1005]))
    binary += b'\x81\x20\x82\xe8\x03'
    binary += pet[1005:]
    #print(len(pet[1005:]))
    conn.Sendallbin(binary)
    #time.sleep(5)
    return -1


def DisplaySIDInfo(conn, info):
    minutes = int(info['songlength']/60)
    seconds = info['songlength']- (minutes*60)
    conn.Sendall(chr(P.CLEAR)+chr(P.GREY3)+chr(P.RVS_ON)+chr(TT.CMDON))
    for y in range(0,10):
        conn.Sendall(chr(TT.LINE_FILL)+chr(y)+chr(160))
    conn.Sendall(chr(TT.CMDOFF)+chr(P.GREY1)+TT.Fill_Line(10,226)+chr(P.GREY3))
    # text = format40('\r Titulo: '+info['title']+'\r Artista: '+info['artist']+'\r Copyright: '+info['copyright']+'\r Duracion: '+ ('00'+str(minutes))[-2:]+':'+('00'+str(seconds))[-2:]+'\r\r pRESIONE return PARA REPRODUCIR\r cUALQUIER TECLA PARA DETENER\r')
    # for line in text:
    # 	conn.Sendall(chr(P.RVS_ON)+line+'\r')
    conn.Sendall(chr(P.CRSR_DOWN)+' tITLE: '+formatX(info['title'])[0][0:30]+'\r')
    conn.Sendall(chr(P.RVS_ON)+' aRTIST: '+formatX(info['artist'])[0][0:29]+'\r')
    conn.Sendall(chr(P.RVS_ON)+' cOPYRIGHT: '+formatX(info['copyright'])[0][0:27]+'\r')
    conn.Sendall(chr(P.RVS_ON)+' pLAYTIME: '+ ('00'+str(minutes))[-2:]+':'+('00'+str(seconds))[-2:]+'\r')
    conn.Sendall(chr(P.RVS_ON)+chr(P.CRSR_DOWN)+" pRESS return TO PLAY\r"+chr(P.RVS_ON)+" aNY KEY TO STOP"+chr(P.RVS_OFF))


def SIDStream(conn, filename,ptime, infosc=True):

    data = sd.SIDParser(filename,ptime)


    if data != None:
        if infosc == True:
            info = {}
            with open(filename, "rb") as fh:
                content = fh.read()
                info['type'] = (content[:4].decode("iso8859-1"))
                info['version'] = (content[5])
                info['subsongs'] = (content[15])
                info['startsong'] = (content[17])
                info['title'] = (content[22:54].decode('iso8859-1')).strip(chr(0))
                info['artist'] = (content[54:86].decode('iso8859-1')).strip(chr(0))
                info['copyright'] = (content[86:118].decode('iso8859-1')).strip(chr(0))
                info['songlength'] = ptime
            #print(info)
            DisplaySIDInfo(conn, info)
            conn.ReceiveKey()

        conn.Sendall(chr(TT.CMDON)+chr(TT.SIDSTREAM))
        count = 0
        #tt0 = time.time()
        for frame in data:
            #print(frame[0])
            conn.Sendallbin(frame[0]) #Register count
            conn.Sendallbin(frame[1]) #Register bitmap
            conn.Sendallbin(frame[2]) #Register data
            conn.Sendallbin(b'\xff')	 #Sync byte
            count += 1

            if count%100 == 0:
                ack = b''
                #tt1 = time.time()
                ack = conn.Receive(1)
                #print('Time delay between 100 packages', round(time.time()-tt0,2),round(time.time()-tt1,2))
                #tt0 = time.time()
                # for r in range(0, 9):
                # 	ack += connection.recv(1)
                    #print('.',end='')
                count = 0
                #print('\n',count, ack)
                if (b'\xff' in ack) or not conn.connected:
                    break	#Abort stream
            
        conn.Sendall(chr(0))	#End stream
        #conn.Receive(1)	#Receive last frame ack character


# Display sequentially all matching files inside a directory
def SlideShow(conn,title,path,delay = 1, waitkey = True):
    # Sends menu options
    files = []	#all files
    slides = []	#filtered list
    #Read all the files from 'path'
    for entries in walk(path):
        files.extend(entries[2])
        break

    pics_e = ('.art','.ocp','.koa','.kla','.ART','.OCP','.KOA','.KLA','.gif','jpg','png','.GIF','.JPG','PNG')
    text_e = ('.txt','.TXT','.seq','.SEQ')
    bin_e = ('.bin','.BIN','.raw','.raw')
    pet_e = ('.c','.C','.pet','.PET')
    aud_e = ('.mp3','.wav','.MP3','.WAV')

    #Keeps only the files with matching extension 
    for f in files:
        if f.endswith(pics_e + text_e + bin_e + pet_e + aud_e):
            slides.append(f)

    slides.sort()	#Sort list

    #Iterate through files
    for p in slides:
        w = 0
        conn.Sendall(TT.enable_CRSR()+chr(P.CLEAR))
        _LOG('SlideShow - Showing: '+p,id=conn.id)
        ext = p[-4:]
        if ext in pics_e:
            FT.SendBitmap(conn, path+p)
        elif ext in bin_e:
            slide = open(path+p,"rb")
            binary = slide.read()
            slide.close()
            conn.Sendallbin(binary)
        elif ext in text_e:
            w = SendText(conn,path+p,title)
        elif ext in pet_e[0:2]:
            w = SendCPetscii(conn,path+p,(0 if waitkey else delay))
        elif ext in pet_e[2:4]:
            w = SendPETPetscii(conn,path+p)
        elif ext in aud_e:
            PlayAudio(conn,path+p)
            w = 1
        # Wait for the user to press RETURN
        if waitkey == True and w == 0:
            WaitRETURN(conn,60.0*5)
        else:
            time.sleep(delay)

        conn.Sendall(TT.to_Text(0,0,0))
    conn.Sendall(TT.enable_CRSR())




def AudioList(conn,title,speech,logtext,path):

    if conn.menu != -1:
        conn.MenuStack.append([conn.MenuDefs,conn.menu])
        conn.menu = -1
    # Init Menu parameter dictionary if needed
    if conn.MenuParameters == {}:
        conn.MenuParameters['current'] = 0

    # Start with barebones MenuDic
    MenuDic = { 
                b'_': (MenuBack,(conn,),"pREVIOUS mENU",True,False),
                b'\r': (AudioList,(conn,title,speech,logtext,path),title,False,False)
              }

    _LOG(logtext,id=conn.id)
    _LOG('Displaying Page: '+str(conn.MenuParameters['current']+1),id=conn.id)
    # Send speech message
    conn.Sendall(TT.to_Speech() + speech)
    time.sleep(1)
    # Selects screen output
    conn.Sendall(TT.to_Screen())
    # Sync
    conn.Sendall(chr(0)*2)
    # # Text mode
    conn.Sendall(TT.to_Text(0,0,0))

    RenderMenuTitle(conn,title)

    # Sends menu options
    files = []	#all files
    audios = []	#filtered list
    #Read all the files from 'path'
    for entries in walk(path):
        files.extend(entries[2])
        break

    wext = ('.wav','.WAV','.mp3','.MP3')

    filefilter = ('.sid', '.SID')
    if wavs == True:
        filefilter = filefilter + wext

    #Filters only the files matching 'filefilter'
    for f in files:
        if f.endswith(filefilter):
            audios.append(f)


    audios.sort()	#Sort list

    #for t in range(0,len(audios)):
    #	length.append(0.0)
    length = [0.0]*len(audios)	#Audio lenght list

    #Calc pages
    pages = int((len(audios)-1) / 20) + 1
    count = len(audios)
    start = conn.MenuParameters['current'] * 20
    end = start + 19
    if end >= count:
        end = count - 1

    #Add pagination keybindings to MenuDic
    if pages > 1:
        if conn.MenuParameters['current'] == 0:
            page = pages-1
        else:
            page = conn.MenuParameters['current']-1
        MenuDic[b'<'] = (SetPage,(conn,page),'pREVIOUS pAGE',True,False)
        if conn.MenuParameters['current'] == pages-1:
            page = 0
        else:
            page = conn.MenuParameters['current']+1
        MenuDic[b'>'] = (SetPage,(conn,page),'nEXT pAGE',True,False)

    for x in range(start, end + 1, 1):
        afunc = PlayAudio
        if x % 2 == 0:
            color1 = P.LT_BLUE
            color2 = P.GREY3
        else:
            color1 = P.CYAN
            color2 = P.YELLOW
        conn.Sendall(chr(P.RVS_ON)+chr(color1)+chr(181)+valid_keys[x-start]+chr(182)+chr(P.RVS_OFF)+chr(color2)+((P.toPETSCII(audios[x]))[:len(audios[x])-4]+' '*30)[:30]+' ')
        if (wavs == True) and (audios[x].endswith(wext)):
            conn.Sendall(chr(P.COMM_B)+chr(P.CRSR_LEFT))
            if meta == True and (audios[x])[-4:] != '.wav' and (audios[x])[-4:] != '.WAV':
                #Load metadata
                audio = mutagen.File(path+audios[x], easy = True)
                cantsegundos = int(audio.info.length)
            else:
                #Load and compute audio playtime
                y, sr = librosa.load(path+audios[x], sr = None, mono= True)
                cantsegundos = int(librosa.get_duration(y, sr))
            cantminutos = int(cantsegundos / 60)
            length[x] = cantsegundos
            cantsegundos = cantsegundos - (cantminutos * 60)
        else:	#SID file
            #print('s-',audios[x])
            afunc = SIDStream
            if os.path.isfile(path+(audios[x])[:-3]+'ssl') == True:
                tf = open(path+(audios[x])[:-3]+'ssl')
                tstr = tf.read()
                tf.close()
                cantminutos = int(hex(ord(tstr[0]))[2:])
                cantsegundos = int(hex(ord(tstr[1]))[2:])
                length[x] = (cantminutos*60)+cantsegundos # Playtime for the 1st subtune
            else:
                length[x] = 60*3
                cantminutos = 3
                cantsegundos = 0

        conn.Sendall(chr(P.WHITE)+('00'+str(cantminutos))[-2:]+':'+('00'+str(cantsegundos))[-2:]+'\r')
        #Add keybinding to MenuDic
        MenuDic[valid_keys[x-start].encode('ascii','ignore')] = (afunc,(conn,path+audios[x],length[x],True),valid_keys[x-start],True,False)
    else:
        lineasimpresas = end - start + 1
        if lineasimpresas < 20:
            for x in range(20 - lineasimpresas):
                conn.Sendall('\r')

    conn.Sendall(' '+chr(P.GREY3)+chr(P.RVS_ON)+'_ '+chr(P.LT_GREEN)+'pREV. mENU '+chr(P.GREY3)+'< '+chr(P.LT_GREEN)+'pREV.pAGE '+chr(P.GREY3)+'> '+chr(P.LT_GREEN)+'nEXT pAGE  '+chr(P.RVS_OFF)+'\r')
    conn.Sendall(chr(P.WHITE)+' ['+str(conn.MenuParameters['current']+1)+'/'+str(pages)+']'+chr(P.CYAN)+' sELECTION:'+chr(P.WHITE)+' ')
    conn.Sendall(chr(255) + chr(161) + 'seleksioneunaopsion,')
    time.sleep(1)
    # Selects screen output
    conn.Sendall(chr(255) + chr(160))
    return MenuDic

# Display audio dialog
def AudioDialog(conn, data):
    conn.Sendall(chr(P.CLEAR)+chr(P.GREY3)+chr(P.RVS_ON)+chr(TT.CMDON))
    for y in range(0,15):
        conn.Sendall(chr(TT.LINE_FILL)+chr(y)+chr(160))
    conn.Sendall(chr(TT.CMDOFF)+chr(P.GREY1)+TT.Fill_Line(15,226)+chr(P.GREY3))
    conn.Sendall(data['title'].center(40,chr(P.HLINE))+'\r')
    if data['album'] != '':
        conn.Sendall(chr(P.RVS_ON)+' aLBUM:\r'+chr(P.RVS_ON)+' '+data['album']+'\r\r')
    if data['artist'] != '':
        conn.Sendall(chr(P.RVS_ON)+' aRTIST:\r'+chr(P.RVS_ON)+' '+data['artist']+'\r\r')
    conn.Sendall(chr(P.RVS_ON)+' lENGTH: '+data['length']+'\r\r')
    conn.Sendall(chr(P.RVS_ON)+' fROM '+data['sr']+' TO '+str(conn.samplerate)+'hZ')
    conn.Sendall(TT.set_CRSR(0,12)+' pRESS <return> TO PLAY\r')
    conn.Sendall(chr(P.RVS_ON)+' pRESS <X> AND WAIT TO STOP\r')
    conn.Sendall(chr(P.RVS_ON)+' pRESS <_> TO CANCEL')
    if conn.ReceiveKey(b'\r_') == b'_':
        return False
    return True
    

#Send Audio file
def PlayAudio(conn,filename, length = 60.0, dialog=False):
    conn.socket.settimeout(_tout+length)	#<<<< This might be pointless
    _LOG('Timeout set to:'+bcolors.OKGREEN+str(length)+bcolors.ENDC+' seconds',id=conn.id)
    if filename[-4:] == '.raw' or filename[-4:] == '.RAW':
        conn.Sendall(chr(255) + chr(161) + '..enviando,')
        time.sleep(1)
        # Select screen output
        conn.Sendall(chr(255) + chr(160))
        # Send selected raw audio
        _LOG('Sending RAW audio: '+filename,id=conn.id)
        archivo=open(filename,"rb")
        binario = b'\xFF\x83'
        binario += archivo.read()
        binario += b'\x00\x00\x00\x00\x00\x00\xFE'
        archivo.close()
    else:
        #Send any other supported audio file format
        conn.Sendall(chr(255) + chr(161) + '..enviando,')
        time.sleep(1)
        # Select screen output
        conn.Sendall(chr(255) + chr(160))
        _LOG('Sending audio: '+filename,id=conn.id)

        if (dialog == True) and (meta == True):
            a_meta = {}
            a_data = mutagen.File(filename)
            a_min = int(a_data.info.length/60)
            a_sec = int(round(a_data.info.length,0)-(a_min*60))
            a_meta['length'] = ('00'+str(a_min))[-2:]+':'+('00'+str(a_sec))[-2:]
            a_meta['sr'] = str(a_data.info.sample_rate)+'hZ'
            a_meta['title'] = P.toPETSCII(filename[filename.rfind('/')+1:filename.rfind('/')+39])
            a_meta['album'] = ''
            a_meta['artist'] = ''
            if a_data.tags != None:
                if a_data.tags.getall('TIT2') != []:
                    a_meta['title'] = P.toPETSCII(a_data.tags.getall('TIT2')[0][0][:38])
                if a_data.tags.getall('TALB') != []:
                    a_meta['album'] = P.toPETSCII(a_data.tags.getall('TALB')[0][0][:38])
                for ar in range(1,5):
                    ars = 'TPE'+str(ar)
                    if a_data.tags.getall(ars) != []:
                        a_meta['artist'] = P.toPETSCII(a_data.tags.getall(ars)[0][0][:38])
                        break
            if not AudioDialog(conn,a_meta):
                return()
            if not conn.connected:
                return()
            conn.Sendall(chr(P.COMM_B)+chr(P.CRSR_LEFT))


        #Streaming mode
        binario = b'\xFF\x83'
        #Load audio
        t0 = time.process_time()
        y, sr = librosa.load(filename, conn.samplerate, True)
        #Normalize and convert to 8-bit
        
        numpy.clip(y, -1, 1, y)
        
        norm = librosa.mu_compress(y, mu=15, quantize=True)
        
        norm = norm + 8
        
        #norm = y / y.max()
        #norm = 255 * norm
        bin8 = numpy.uint8(norm)
        #Dividimos por 16
        #bin8 = bin8 / 16
        #Convert to a nibble bytearray
        t = time.process_time() - t0

        l = len(bin8)
        _LOG('Samples: '+bcolors.OKGREEN+str(l)+bcolors.ENDC+' processed in '+bcolors.OKGREEN+str(round(t,2))+bcolors.ENDC+' seconds\nStreaming',id=conn.id)
        t0 = time.time()
        count = 0
        overrun = 0	# Estimated bytes in the receiving buffer


        for b in range(0,l-1,2):
            lnibble = int(bin8[b])
            if lnibble == 0:
                lnibble = int(1)
            if b+1 <= l:
                hnibble = int(bin8[b+1])
            else:
                hnibble = int(0)
            binario += (lnibble + (16 * hnibble)).to_bytes(1,'big')
            count += 1
            #Send data if there is more than samplerate*0.75 bytes processed
            if count > conn.samplerate*0.75:
                conn.Sendallbin(binario)
                #_LOG('>', _end='', date=False)
                sys.stderr.flush()
                overrun += count
                #Check for terminal cancelation
                conn.socket.setblocking(0)	# Change socket to non-blocking
                try:
                    hs = conn.socket.recv(1)
                    if hs == b'\xff':
                        conn.socket.setblocking(1)
                        binario = b''
                        _LOG('USER CANCEL',id=conn.id)
                        break
                except:
                    pass
                conn.socket.setblocking(1)

                time.sleep(1)	#Wait 1 second to avoid flooding the receiver buffer
                overrun -= conn.samplerate*0.5	#remove the equivalent to 1 second of playtime
                if overrun > 200000 * 0.75: #If the buffer is more than 75% full, wait a little longer
                    #_LOG('-', _end='', date=False)
                    sys.stderr.flush()
                    time.sleep(2)
                    overrun -= conn.samplerate	#remove the equivalent to 2 seconds of playtime
                count = 0
                binario = b''
        binario += b'\x00\x00\x00\x00\x00\x00\xFE'
        t = time.time() - t0
        #print(bcolors.ENDC)
        #print('['+str(conn.id)+'] ',datetime.datetime.now().isoformat(sep=' ', timespec='milliseconds'),'Stream completed in '+bcolors.OKGREEN+str(t)+bcolors.ENDC+' seconds')	#This one cannot be replaced by _LOG()... yet
        _LOG('Stream completed in '+bcolors.OKGREEN+str(round(t,2))+bcolors.ENDC+' seconds',id=conn.id)
    conn.Sendallbin(binario)
    time.sleep(1)
    #conn.Sendall(chr(P.DELETE))
    conn.socket.settimeout(_tout)


# Sends program file into the client memory at the correct address
def SendProgram(conn,filename):
    # Verify .prg extension
    if filename[-4:] == '.prg' or filename[-4:] == '.PRG':
        _LOG('Filename: '+filename, id=conn.id)
        # Open file
        archivo=open(filename,"rb")
        # Read load address
        binario=archivo.read(2)
        # Sync
        binariofinal = b'\x00'
        # Enter command mode
        binariofinal += b'\xFF'

        # Set the transfer pointer + load address (low:high)
        filesize = os.path.getsize(filename) - 2
        binariofinal += b'\x80'
        if isinstance(binario[0],str) == False:
            binariofinal += binario[0].to_bytes(1,'big')
            binariofinal += binario[1].to_bytes(1,'big')
        else:
            binariofinal += binario[0]
            binariofinal += binario[1]
        # Set the transfer pointer + program size (low:high)
        binariofinal += b'\x82'
        binariofinal += filesize.to_bytes(2,'little')
        _LOG('Load Address: '+bcolors.OKGREEN+str(binario[1]*256+binario[0])+bcolors.ENDC, '/ Bytes: '+bcolors.OKGREEN+str(filesize)+bcolors.ENDC,id=conn.id)
        # Program data
        binariofinal += archivo.read(filesize)

        # Exit command mode
        binariofinal += b'\xFE'
        # Close file
        archivo.close()
        # Send the data
        conn.Sendallbin(binariofinal)

# Sends a file directly
def SendRAWFile(conn,filename, wait=True):
    _LOG('Sending RAW file: ', filename, id=conn.id)

    archivo=open(filename,"rb")
    binario=archivo.read()
    conn.Sendallbin(binario)

    # Wait for the user to press RETURN
    if wait == True:
        WaitRETURN(conn)


def WaitRETURN(conn,timeout = 60.0):
    # Wait for user to press RETURN
    _LOG('Waiting for the user to press RETURN...',id=conn.id)
    tecla = b''
    conn.socket.settimeout(timeout)
    while conn.connected == True and tecla != b'\r':
        tecla = conn.Receive(1)
        if tecla == b'':
            conn.connected = False
    conn.socket.settimeout(_tout)
    if conn.connected == False:
        try:
            conn.socket.sendall(b'tIMEOUT - dESCONECTADO ')
        except socket.error:
            pass
    _LOG(bcolors.OKBLUE+str(tecla)+bcolors.ENDC,id=conn.id)

def WaitKey(conn):
    # Wait for the user to press any key
    _LOG('Waiting for the user to press a key...',id=conn.id)
    tecla = b''
    conn.socket.settimeout(60.0)
    tecla = conn.Receive(1)
    if tecla == b'':
        conn.connected = False
        try:
            conn.socket.sendall(b'tIMEOUT - dESCONECTADO ')
        except socket.error:
            pass
    conn.socket.settimeout(_tout)

# Logoff
def LogOff(conn, confirmation=True):
    global bbs_instance

    lan = {'en':['aRE YOU SURE (y/n)? ','YN','dISCONNECTED'],'es':['eSTA SEGURO (s/n)? ','SN','dESCONECTADO']}

    l_str = lan.get(bbs_instance.lang,lan['en'])

    if confirmation == True:
        conn.Sendall(chr(P.DELETE)*23 + chr(P.LT_GREEN) + l_str[0] + chr(P.WHITE))
        time.sleep(1)
        data = ''
        #while data != b'Y' and data != b'N':
        #	data = conn.Receive(1)
        data = conn.ReceiveKey(bytes(l_str[1],'ascii'))
        if data == bytes(l_str[1][0],'ascii'):
            _LOG('Disconnecting...\r',id=conn.id)
            conn.Sendallbin(data)
            time.sleep(1)
            conn.Sendall(chr(P.WHITE) + '\r\r'+bbs_instance.GBMess+'\r')
            time.sleep(1)
            conn.Sendall(chr(P.LT_BLUE) + '\r'+l_str[2]+'\r'+chr(P.WHITE))
            time.sleep(1)
            conn.connected = False	#break
            return True
        else:
            return False
    else:
        conn.connected = False
        return True


# Switch menu
def SwitchMenu(conn, id):
    if id-1 != conn.menu:
        if len(conn.MenuDefs) != 0:
            conn.MenuStack.append([conn.MenuDefs,conn.menu])
        conn.menu = id-1
        conn.MenuDefs = GetKeybindings(conn,id-1)
        #Function = conn.MenuDefs[b'\r'][0]
        #Function(*conn.MenuDefs[b'\r'][1])

        #conn.newmenu = id-1	#replace


# Paginate current menu
def SetPage(conn,page):
    #global MenuParameters

    if conn.MenuParameters != {}:
        conn.MenuParameters['current'] = page


# Generate keybindings
def GetKeybindings(conn,id):
    menu = bbs_instance.MenuList[id]
    kb = {}
    for cat in menu['entries']:
        #kb.update(cat['entrydefs'])
        for e in cat['entrydefs']:
            #print[e,cat]
            kb[e] = cat['entrydefs'][e].copy()
            if isinstance(kb[e][2],tuple):
                kb[e][2]=kb[e][2][0]
            kb[e][1] = (conn,)+kb[e][1]
    return kb

#######################################################
##					  BBS Loop						 ##
#######################################################

def BBSLoop(conn):
    global bbs_instance
    try:
        # Sync
        conn.Sendall(chr(0)*2)
        # # Text mode + Page number: 0 (default) + Border color: 0 (negro) + Background color: 0 (negro)
        conn.Sendall(TT.to_Text(0,0,0))
        # Send speech message
        conn.Sendall(TT.to_Speech() + '.bienvenido,p\'r2esioneritarn,')
        time.sleep(1)
        # Select screen output
        conn.Sendall(TT.to_Screen())
        # Clear screen + Lower/uppercase charset
        conn.Sendall(chr(P.CLEAR) + chr(P.TOLOWER))
        # Cyan ink
        conn.Sendall(chr(P.CYAN) + '\r'+bbs_instance.WMess+'\r')
        # Light blue ink
        if bbs_instance.lang == 'es':
            conn.Sendall(chr(P.LT_BLUE) + '\rpRESIONE return...\r')
        else:
            conn.Sendall(chr(P.LT_BLUE) + '\rpRESS return...\r')

        # Connected, wait for the user to press RETURN
        WaitRETURN(conn)

        # Ask for ID and supported TURBO56K version
        conn.Sendall(chr(255) + chr(162) + chr(254))
        time.sleep(1)
        datos = ""
        conn.socket.settimeout(10.0)
        datos = conn.Receive(2)
        conn.socket.settimeout(_tout)
        _LOG('ID:', datos,id=conn.id)
        if datos == b"RT":
            datos = conn.Receive(20)
            _LOG('Terminal: ['+ bcolors.OKGREEN + str(datos) + bcolors.ENDC + ']',id=conn.id)
            dato1 = conn.Receive(1)
            dato2 = conn.Receive(1)
            _LOG('TURBO56K version: '+ bcolors.OKGREEN + str(ord(dato1)) + '.' + str(ord(dato2)) + bcolors.ENDC,id=conn.id) 

            if b"RETROTERM-SL" in datos:
                _LOG('SwiftLink mode, audio streaming at 7680Hz',id=conn.id)
                conn.samplerate = 7680

            t56kver = ord(dato1)+((ord(dato2))/10)

            if t56kver > 0.4:
                _LOG('Sending intro pic',id=conn.id)
                bg = FT.SendBitmap(conn,'bbsfiles/splash.art',12,False)
                _LOG('Spliting Screen',id=conn.id)
                conn.Sendall(TT.split_Screen(12,False,ord(bg),0))
                time.sleep(1)
                conn.Sendall(chr(P.CLEAR)+chr(P.LT_BLUE)+"tURBO56K V"+str(t56kver)+" DETECTED\r\r")
                conn.Sendall("lINE FILL "+chr(P.LT_GREEN)+chr(P.CHECKMARK)+'\r')
                conn.Sendall(chr(P.LT_BLUE)+"sid STREAMING "+chr(P.LT_GREEN)+chr(P.CHECKMARK)+"\r")
                conn.Sendall(chr(P.LT_BLUE)+"sPLIT sCREEN "+chr(P.LT_GREEN)+chr(P.CHECKMARK)+"\r")
                conn.Sendall(chr(P.LT_BLUE)+"tEXT WINDOW "+chr(P.LT_GREEN)+chr(P.CHECKMARK)+"\r")
                conn.Sendall(chr(P.LT_BLUE)+"pcm AUDIO SAMPLERATE "+chr(P.YELLOW)+str(conn.samplerate)+"\r\r")
                conn.Sendall(chr(P.WHITE)+"vIEW (i)NTRO OR (s)KIP")
                time.sleep(1)
                t = conn.ReceiveKey(b'IS')
                time.sleep(1)
                if not conn.connected:
                    return()
                conn.Sendall(chr(0)*2+TT.split_Screen(0,False,0,0)+chr(P.CLEAR)) #Sendall(chr(0)+..
                if t == b'I':
                    SlideShow(conn,'','bbsfiles/intro/')
                    conn.Sendall(TT.enable_CRSR())
                else:
                    conn.Sendall(chr(0)*2+TT.split_Screen(0,False,0,0)) #Sendall(chr(0)+..
            else:
                _LOG('Old terminal detected - Terminating',id=conn.id)
                conn.Sendall('pLEASE USE retroterm V0.13 OR POSTERIOR'+chr(P.WHITE))
                conn.connected = False


            # Display the main menu

            conn.menu = 0		# Starting at the main menu
            conn.MenuDefs = GetKeybindings(conn,0)
            SendMenu(conn)

            while conn.connected == True and _run == True:
                data = conn.Receive(1)
                _LOG('received "'+bcolors.OKBLUE+str(data)+bcolors.ENDC+'"',id=conn.id)
                if data != b'' and conn.connected == True:
                    #print(conn.id,conn.MenuStack)
                    #print(conn.MenuDefs)
                    if data in conn.MenuDefs:
                        prompt = conn.MenuDefs[data][2] if len(conn.MenuDefs[data][2])<20 else conn.MenuDefs[data][2][:17]+'...'
                        conn.Sendall(prompt)	#Prompt
                        time.sleep(1)
                        wait = conn.MenuDefs[data][4]
                        Function = conn.MenuDefs[data][0]
                        #print('f1')
                        res = Function(*conn.MenuDefs[data][1])
                        if isinstance(res,dict):
                            conn.MenuDefs = res
                            #print('change')
                        elif data!=b'\r':
                            if wait:
                                WaitRETURN(conn,60.0*5)
                                conn.Sendall(TT.enable_CRSR())	#Enable cursor blink just in case
                            Function = conn.MenuDefs[b'\r'][0]
                            #print('f2')
                            res = Function(*conn.MenuDefs[b'\r'][1])
                            if isinstance(res,dict):
                                conn.MenuDefs = res
                    else:
                        continue
                else:
                    _LOG('no more data from', conn.addr, id=conn.id)
                    break

        else:
            conn.Sendall(chr(P.CYAN) + '\r\ntHIS bbs REQUIRES A TERMINAL\r\nCOMPATIBLE WITH turbo56k 0.3 OR NEWER.\r\n')
            conn.Sendall(chr(P.LT_BLUE) + 'dISCONNECTED...')
            time.sleep(1)
            _LOG('Not a compatible terminal, disconnecting...',id=conn.id)
            # Clean up the connection
            conn.socket.close()
    finally:
        # Clean up the connection
        conn.socket.close()
        _LOG('Disconnected',id=conn.id)


## Connection check thread ##
def ConnTask():
    global conlist

    while _run:
        time.sleep(1) # check once per second
        for t in range(1,6):
            if t in conlist:				#Find closed connections
                if not conlist[t][0].is_alive():
                    conlist[t][1].Close()
                    del conlist[t][1]
                    try:
                        conlist[t][0].join()
                    except:
                        pass
                    conlist.pop(t)
                    _LOG('Slot freed - Awaiting a connection')

#######################################################
##              		MAIN                         ##
#######################################################

# Initialize variables

print('\n\nRetroBBS v0.10 (c)2021\nby Pablo Roldán(durandal) and\nJorge Castillo(Pastbytes)\n\n')


bbs_instance = BBS('','',0)

# Parse plugins
p_mods = [importlib.import_module(name) for finder, name, ispkg in iter_namespace(plugins)]
for a in p_mods:
    fname,parms = a.setup()
    PlugDict[fname] = [a.plugFunction,parms] 
    _LOG('Loaded plugin: '+fname)


# Read config file
ConfigRead()

# Register CTRL-C handler
signal.signal(signal.SIGINT, signal_handler)

# Create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Bind the socket to the port
server_address = (bbs_instance.ip, bbs_instance.port)
_LOG('Initializing server on %s port %s' % server_address)
sock.bind(server_address)

# Listen for up to 5 incoming connections
sock.listen(5)

#Ignore LibRosa filetype Warnings
warnings.filterwarnings("ignore", message="PySoundFile failed. Trying audioread instead.")

#List of current active connections
conlist = {}

conthread = threading.Thread(target = ConnTask, args = ())
conthread.start()

while True:
    # Wait for a connection
    _LOG('Awaiting a connection')
    c, c_addr = sock.accept()

    newid = 1
    for r in range(1,6):			#Find free id
        if r not in conlist:
            newid = r
            break
    newconn = Connection(c,c_addr,bbs_instance,newid)
    
    conlist[newid] = [threading.Thread(target = BBSLoop, args=(newconn,)),newconn]
    conlist[newid][0].start()

    
