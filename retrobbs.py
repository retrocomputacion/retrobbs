#################################################################################################
# RetroBBS 0.20 (compatible with TURBO56K 0.6 and retroterm 0.14                              	#
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
# March		16 - 2021:	SendCPetscii() and SendPETPetscii() added, support for .c and .pet files#
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
# Late 2021-May 2022 :  Audio functions moved to their own module, started database handling,   #
#                       user login, etc.                                                        #
#                       MenuDef index 3 now stores the minimun user class needed to access menu #
#################################################################################################


from __future__ import print_function

import argparse
import time
import socket
import sys
import re
import platform
import subprocess
from os import walk
import datetime
import signal
import string
import itertools
import configparser #INI file parser
import threading

#Petscii
import common.petscii as P

#Turbo56K
from common import turbo56k as TT

from common.classes import BBS
from common.connection import Connection
from common.bbsdebug import _LOG, bcolors, set_verbosity
from common.helpers import MenuBack, valid_keys, formatX, More, SetPage
from common.style import KeyPrompt, bbsstyle, default_style, RenderMenuTitle, KeyLabel
from common import audio as AA
from common import messaging as MM

#File transfer functions
import common.filetools as FT

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


##################################
# BBS Version                    #
_version = 0.20                  #
##################################


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

    #Iterate Section Entries
    def EIter(cfg, key, sentry):
        for e in range(0,sentry['entries']):
            tentry = cfg[key]['entry'+str(e+1)+'title']	#Entry Title
            if sentry['columns'] < 2:
                dentry = cfg.get(key,'entry'+str(e+1)+'desc', fallback = '')
                if dentry != '':
                    tentry = (tentry,dentry)
            ekey = bytes(cfg[key]['entry'+str(e+1)+'key'],'ascii')		#Entry Key binding
            efunc = cfg[key]['entry'+str(e+1)+'func']		#Entry Internal function
            level = cfg.getint(key,'entry'+str(e+1)+'level', fallback = 0)
            if efunc in func_dic:
                #[function_call, parameters, title, ???, wait]
                sentry['entrydefs'][ekey] = [func_dic[efunc],None,tentry,level,False]
            elif efunc in PlugDict:
                sentry['entrydefs'][ekey] = [PlugDict[efunc][0],None,tentry,level,False]
            else:
                raise Exception('config.ini - Unknown function at: '+'entry'+str(e+1)+'func')
            #Parse parameters
            parms = []
            if efunc == 'IMAGEGALLERY':		#Show image file list
                p = cfg.get(key, 'entry'+str(e+1)+'path', fallback='images')
                parms= [tentry,'','Displaying image list',p,('.art','.ocp','.koa','.kla','.ART','.OCP','.KOA','.KLA','.gif','jpg','png','.GIF','.JPG','PNG'),FT.SendBitmap]
            elif efunc == 'SWITCHMENU':		#Switch menu
                parms = [cfg[key].getint('entry'+str(e+1)+'id')]
            elif efunc == 'FILES':			#Show file list
                exts = tuple((cfg.get(key,'entry'+str(e+1)+'ext', fallback='.prg,.PRG')).split(','))
                p = cfg.get(key, 'entry'+str(e+1)+'path', fallback='programs')
                parms = [tentry,'','Displaying file list',p,exts,FT.SendProgram]
            elif efunc == 'AUDIOLIBRARY':	#Show audio file list
                p = cfg.get(key, 'entry'+str(e+1)+'path', fallback='sound')
                parms = [tentry,'','Displaying audio list',p]
            elif efunc == 'PCMPLAY':		#Play PCM audio
                parms = [cfg.get(key, 'entry'+str(e+1)+'path', fallback='bbsfiles/bbsintroaudio-eng11K8b.wav')]
            elif efunc == 'SLIDESHOW':		#Iterate through and show all supported files in a directory
                parms = [tentry,cfg.get(key, 'entry'+str(e+1)+'path', fallback='bbsfiles/pictures')]
            elif efunc == 'INBOX':
                parms = [0]
            elif efunc == 'BOARD':
                parms = [cfg.getint(key,'entry'+str(e+1)+'id', fallback = 1)]
            elif efunc == 'BACK' or efunc == 'EXIT' or efunc == 'USEREDIT' or efunc =='USERLIST' or efunc == 'MESSAGE':
                parms = []
            elif efunc in PlugDict:			#Plugin function
                parms = []
                for p in PlugDict[efunc][1]:	#Iterate parameters
                    ep = cfg.get(key, 'entry'+str(e+1)+p[0], fallback=p[1])
                    if isinstance(p[1],tuple) == True and isinstance(ep,tuple) == False:
                        ep = tuple([int(e) if e.isdigit() else 0 for e in ep.split(',')])
                    parms.append(ep)

            # This tuple need to be added to one (conn,) on each connection instance when calling func
            # also needs conn.MenuParameters added to this
            # finaltuple = (conn,)+ _parms_
            sentry['entrydefs'][ekey][1] = tuple(parms)
        return(sentry)


    #Iterate Menu Sections
    def MIter(cfg, key, mentry):
        for s in range(0, mentry['sections']):
            skey = key+str(s+1)
            tsection = cfg[skey]['title']						#Section Title
            ecount = cfg[skey].getint('entries')				#Section number of entries
            scolumns = cfg[skey].getint('columns', fallback= 2)
            mentry['entries'][s] = {'title':tsection,'entries':ecount,'columns':scolumns,'entrydefs':{}}
            mentry['entries'][s] = EIter(cfg, skey, mentry['entries'][s])
        return(mentry)
    
    #Internal function dictionary
    func_dic = {'IMAGEGALLERY': FileList,	#+
                'AUDIOLIBRARY': AA.AudioList,	#+
                'FILES': FileList,			#+
                'SENDRAW': FT.SendRAWFile,
                'SWITCHMENU': SwitchMenu,	#+
                'SLIDESHOW': SlideShow,		#+
                'SIDPLAY': AA.SIDStream,
                'PCMPLAY': AA.PlayAudio,		#+
                'TEXT': SendText,
                'SHOWPIC': FT.SendBitmap,
                'EXIT': LogOff,				#+
                'BACK': MenuBack,
                'USEREDIT': EditUser,
                'USERLIST': UserList,       #+
                'BOARD': MM.inbox,
                'INBOX': MM.inbox}			#+tmp

    config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
    config.read('config.ini')

    #MAIN variables

    bbs_instance.name = config['MAIN']['bbsname']
    bbs_instance.ip = config['MAIN']['ip']
    bbs_instance.port = config['MAIN'].getint('port')
    bbs_instance.lang = config['MAIN']['language']
    bbs_instance.WMess = config['MAIN'].get('welcome', fallback='Welcome!')
    bbs_instance.GBMess = config['MAIN'].get('goodbye', fallback='Goodbye!')

    bbs_instance.dateformat = config['MAIN'].getint('dateformat', fallback=1)

    #Parse Menues
    mcount = config['MAIN'].getint('menues')								#Number of menues

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
        _bbs_menues[m] = MIter(config,tkey,_bbs_menues[m])
        _bbs_menues[m]['entries'][0]['entrydefs'][b'\r']=[SendMenu,(),'',False,False]

    bbs_instance.MenuList = _bbs_menues

    #Get any message boards options
    try:
        bbs_instance.BoardOptions = dict(config.items('BOARDS'))
    except:
        bbs_instance.BoardOptions = {}

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
    global bbs_instance

    _LOG('Ctrl+C! Bye!', v=3)
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


def FileList(conn:Connection,title,speech,logtext,path,ffilter,fhandler):

    if conn.menu != -1:
        conn.MenuStack.append([conn.MenuDefs,conn.menu])
        conn.menu = -1
    # Init Menu parameter dictionary if needed
    if conn.MenuParameters == {}:
        conn.MenuParameters['current'] = 0

    # Start with barebones MenuDic
    MenuDic = { 
                b'_': (MenuBack,(conn,),"Previous Menu",0,False),
                b'\r': (FileList,(conn,title,speech,logtext,path,ffilter,fhandler),title,0,False)
              }	

    _LOG(logtext,id=conn.id, v=4)
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
        MenuDic[b'<'] = (SetPage,(conn,page),'Previous Page',0,False)
        if conn.MenuParameters['current'] == pages-1:
            page = 0
        else:
            page = conn.MenuParameters['current']+1
        MenuDic[b'>'] = (SetPage,(conn,page),'Next Page',0,False)

    if fhandler == FT.SendProgram:
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
        KeyLabel(conn, valid_keys[x-start], (programs[x][:len(programs[x])-4]+' '*16)[:16]+('\r'if x%2 else ' '), (x % 4)<2)
        #Add keybinding to MenuDic
        if fhandler == FT.SendProgram:
            parameters = (conn,path+programs[x],)
        else:
            parameters = (conn,path+programs[x],25,True,True,)
        MenuDic[valid_keys[x-start].encode('ascii','ignore')] = (fhandler,parameters,valid_keys[x-start],0,keywait)
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
def SendMenu(conn:Connection):
    global bbs_instance

    if conn.menu < 0:
        return()
    conn.Sendall(TT.to_Text(0,0,0)+TT.to_Screen())	#Set Screen Text mode output
    tmenu = bbs_instance.MenuList[conn.menu]	#Change to simply tmenu = conn.MenuDefs
    _LOG("Sending menu: "+tmenu['title'],id=conn.id,v=4)
    RenderMenuTitle(conn,tmenu['title'])
    conn.Sendall('\r')
    for s in tmenu['entries']:
        #Sections
        conn.Sendall(' '+chr(P.WHITE)+P.toPETSCII(s['title'])+'\r')
        conn.Sendall(chr(P.LT_GREEN)+chr(176)+38*chr(P.HLINE)+chr(174))

        #Items
        count = 0
        toggle = False
        if s['columns'] < 2:
            sw = 1
            tw = 37
        else:
            sw = 2
            tw = 17
        for i in s['entrydefs']:
            if i == b'\r':
                continue

            if isinstance(s['entrydefs'][i][2],tuple):
                t = s['entrydefs'][i][2][0]
                desc = formatX(s['entrydefs'][i][2][1],columns=36)
            else:
                t = s['entrydefs'][i][2]
                desc =''

            title = t if len(t)<tw else t[0:tw-4]+'...'

            KeyLabel(conn,chr(i[0]),title, toggle)
            if count % sw == 0:
                toggle = not toggle
                line = ' '*(tw-1-len(title))+(' 'if sw == 2 else chr(P.GREEN)+chr(P.VLINE))
                conn.Sendall(line)
            else:
                conn.Sendall(' '*(19-(len(title)+3))+chr(P.GREEN)+chr(P.VLINE))
            if desc != '':
                tdesc = ''
                for l in desc:
                    tdesc += chr(P.LT_GREEN)+chr(P.VLINE)+chr(P.WHITE)+'  '+l+((36-len(l))*' ')+chr(P.GREEN)+chr(P.VLINE)
                conn.Sendall(tdesc)
            count += 1
        if (count % sw == 1) and (sw == 2):
            conn.Sendall(' '*19+chr(P.GREEN)+chr(P.VLINE))


        conn.Sendall(chr(173)+38*chr(P.HLINE)+chr(189))
    ####
    conn.Sendall(TT.set_CRSR(0,24)+chr(P.WHITE)+' '+P.toPETSCII(tmenu['prompt'])+' ')
    #WaitRETURN(conn)


def SendText(conn:Connection, filename, title='', lines=25):
    colors = (P.BLACK,P.WHITE,P.RED,P.PURPLE,P.CYAN,P.GREEN,P.BLUE,P.YELLOW,P.BROWN,P.PINK,P.ORANGE,P.GREY1,P.GREY2,P.LT_BLUE,P.LT_GREEN,P.GREY3)
    if title != '':
        RenderMenuTitle(conn, title)
        l = 22
        conn.Sendall(TT.set_Window(3,24))
    else:
        l = lines
        conn.Sendall(chr(P.CLEAR))

    if filename.endswith(('.txt','.TXT')):
        #Convert plain text to PETSCII and display with More
        tf = open(filename,"r")
        ot = tf.read()
        tf.close()
        text = formatX(ot)

        More(conn,text,l)

    elif filename.endswith(('.seq','.SEQ')):
        prompt='RETURN'
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
            elif char[0] == P.CRSR_RIGHT:
                cc += 1
            elif char[0] == P.CRSR_LEFT or char == P.DELETE:
                cc -= 1
            elif char[0] == P.CRSR_UP:
                ll -= 1
            elif char[0] == P.CRSR_DOWN:
                ll += 1
            elif char == b'\x0d':
                ll += 1
                cc = 0
                rvs = ''
            elif char[0] == P.HOME or char[0] == P.CLEAR:
                ll = 0
                page = 0
                cc = 0
            elif char[0] in colors:
                color = chr(char[0])
            elif char[0] == P.RVS_ON:
                rvs = chr(P.RVS_ON)
            elif char[0] == P.RVS_OFF:
                rvs = ''
            elif char[0] == P.TOLOWER:
                prompt = 'RETURN'
            elif char[0] == P.TOUPPER:
                prompt = 'return'
            if cc == 40:
                cc = 0
                ll += 1
            elif cc < 0:
                if ll!=l*page:
                    cc = 39
                    ll -= 1
                else:
                    cc = 0
            if ll < l*page:
                ll = l*page
            elif ll >= (l*page)+(l-1):
                if cc !=0:
                    conn.Sendall('\r')
                conn.Sendall(KeyPrompt(prompt+' OR _'))
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
        conn.Sendall(KeyPrompt(prompt))
        conn.ReceiveKey()

    if lines == 25:
        conn.Sendall(TT.set_Window(0,24))
    return -1
#######

def SendCPetscii(conn:Connection,filename,pause=0):
    try:
        fi = open(filename,'r')
    except:
        return()
    text = fi.read()
    fi.close
    #### Falta fijarse si es upper o lower
    if text.find('upper') != -1:
        conn.Sendall(chr(P.TOUPPER))
    else:
        conn.Sendall(chr(P.TOLOWER))
    frames = text.split('unsigned char frame')
    for f in frames:
        if f == '':
            continue
        binary = b''
        fr = re.sub('(?:[0-9]{4})*\[\]={// border,bg,chars,colors\n','',f)
        fl = fr.split('\n')
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
        binary+= b'\x81\x20\x82\xe8\x03'
        i = 0
        for line in fl[26:52]:
            for c in line.split(','):	#Color RAM
                if c.isnumeric():
                    binary += int(c).to_bytes(1,'big')
                    i+=1
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

def SendPETPetscii(conn:Connection,filename):
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
    binary += b'\x81\x20\x82\xe8\x03'
    binary += pet[1005:]
    conn.Sendallbin(binary)
    #time.sleep(5)
    return -1

# Display sequentially all matching files inside a directory
def SlideShow(conn:Connection,title,path,delay = 1, waitkey = True):
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
    sid_e = ('.sid','.SID')

    #Keeps only the files with matching extension 
    for f in files:
        if f.endswith(pics_e + text_e + bin_e + pet_e + aud_e + sid_e):
            slides.append(f)

    slides.sort()	#Sort list

    #Iterate through files
    for p in slides:
        w = 0
        conn.Sendall(TT.enable_CRSR()+chr(P.CLEAR))
        _LOG('SlideShow - Showing: '+p,id=conn.id,v=4)
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
            AA.PlayAudio(conn,path+p,None)
            w = 1
        elif ext in sid_e:
            AA.SIDStream(conn,path+p,None,False)
            w = 1
        # Wait for the user to press RETURN
        if waitkey == True and w == 0:
            WaitRETURN(conn,60.0*5)
        else:
            time.sleep(delay)

        conn.Sendall(TT.to_Text(0,0,0))
    conn.Sendall(TT.enable_CRSR())

def WaitRETURN(conn:Connection,timeout = 60.0):
    # Wait for user to press RETURN
    _LOG('Waiting for the user to press RETURN...',id=conn.id,v=4)
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
    _LOG(bcolors.OKBLUE+str(tecla)+bcolors.ENDC,id=conn.id,v=4)

def WaitKey(conn:Connection):
    # Wait for the user to press any key
    _LOG('Waiting for the user to press a key...',id=conn.id,v=4)
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
def LogOff(conn:Connection, confirmation=True):
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
            _LOG('Disconnecting...\r',id=conn.id,v=3)
            conn.Sendallbin(data)
            time.sleep(1)
            conn.Sendall(chr(P.WHITE) + '\r\r'+P.toPETSCII(bbs_instance.GBMess)+'\r')
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

# Generate keybindings
def GetKeybindings(conn:Connection,id):
    global bbs_instance

    menu = bbs_instance.MenuList[id]
    kb = {}
    for cat in menu['entries']:
        #kb.update(cat['entrydefs'])
        for e in cat['entrydefs']:
            kb[e] = cat['entrydefs'][e].copy()
            if isinstance(kb[e][2],tuple):
                kb[e][2]=kb[e][2][0]
            kb[e][1] = (conn,)+kb[e][1]
    return kb

# SignIn/SignUp
def SignIn(conn:Connection):
    global bbs_instance

    # dateord = [[0,1,2],[1,0,2],[2,1,0]]
    # dateleft = [[0,3,3],[3,0,3],[3,5,0]]

    keys = string.ascii_letters + string.digits + ' +-_,.$%&'
    conn.Sendall(chr(P.CLEAR)+chr(P.CYAN)+'uSERNAME:')
    Done = False
    while not Done:
        name = conn.ReceiveStr(bytes(keys,'ascii'), 16, False)
        if not conn.connected:
            return
        while len(name) > 0 and len(name) < 6:
            conn.Sendall('\ruSERNAME MUST BE 6 TO 16 CHARACTERS\rLONG, TRY AGAIN:')
            name = conn.ReceiveStr(bytes(keys,'ascii'), 16, False)
            if not conn.connected:
                return
        #name = P.toASCII(name)
        if len(name) > 0 and P.toASCII(name) != '_guest_':
            uentry = bbs_instance.database.chkUser(P.toASCII(name))
            if uentry != None:
                retries = 3
                if uentry['online'] == 1:
                    Done = True
                    conn.Sendall('\ruSER ALREADY LOGGED IN\r')
                while (not Done) and (retries > 0):
                    conn.Sendall('\rpASSWORD:')
                    if bbs_instance.database.chkPW(uentry, P.toASCII(conn.ReceiveStr(bytes(keys,'ascii'), 16, True))):
                        conn.Sendall(chr(P.LT_GREEN)+'\rlOGIN SUCCESSFUL'+chr(7)+chr(P.CHECKMARK))
                        conn.username = P.toASCII(name)
                        conn.userid = uentry.doc_id
                        conn.userclass = uentry['uclass']
                        time.sleep(1)
                        Done = True
                    else:
                        retries -= 1
                        conn.Sendall(chr(P.RED)+'\rpASSWORD INCORRECT'+chr(P.CYAN))
                        time.sleep(1)
                if retries == 0:
                    Done = True
                if not conn.connected:
                    return
            else:
                conn.Sendall('\ruSER NOT FOUND, REGISTER (y/n)?')
                if conn.ReceiveKey(b'YN') == b'Y':
                    # dord = dateord[conn.bbs.dateformat]
                    # dleft = dateleft[conn.bbs.dateformat]
                    if conn.bbs.dateformat == 1:
                        datestr = "%m/%d/%Y"
                        dout = "mm/dd/yyyy"
                    elif conn.bbs.dateformat == 2:
                        datestr = "%Y/%m/%d"
                        dout = "yyyy/mm/dd"
                    else:
                        datestr = "%d/%m/%Y"
                        dout = "dd/mm/yyyy"
                    if not conn.connected:
                        return
                    if conn.TermFt[51] != 80:
                        lines = 13
                    else:
                        lines = 25
                    SendText(conn,'bbsfiles/terms/rules.txt','',lines)
                    conn.Sendall('\rrEGISTERING USER '+name+'\riNSERT YOUR PASSWORD:')
                    pw = conn.ReceiveStr(bytes(keys,'ascii'), 16, True)
                    if not conn.connected:
                        return
                    while len(pw) < 6:
                        conn.Sendall('\rpASSWORD MUST BE 6 TO 16 CHARACTERS LONGiNSERT YOUR PASSWORD:')
                        pw = conn.ReceiveStr(bytes(keys,'ascii'), 16, True)
                        if not conn.connected:
                            return
                    conn.Sendall('\rfIRST NAME:')
                    fname = conn.ReceiveStr(bytes(keys,'ascii'), 16)
                    if not conn.connected:
                        return
                    conn.Sendall('\rlAST NAME:')
                    lname = conn.ReceiveStr(bytes(keys,'ascii'), 16)
                    if not conn.connected:
                        return
                    conn.Sendall('\rcOUNTRY:')
                    country = conn.ReceiveStr(bytes(keys,'ascii'), 16)
                    if not conn.connected:
                        return
                    bday = conn.ReceiveDate('\rbIRTHDATE: ',datetime.date(1900,1,1),datetime.date.today(),datetime.date(1970,1,1))
                    conn.username = P.toASCII(name)
                    conn.userid = bbs_instance.database.newUser(P.toASCII(name), P.toASCII(pw), P.toASCII(fname), P.toASCII(lname), bday.strftime("%d/%m/%Y"), P.toASCII(country))
                    _LOG('NEW USER: '+name,v=3)
                    conn.userclass = 1
                    conn.Sendall('\rrEGISTRATION COMPLETE, WELCOME!')
                    Done = True
                    time.sleep(1)
                    conn.Sendall(chr(P.YELLOW)+'\ryOUR USER DATA:\r'+chr(P.GREEN)+chr(P.HLINE)*14+'\r')
                    conn.Sendall(chr(P.ORANGE)+'uSER NAME: '+chr(P.WHITE)+name+'\r')
                    conn.Sendall(chr(P.ORANGE)+'pASSWORD: '+chr(P.WHITE)+('*'*len(pw))+'\r')
                    conn.Sendall(chr(P.ORANGE)+'fIRST NAME: '+chr(P.WHITE)+fname+'\r')
                    conn.Sendall(chr(P.ORANGE)+'lAST NAME: '+chr(P.WHITE)+lname+'\r')
                    conn.Sendall(chr(P.ORANGE)+'bIRTHDATE '+chr(P.WHITE)+bday.strftime(datestr)+'\r')
                    conn.Sendall(chr(P.ORANGE)+'cOUNTRY: '+chr(P.WHITE)+country+'\r')
                    time.sleep(1)
                    conn.Sendall('\r'+chr(P.YELLOW)+"dO YOU WANT TO EDIT YOUR DATA (y/n)?")
                    if conn.ReceiveKey(b'YN') == b'Y':
                        if not conn.connected:
                            return
                        #Edit user data
                        EditUser(conn)
                else:
                    Done = True
                if not conn.connected:
                    return
        else:
            Done = True
#

# Edit logged in user
# This always runs outside the mainloop regardless of where is called
def EditUser(conn:Connection):
    _LOG('Editing user '+conn.username, v=3)
    keys = string.ascii_letters + string.digits + ' +-_,.$%&'
    if conn.bbs.dateformat == 1:
        datestr = "%m/%d/%Y"
        dout = "mm/dd/yyyy"
    elif conn.bbs.dateformat == 2:
        datestr = "%Y/%m/%d"
        dout = "yyyy/mm/dd"
    else:
        datestr = "%d/%m/%Y"
        dout = "dd/mm/yyyy"
    if conn.userid == 0:
        return
    conn.Sendall(TT.split_Screen(0,False,0,0)) # Cancel any split screen/window
    done = False
    while (not done) and conn.connected:
        uentry = bbs_instance.database.chkUser(conn.username)
        RenderMenuTitle(conn,"Edit User Data")
        conn.Sendall(chr(P.CRSR_DOWN)*2)
        KeyLabel(conn,'a','Username: '+uentry['uname'],True)
        conn.Sendall('\r')
        KeyLabel(conn,'b','First name: '+uentry['fname'],False)
        conn.Sendall('\r')
        KeyLabel(conn,'c','Last name: '+uentry['lname'],True)
        conn.Sendall('\r')
        KeyLabel(conn,'d','Birthdate: '+datetime.datetime.strptime(uentry['bday'],'%d/%m/%Y').strftime(datestr),False)
        conn.Sendall('\r')
        KeyLabel(conn,'e','Country: '+uentry['country'],True)
        conn.Sendall('\r')
        KeyLabel(conn,'f','Change password',False)
        conn.Sendall('\r')
        KeyLabel(conn,'_','Exit',True)
        conn.Sendall('\r\r')
        conn.Sendall(TT.Fill_Line(12,64)+'pRESS OPTION')
        k = conn.ReceiveKey(b'ABCDEF_')
        if k == b'_':
            done = True
        elif k == b'A': #Username
            n = False
            conn.Sendall('\r'+chr(P.CRSR_UP))
            while not n:
                conn.Sendall(TT.Fill_Line(13,32)+chr(P.YELLOW)+'nEW USERNAME:')
                name = P.toASCII(conn.ReceiveStr(bytes(keys,'ascii'), 16, False))
                if not conn.connected:
                    return
                if len(name) < 6:
                    conn.Sendall(chr(P.ORANGE)+'\ruSERNAME MUST BE 6 TO 16 CHARACTERS\rLONG, TRY AGAIN\r')
                    time.sleep(2)
                    conn.Sendall(TT.Fill_Line(14,32)+TT.Fill_Line(15,32)+(chr(P.CRSR_UP))*3)
                elif name == '_guest_':
                    conn.Sendall(chr(P.ORANGE)+'\riNVALID NAME\rTRY AGAIN\r')
                    time.sleep(2)
                    conn.Sendall(TT.Fill_Line(14,32)+TT.Fill_Line(15,32)+(chr(P.CRSR_UP))*3)
                elif name != conn.username:
                    tentry = bbs_instance.database.chkUser(name)
                    if tentry != None:
                        conn.Sendall(chr(P.ORANGE)+'\ruSERNAME ALREADY TAKEN\rTRY AGAIN:\r')
                        time.sleep(2)
                        conn.Sendall(TT.Fill_Line(14,32)+TT.Fill_Line(15,32)+(chr(P.CRSR_UP))*3)
                    else:
                        bbs_instance.database.updateUser(uentry.doc_id,name,None,None,None,None,None)
                        conn.username = name
                        n = True
                else:   #Same old username
                    n = True
        elif k == b'B': #First name
            conn.Sendall('\r'+chr(P.CRSR_UP))
            conn.Sendall(TT.Fill_Line(13,32)+'fIRST NAME:')
            fname = P.toASCII(conn.ReceiveStr(bytes(keys,'ascii'), 16))
            if not conn.connected:
                return
            bbs_instance.database.updateUser(uentry.doc_id,None,None,fname,None,None,None)
        elif k == b'C': #Last name
            conn.Sendall('\r'+chr(P.CRSR_UP))
            conn.Sendall(TT.Fill_Line(13,32)+'lAST NAME:')
            lname = P.toASCII(conn.ReceiveStr(bytes(keys,'ascii'), 16))
            if not conn.connected:
                return
            bbs_instance.database.updateUser(uentry.doc_id,None,None,None,lname,None,None,None)
        elif k == b'D': #Birthdate
            conn.Sendall('\r'+chr(P.CRSR_UP))
            conn.Sendall(TT.Fill_Line(13,32))
            bday = conn.ReceiveDate('\rbIRTHDATE: ',datetime.date(1900,1,1),datetime.date.today(),datetime.date(1970,1,1))
            if not conn.connected:
                return
            bbs_instance.database.updateUser(uentry.doc_id,None,None,None,None,bday.strftime("%d/%m/%Y"),None)
        elif k == b'E': #Country
            conn.Sendall('\r'+chr(P.CRSR_UP))
            conn.Sendall(TT.Fill_Line(13,32)+'cOUNTRY:')
            country = P.toASCII(conn.ReceiveStr(bytes(keys,'ascii'), 16))
            if not conn.connected:
                return
            bbs_instance.database.updateUser(uentry.doc_id,None,None,None,None,None,country)
        elif k == b'F': #Password
            n = 0
            conn.Sendall('\r'+chr(P.CRSR_UP))
            while n < 3:
                conn.Sendall(TT.Fill_Line(13,32)+'oLD PASSWORD:')
                pw = P.toASCII(conn.ReceiveStr(bytes(keys,'ascii'), 16, True))
                if not conn.connected:
                    return
                if bbs_instance.database.chkPW(uentry,pw,False):
                    m = False
                    conn.Sendall('\r'+chr(P.CRSR_UP))
                    while not m:
                        conn.Sendall(TT.Fill_Line(13,32)+'nEW PASSWORD:')
                        pw = P.toASCII(conn.ReceiveStr(bytes(keys,'ascii'), 16, True))
                        if not conn.connected:
                            return
                        if len(pw) < 6:
                            conn.Sendall(chr(P.ORANGE)+'\rpASSWORD MUST BE 6 TO 16 CHARACTERS\rLONG, TRY AGAIN\r')
                            time.sleep(2)
                            conn.Sendall(TT.Fill_Line(14,32)+TT.Fill_Line(15,32)+(chr(P.CRSR_UP))*3)
                        else:
                            bbs_instance.database.updateUser(uentry.doc_id,None,pw,None,None,None,None)
                            m = True
                            n = 3
                else:
                    conn.Sendall('\riNCORRECT PASSWORD\rTRY AGAIN\r')
                    time.sleep(2)
                    conn.Sendall(TT.Fill_Line(14,32)+TT.Fill_Line(15,32)+(chr(P.CRSR_UP))*3)
                    n += 1

# Display user list
def UserList(conn:Connection):
    if conn.menu != -1:
        conn.MenuStack.append([conn.MenuDefs,conn.menu])
        conn.menu = -1
    # Init Menu parameter dictionary if needed
    if conn.MenuParameters == {}:
        conn.MenuParameters['current'] = 0

    # Start with barebones MenuDic
    MenuDic = { 
                b'_': (MenuBack,(conn,),"Previous Menu",0,False),
                b'\r': (UserList,(conn,),"",0,False)
              }	
 
     # Select screen output
    conn.Sendall(TT.to_Screen())
    # Sync
    conn.Sendall(chr(0)*2)
    # # Text mode
    conn.Sendall(TT.to_Text(0,0,0))
    RenderMenuTitle(conn,"User list")

    users = bbs_instance.database.getUsers()
    digits = len(str(max(users[:])[0]))

    conn.Sendall(chr(P.WHITE)+" id         uSERNAME\r\r"+chr(P.LT_GREEN))
    conn.Sendall(TT.Fill_Line(4,64))

    pages = int((len(users)-1) / 18) + 1
    count = len(users)
    start = conn.MenuParameters['current'] * 18
    end = start + 17
    if end >= count:
        end = count - 1

    #Add pagination keybindings to MenuDic
    if pages > 1:
        if conn.MenuParameters['current'] == 0:
            page = pages-1
        else:
            page = conn.MenuParameters['current']-1
        MenuDic[b'<'] = (SetPage,(conn,page),'Previous Page',0,False)
        if conn.MenuParameters['current'] == pages-1:
            page = 0
        else:
            page = conn.MenuParameters['current']+1
        MenuDic[b'>'] = (SetPage,(conn,page),'Next Page',0,False)

    x = 0
    for x in range(start, end + 1):
        if x % 4 == 0 or x % 4 == 1:
            color1 = P.LT_BLUE
            color2 = P.GREY3
        if x % 4 == 2 or x % 4 == 3:
            color1 = P.CYAN
            color2 = P.YELLOW
        KeyLabel(conn, str(users[x][0]).zfill(digits), '   '+users[x][1]+'\r', x % 2)
    else:
        lineasimpresas = end - start + 1
        if lineasimpresas < 18:
            for x in range(18 - lineasimpresas):
                conn.Sendall('\r')
    conn.Sendall(' '+chr(P.GREY3)+chr(P.RVS_ON)+'_ '+chr(P.LT_GREEN)+'pREV. mENU '+chr(P.GREY3)+'< '+chr(P.LT_GREEN)+'pREV.pAGE '+chr(P.GREY3)+'> '+chr(P.LT_GREEN)+'nEXT pAGE  '+chr(P.RVS_OFF)+'\r')
    conn.Sendall(chr(P.WHITE)+' ['+str(conn.MenuParameters['current']+1)+'/'+str(pages)+']'+chr(P.CYAN)+' sELECTION:'+chr(P.WHITE)+' ')
    conn.Sendall(chr(255) + chr(161) + 'seleksioneunaopsion,')
    time.sleep(1)
    # Select screen output
    conn.Sendall(TT.to_Screen())
    return MenuDic

def GetTerminalFeatures(conn:Connection):

    if b"RETROTERM-SL" in conn.TermString:
        _LOG('SwiftLink mode, audio streaming at 7680Hz',id=conn.id,v=3)
        conn.samplerate = 7680
    if conn.T56KVer > 0.5:
        result = [b'\x80']*(TT.TURBO56K_LCMD-127)
        conn.Sendall(chr(TT.CMDON))
        for cmd in range(128,TT.TURBO56K_LCMD+1):
            conn.Sendall(chr(TT.QUERYCMD)+chr(cmd))
            result[cmd-128] = (conn.Receive(1))
        conn.Sendall(chr(TT.CMDOFF))
    else:
        result = [b'\x02',b'\x01',b'\x02',b'\x00',b'\x00',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',
                  b'\x03',b'\x02',b'\x03',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',
                  b'\x00',b'\x00',b'\x00',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',b'\x80',
                  b'\x02',b'\x02',b'\x01',b'\x02',b'\x80',b'\x02']
    conn.TermFt = result

def SendTerminalFeatures(conn:Connection):
 
    conn.Sendall(chr(P.CLEAR)+chr(P.LT_BLUE)+"tERMINAL ID: "+chr(P.WHITE)+conn.TermString.decode("utf-8")+"\r")
    time.sleep(0.5)
    conn.Sendall(chr(P.LT_BLUE)+"tURBO56k VERSION: "+chr(P.WHITE)+str(conn.T56KVer)+"\r")
    time.sleep(0.5)
    conn.Sendall(chr(P.LT_BLUE)+"cHECKING TERMINAL FEATURES:\r")
    time.sleep(1)
    for ix, x in enumerate(conn.TermFt):
        if x != b'\x80':
            if (ix % 16) == 0:
                conn.Sendall(chr(P.WHITE)+"\r$"+hex(ix)[2:3]+"X: ")
            if ix in TT.T56K_CMD:
                #conn.Sendall(chr(P.GREY3)+P.toPETSCII(TT.T56K_CMD[ix])+chr(P.LT_GREEN)+chr(P.CHECKMARK)+"\r")
                conn.Sendall(chr(P.LT_GREEN)+chr(P.CHECKMARK))
                #if ix == 3:
                #    conn.Sendall(chr(P.GREY3)+"pcm AUDIO SAMPLERATE "+chr(P.YELLOW)+str(conn.samplerate)+"\r")
            else:
                #conn.Sendall(chr(P.GREY2)+"uNKNOWN COMMAND"+chr(P.LT_GREEN)+chr(P.CHECKMARK)+"\r")
                conn.Sendall(chr(P.YELLOW)+"?")
        elif ix in TT.T56K_CMD:
            #conn.Sendall(chr(P.LT_BLUE)+P.toPETSCII(TT.T56K_CMD[ix])+chr(P.RED)+"X\r")
            conn.Sendall(chr(P.RED)+"X")
        #time.sleep(0.1)
    conn.Sendall('\r')
    if conn.TermFt[3] != b'\x80':
        conn.Sendall(chr(P.GREY3)+"pcm AUDIO SAMPLERATE "+chr(P.YELLOW)+str(conn.samplerate)+"hZ\r")
    time.sleep(2)

#######################################################
##					  BBS Loop						 ##
#######################################################

def BBSLoop(conn:Connection):
    global bbs_instance

    try:
        # Sync
        conn.Sendall(chr(0)*2)
        # Reset
        conn.Sendall(TT.reset_Turbo56K())
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
        conn.Sendall(chr(P.CYAN) + '\r'+P.toPETSCII(bbs_instance.WMess)+'\r')
        conn.Sendall(P.toPETSCII('RetroBBS v%.2f\r'%bbs_instance.version))
        conn.Sendall(P.toPETSCII('running under:\r'+bbs_instance.OSText+'\r'))
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
        _LOG('ID:', datos,id=conn.id,v=4)
        if datos == b"RT":
            datos = conn.Receive(20)
            _LOG('Terminal: ['+ bcolors.OKGREEN + str(datos) + bcolors.ENDC + ']',id=conn.id,v=4)
            dato1 = conn.Receive(1)
            dato2 = conn.Receive(1)
            _LOG('TURBO56K version: '+ bcolors.OKGREEN + str(ord(dato1)) + '.' + str(ord(dato2)) + bcolors.ENDC,id=conn.id,v=4) 

            t56kver = ord(dato1)+((ord(dato2))/10)

            #Increment visit counters
            bbs_instance.visits += 1            #Session counter
            bbs_instance.database.newVisit()    #Total counter

            if t56kver > 0.4:
                conn.TermString = datos
                conn.T56KVer = t56kver
                GetTerminalFeatures(conn)
                SendTerminalFeatures(conn)
                if conn.TermFt[1]!=b'\x80' and conn.TermFt[2]!=b'\x80' and conn.TermFt[51]!=b'\x80':
                    _LOG('Sending intro pic',id=conn.id,v=4)
                    bg = FT.SendBitmap(conn,'bbsfiles/splash.art',12,False)
                    _LOG('Spliting Screen',id=conn.id,v=4)
                    conn.Sendall(TT.split_Screen(12,False,ord(bg),0))
                time.sleep(1)
                Done = False
                while not Done:
                    conn.Sendall(chr(P.CLEAR)+chr(P.WHITE)+"(l)OGIN or (g)UEST?")
                    time.sleep(1)
                    t = conn.ReceiveKey(b'LGS')
                    if not conn.connected:
                        return()
                    if t == b'L':
                        SignIn(conn)
                        if conn.username != '_guest_':
                            conn.Sendall(chr(0)*2+TT.split_Screen(0,False,0,0))
                            SlideShow(conn,'','bbsfiles/intro/')
                            conn.Sendall(TT.enable_CRSR())
                            Done = True
                    elif t == b'G':
                        conn.Sendall(chr(0)*2+TT.split_Screen(0,False,0,0)+chr(P.CLEAR))
                        SlideShow(conn,'','bbsfiles/intro/')
                        conn.Sendall(TT.enable_CRSR())
                        Done = True
                    else:
                        conn.Sendall(chr(0)*2+TT.split_Screen(0,False,0,0))
                        Done = True
            else:
                _LOG('Old terminal detected - Terminating',id=conn.id)
                conn.Sendall('pLEASE USE retroterm V0.13 OR POSTERIOR\r fOR THE LATEST VERSION VISIT\r www.pastbytes.com/retroterm\r'+chr(P.WHITE))
                conn.connected = False


            # Display the main menu

            conn.menu = 0		# Starting at the main menu
            conn.MenuDefs = GetKeybindings(conn,0)
            SendMenu(conn)

            while conn.connected == True and _run == True:
                data = conn.Receive(1)
                _LOG('received "'+bcolors.OKBLUE+str(data)+bcolors.ENDC+'"',id=conn.id,v=4)
                if data != b'' and conn.connected == True:
                    if data in conn.MenuDefs:
                        if conn.userclass >= conn.MenuDefs[data][3]:
                            prompt = conn.MenuDefs[data][2] if len(conn.MenuDefs[data][2])<20 else conn.MenuDefs[data][2][:17]+'...'
                            conn.Sendall(P.toPETSCII(prompt))	#Prompt
                            time.sleep(1)
                            wait = conn.MenuDefs[data][4]
                            Function = conn.MenuDefs[data][0]
                            res = Function(*conn.MenuDefs[data][1])
                            if isinstance(res,dict):
                                conn.MenuDefs = res
                            elif data!=b'\r':
                                if wait:
                                    WaitRETURN(conn,60.0*5)
                                    conn.Sendall(TT.enable_CRSR())	#Enable cursor blink just in case
                                Function = conn.MenuDefs[b'\r'][0]
                                res = Function(*conn.MenuDefs[b'\r'][1])
                                if isinstance(res,dict):
                                    conn.MenuDefs = res
                        else:
                            conn.Sendall('yOU CANT ACCESS THIS AREA')
                            time.sleep(2)
                            SendMenu(conn)
                    else:
                        continue
                else:
                    _LOG('no more data from', conn.addr, id=conn.id)
                    break

        else:
            conn.Sendall(chr(P.CYAN) + '\r\ntHIS bbs REQUIRES A TERMINAL\r\nCOMPATIBLE WITH turbo56k 0.3 OR NEWER.\r\n')
            conn.Sendall('fOR THE LATEST VERSION VISIT\r www.pastbytes.com/retroterm\r' + chr(P.LT_BLUE) + 'dISCONNECTED...')
            time.sleep(1)
            _LOG('Not a compatible terminal, disconnecting...',id=conn.id,v=2)
            # Clean up the connection
            conn.socket.close()
    finally:
        # Clean up the connection
        conn.socket.close()
        _LOG('Disconnected',id=conn.id,v=3)


## Connection check thread ##
def ConnTask():
    global conlist
    global bbs_instance

    while _run:
        time.sleep(1) # check once per second
        for t in range(1,6):
            if t in conlist:				#Find closed connections
                if not conlist[t][0].is_alive():
                    conlist[t][1].Close()
                    if conlist[t][1].userclass != 0:
                        bbs_instance.database.logoff(conlist[t][1].userid,conlist[t][1].outbytes,conlist[t][1].inbytes)
                    del conlist[t][1]
                    try:
                        conlist[t][0].join()
                    except:
                        pass
                    conlist.pop(t)
                    _LOG('Slot freed - Awaiting a connection',v=3)

#######################################################
##              		MAIN                         ##
#######################################################

# Initialize variables

parser = argparse.ArgumentParser(description='Python BBS server for Turbo56K enabled terminals')
parser.add_argument('-v', dest='verb', type=int, choices=range(1,5),nargs='?', const=1, default=1, help='Verbosity level (1-4): 1 = Errors only | 4 = All logs')


if AA.wavs != True:
    _LOG('Audio fileformats not available!', v=2)

if AA.meta != True:
    _LOG('Audio Metadata not available!', v=2)

args = parser.parse_args()

set_verbosity(args.verb)

bbs_instance = BBS('','',0)
bbs_instance.version = _version
#Check OS type
bbs_instance.OSText = platform.system()
if 'Linux' in bbs_instance.OSText:
    #Get distro
    mi = subprocess.check_output(["hostnamectl", "status"], universal_newlines=True)
    m = re.search('Operating System: (.+?)\n', mi)
    bbs_instance.OSText = m.group(1)
else:
    #Add OS version
    bbs_instance.OSText = bbs_instance.OSText + platform.release()

print('\n\nRetroBBS v%.2f (c)2021-2022\nby Pablo Roldán(durandal) and\nJorge Castillo(Pastbytes)\n\n'%_version)

# Parse plugins
p_mods = [importlib.import_module(name) for finder, name, ispkg in iter_namespace(plugins)]
for a in p_mods:
    if 'setup' in dir(a):
        fname,parms = a.setup()
        PlugDict[fname] = [a.plugFunction,parms] 
        _LOG('Loaded plugin: '+fname,v=4)


# Read config file
ConfigRead()

# Register CTRL-C handler
signal.signal(signal.SIGINT, signal_handler)

# Create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Bind the socket to the port
server_address = (bbs_instance.ip, bbs_instance.port)
_LOG('Initializing server on %s port %s' % server_address,v=3)
sock.bind(server_address)

# Listen for up to 5 incoming connections
sock.listen(5)

#List of current active connections
conlist = {}

conthread = threading.Thread(target = ConnTask, args = ())
conthread.start()

while True:
    # Wait for a connection
    _LOG('Awaiting a connection',v=3)
    c, c_addr = sock.accept()

    newid = 1
    for r in range(1,6):			#Find free id
        if r not in conlist:
            newid = r
            break
    newconn = Connection(c,c_addr,bbs_instance,newid)
    
    conlist[newid] = [threading.Thread(target = BBSLoop, args=(newconn,)),newconn]
    conlist[newid][0].start()
