#################################################################################################
# RetroBBS 0.50 (compatible with TURBO56K 0.6 and retroterm 0.14                              	#
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
from os.path import splitext, getmtime, exists
import datetime
import signal
import string
import configparser #INI file parser
import threading
from html import unescape
import random

from common import extensions as EX
from common import turbo56k as TT
from common.classes import BBS
from common.connection import Connection
from common.bbsdebug import _LOG, bcolors, set_verbosity
from common.helpers import MenuBack, valid_keys, formatX, More, SetPage, crop, format_bytes, date_strings
from common.style import RenderMenuTitle, KeyLabel
from common import audio as AA
from common import messaging as MM
from common import video as VV

#File transfer functions
from common import filetools as FT

#Image filename extensions
from common.imgcvt import im_extensions

##################################
# BBS Version
_version = 0.60
##################################

# Threads running flag
_run = True

# Timeout default value (secs)
_tout = 60.0*5

# Configuration file
config_file = 'config.ini'

###########################
# Reads Configuration file
###########################
def ConfigRead():
    global bbs_instance

    #Iterate Section Entries
    def EIter(cfg, key, sentry):
        PlugDict = bbs_instance.plugins
        nchar = 0   # LABEL (no associated key) entries use chars 0x00 to 0x0c
        for e in range(0,sentry['entries']):
            try:
                tentry = cfg[key]['entry'+str(e+1)+'title']	# Entry Title
            except:
                raise Exception(f'Configuration file error:\n entry{str(e+1)}title not found')
            if sentry['columns'] < 2:
                dentry = cfg.get(key,'entry'+str(e+1)+'desc', fallback = '')
                if dentry != '':
                    tentry = (tentry,dentry)
            efunc = cfg.get(key,'entry'+str(e+1)+'func', fallback ='LABEL')		# Entry Internal function
            if efunc != 'LABEL':
                try:
                    ekey = cfg[key]['entry'+str(e+1)+'key']		# Entry Key binding
                except:
                    raise Exception('Configuration file error:\n Menu entry missing associated key')
            else:
                ekey = chr(nchar)
                nchar += 1
                if nchar == '\r':
                    raise Exception('Configuration file - Too many LABEL entries')
            if ekey not in sentry['entrydefs']:
                sentry['entrydefs'][ekey] = {}
            emode = cfg.get(key,'entry'+str(e+1)+'mode', fallback ='')		    # Entry connection mode
            level = cfg.getint(key,'entry'+str(e+1)+'level', fallback = 0)
            # Parse parameters
            parms = []
            if efunc == 'IMAGEGALLERY':		# Show image file list
                p = cfg.get(key, 'entry'+str(e+1)+'path', fallback='images/')
                parms= [tentry,'','Displaying image list',p,tuple(['.GIF','.JPG','.PNG']+im_extensions),FT.SendBitmap,cfg.getboolean(key,'entry'+str(e+1)+'save',fallback=False)]
            elif efunc == 'SWITCHMENU':		# Switch menu
                parms = [cfg[key].getint('entry'+str(e+1)+'id')]
            elif efunc == 'FILES':			# Show file list
                te = cfg.get(key,'entry'+str(e+1)+'ext', fallback='')
                if te != '':
                    exts = tuple(te.split(','))
                else:
                    exts = ()
                p = cfg.get(key, 'entry'+str(e+1)+'path', fallback='programs/')
                parms = [tentry,'Displaying file list',p,exts,FT.SendFile,cfg.getboolean(key,'entry'+str(e+1)+'save',fallback=False),cfg.getboolean(key,'entry'+str(e+1)+'subdirs',fallback=False)]
            elif efunc == 'AUDIOLIBRARY':	# Show audio file list
                p = cfg.get(key, 'entry'+str(e+1)+'path', fallback='sound/')
                parms = [tentry,'','Displaying audio list',p]
            elif efunc == 'PCMPLAY':		# Play PCM audio
                parms = [cfg.get(key, 'entry'+str(e+1)+'path', fallback=bbs_instance.Paths['bbsfiles']+'bbsintroaudio-eng11K8b.wav'),None]
            elif efunc == 'GRABFRAME':		# Grab video frame
                parms = [cfg.get(key, 'entry'+str(e+1)+'path', fallback=''),None]
            elif efunc == 'SIDPLAY' or efunc == 'CHIPPLAY':        #Play SID/MUS
                parms = [cfg.get(key, 'entry'+str(e+1)+'path', fallback = ''),cfg.getint(key,'entry'+str(e+1)+'playt',fallback=None),False,cfg.getint(key,'entry'+str(e+1)+'subt',fallback=None)]
            elif efunc == 'SLIDESHOW':		# Iterate through and show all supported files in a directory
                parms = [tentry,cfg.get(key, 'entry'+str(e+1)+'path', fallback=bbs_instance.Paths['bbsfiles']+'pictures'),1,True,cfg.getboolean(key,'entry'+str(e+1)+'shuffle', fallback=False)]
            elif efunc == 'SENDFILE':
                parms = [cfg.get(key, 'entry'+str(e+1)+'path', fallback=''),cfg.getboolean(key,'entry'+str(e+1)+'dialog', fallback=False),cfg.getboolean(key,'entry'+str(e+1)+'save', fallback=False)]
            elif efunc == 'SENDRAW':
                parms = [cfg.get(key, 'entry'+str(e+1)+'path', fallback='')]
            elif efunc == 'INBOX':
                parms = [0]
            elif efunc == 'BOARD':
                parms = [cfg.getint(key,'entry'+str(e+1)+'id', fallback = 1)]
            # functions without parameters
            elif efunc in ['BACK','EXIT','USEREDIT','USERLIST','MESSAGE','LABEL','STATS']:
                parms = []
            elif efunc in PlugDict:			# Plugin function
                parms = []
                for p in PlugDict[efunc][1]:	# Iterate parameters
                    ep = cfg.get(key, 'entry'+str(e+1)+p[0], fallback=p[1])
                    if isinstance(p[1],tuple) == True and isinstance(ep,tuple) == False:
                        ep = tuple([int(e) if e.isdigit() else 0 for e in ep.split(',')])
                    parms.append(ep)
            # Parameter tuple need to be added to one (conn,) on each connection instance when calling func
            # also needs conn.MenuParameters added to this
            # finaltuple = (conn,)+ _parms_
            if efunc in func_dic:
                for mode in emode.split(','):
                    # [function_call, parameters, title, user_level, wait]
                    sentry['entrydefs'][ekey][mode] = [func_dic[efunc],tuple(parms),tentry,level,False]
            elif efunc in PlugDict:
                for mode in emode.split(','):
                    sentry['entrydefs'][ekey][mode] = [PlugDict[efunc][0],tuple(parms),tentry,level,False]
            else:
                raise Exception('Configuration file - Unknown function at: '+'entry'+str(e+1)+'func')
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
    func_dic = {'IMAGEGALLERY': Gallery,
                'AUDIOLIBRARY': AA.AudioList,
                'FILES': FT.FileList,
                'SENDRAW': FT.SendRAWFile,
                'SWITCHMENU': SwitchMenu,
                'SLIDESHOW': SlideShow,
                'SIDPLAY': AA.SIDStream,
                'CHIPPLAY': AA.CHIPStream,
                'PCMPLAY': AA.PlayAudio,
                'TEXT': FT.SendText,
                'SHOWPIC': FT.SendBitmap,
                'EXIT': LogOff,
                'BACK': MenuBack,
                'USEREDIT': EditUser,
                'USERLIST': UserList,
                'BOARD': MM.inbox,
                'INBOX': MM.inbox,
                'GRABFRAME': VV.Grabframe,
                'STATS': Stats,
                'SENDFILE': FT.SendFile,
                'LABEL': None}
    config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
    config.read(config_file)
    bbs_instance.cfgmts = getmtime(config_file) # Set latest configuration file modify datestamp

    # MAIN variables
    bbs_instance.name = config['MAIN']['bbsname']
    bbs_instance.ip = config['MAIN']['ip']
    bbs_instance.port = config['MAIN'].getint('port')
    bbs_instance.lines = config['MAIN'].getint('lines', fallback= 5)
    bbs_instance.lang = config['MAIN']['language']
    bbs_instance.WMess = config['MAIN'].get('welcome', fallback='Welcome!')
    bbs_instance.GBMess = config['MAIN'].get('goodbye', fallback='Goodbye!')
    bbs_instance.BSYMess = config['MAIN'].get('busy', fallback='BUSY')
    bbs_instance.dateformat = config['MAIN'].getint('dateformat', fallback=1)
    bbs_instance.Template = config['MAIN'].get('template', fallback='default')+'/'

    # Get any paths
    try:
        bbs_instance.Paths.update(dict(config.items('PATHS')))
    except:
        pass
    # Get any message boards options
    try:
        bbs_instance.BoardOptions = dict(config.items('BOARDS'))
    except:
        bbs_instance.BoardOptions = {}
    # Get any plugin config options
    try:
        bbs_instance.PlugOptions = dict(config.items('PLUGINS'))
    except:
        bbs_instance.PlugOptions = {}

    # Parse Menues
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
        _bbs_menues[m] = {'title':tmenu, 'sections':scount, 'prompt':prompt, 'type':0, 'entries':[{}]*scount}
        _bbs_menues[m] = MIter(config,tkey,_bbs_menues[m])
        _bbs_menues[m]['entries'][0]['entrydefs']['\r']={'':[SendMenu,(),'',0,False]}
    bbs_instance.MenuList = _bbs_menues

################################
#Handles CTRL-C
################################
def signal_handler(sig, frame):
    global _run
    global conlist
    global conthread
    global bbs_instance

    _LOG('Ctrl+C! Bye!', v=3)
    _run = False

    for t in range(1,bbs_instance.lines+1):
        if t in conlist:				#Find closed connections
            conlist[t][1].Close()
            conlist[t][0].join()
    conthread.join()

    try:
        sock.shutdown(socket.SHUT_RDWR)
        sock.close()
    except Exception as e:
        _LOG('Socket shutdown failed: '+e, v=1)
        pass
    del bbs_instance
    sys.exit(0)

#########################################################################################
# Show a menu with a list of files, call fhandler on user selection
#########################################################################################
def Gallery(conn:Connection,title,speech,logtext,path,ffilter,fhandler,transfer=False):
    if conn.menu != -1:
        conn.MenuStack.append([conn.MenuDefs,conn.menu])
        conn.menu = -1
    # Init Menu parameter dictionary if needed
    if conn.MenuParameters == {}:
        conn.MenuParameters['current'] = 0

    st = conn.style

    # transfer &= conn.QueryFeature(TT.FILETR) < 0x80

    scwidth,scheight = conn.encoder.txt_geo

    max_e = min(((scheight-5)*2),40)      # Number of entries per page (hardcoded to 40 maximum, the number of available keys)
    e_width = (scwidth//2)-4    # Max characters per entry
    separator = '  ' if scwidth % 2 == 0 else '   '

    # Start with barebones MenuDic
    MenuDic = { 
                conn.encoder.decode(conn.encoder.back): (MenuBack,(conn,),"Previous Menu",0,False),
                conn.encoder.nl: (Gallery,(conn,title,speech,logtext,path,ffilter,fhandler,transfer),title,0,False)
              }	
    _LOG(logtext,id=conn.id, v=4)
    # Send speech message
    if conn.T56KVer > 0:
        conn.Sendall(TT.to_Speech() + speech)
    # Select screen output
    conn.SendTML(f'<PAUSE n=1><SETOUTPUT><NUL n=2><CURSOR><TEXT border={conn.style.BoColor} background={conn.style.BgColor}>')
    RenderMenuTitle(conn,title)
    # Send menu options
    files = []	# all files
    programs = []	# filtered list
    # Read all files from 'path'
    for entries in walk(path):
        files.extend(entries[2])
        break
    # Filter out all files not matching 'filter'
    if len(ffilter) > 0:
        for f in files:
            if splitext(f)[1].upper() in ffilter:
                programs.append(f)
    else:
        programs = files
    programs.sort()	#Sort list
    pages = int((len(programs)-1) / max_e) + 1
    count = len(programs)
    start = conn.MenuParameters['current'] * max_e
    end = start + (max_e-1)
    if end >= count:
        end = count - 1
    # Add pagination keybindings to MenuDic
    if pages > 1:
        if conn.MenuParameters['current'] == 0:
            page = pages-1
        else:
            page = conn.MenuParameters['current']-1
        MenuDic['<'] = (SetPage,(conn,page),'Previous Page',0,False)
        if conn.MenuParameters['current'] == pages-1:
            page = 0
        else:
            page = conn.MenuParameters['current']+1
        MenuDic['>'] = (SetPage,(conn,page),'Next Page',0,False)
    if fhandler == FT.SendFile:
        keywait = False
    else:
        keywait = True
    for x in range(start, end + 1):
        if len(ffilter) == 0:
            if len(programs[x]) > e_width:
                fn = splitext(programs[x])
                label = fn[0][:e_width-len(fn[1])]+fn[1]
            else:
                label = programs[x]
        else:
            label = splitext(programs[x])[0]
        KeyLabel(conn, valid_keys[x-start], (label+' '*e_width)[:e_width]+(''if x%2 else separator), (x % 4)<2)
        # Add keybinding to MenuDic
        if fhandler == FT.SendFile:
            parameters = (conn,path+programs[x],True,transfer,)
        else:
            parameters = (conn,path+programs[x],True,transfer,)
        MenuDic[valid_keys[x-start]] = (fhandler,parameters,valid_keys[x-start],0,keywait)
    conn.SendTML(conn.templates.GetTemplate('main/navbar',**{'barline':scheight-2,'crsr':'','pages':'&lt; / &gt;','keys':[]}))


    conn.SendTML(f'<AT x=0 y={scheight-1}><WHITE> [{conn.MenuParameters["current"]+1}/{pages}]<CYAN> Selection:<WHITE> ')
    if conn.T56KVer > 0:
        conn.Sendall(TT.to_Speech() + 'seleksioneunaopsion,')
        # Select screen output
        conn.Sendall(TT.to_Screen())
    return MenuDic


######################################
# Render Menu from MenuList structure
######################################
def SendMenu(conn:Connection):
    if conn.menu < 0:
        return()
    # Get screen dimensions
    scwidth = conn.encoder.txt_geo[0]
    scheight = conn.encoder.txt_geo[1]
    conn.SendTML(f'<SETOUTPUT><TEXT border={conn.style.BoColor} background={conn.style.BgColor}><CLR><CURSOR>')
    tmenu = conn.bbs.MenuList[conn.menu]	#Change to simply tmenu = conn.MenuDefs
    _LOG("Sending menu: "+tmenu['title'],id=conn.id,v=4)
    RenderMenuTitle(conn,tmenu['title'])
    conn.SendTML('<BR>')
    for scount, s in enumerate(tmenu['entries']):
        #Sections
        parms = {'section': s, 'scount':scount, 'formatX':formatX, 'crop':crop, 'unescape':unescape}
        if s['columns'] == 1:
            conn.SendTML(conn.templates.GetTemplate('main/menusection1col',**parms))
        elif s['columns'] == 2:
            conn.SendTML(conn.templates.GetTemplate('main/menusection2col',**parms))
    conn.SendTML(f'<AT x=0 y={scheight-1}><WHITE> {tmenu["prompt"]} ')

#####################################################################
# Sequentially display all matching files inside a directory
#####################################################################
def SlideShow(conn:Connection,title,path,delay = 1, waitkey = True, shuffle = False):
    # Sends menu options
    files = []	#all files
    slides = []	#filtered list
    #Read all the files from 'path'
    for entries in walk(path):
        files.extend(entries[2])
        break

    pics_e = tuple(['.GIF','.JPG','PNG']+im_extensions)
    text_e = ('.TXT','.SEQ')
    bin_e = ('.BIN','.raw')
    pet_e = ('.C','.PET')
    aud_e = ('.MP3','.WAV')
    chip_e = ('.SID','.MUS','.YM','.VTX','.VGZ')

    #Keeps only the files with matching extension 
    for f in files:
        if splitext(f)[1].upper() in pics_e + text_e + bin_e + pet_e + aud_e + chip_e + ('.TML',):
            slides.append(f)

    if shuffle:
        random.shuffle(slides)
    else:
        slides.sort()	#Sort list

    turbo = conn.T56KVer > 0

    #Iterate through files
    for p in slides:
        w = 0
        conn.SendTML('<CURSOR><CLR>')
        _LOG('SlideShow - Showing: '+p,id=conn.id,v=4)
        ext = splitext(p)[1].upper()
        if ext in pics_e and (conn.QueryFeature(TT.PRADDR) < 0x80):
            FT.SendBitmap(conn, path+p)
        elif ext in bin_e and turbo:
            with open(path+p,'rb') as slide:
                binary = slide.read()
                conn.Sendallbin(binary)
        elif ext in text_e:
            w = FT.SendText(conn,path+p,title)
        elif ext == pet_e[0] and turbo:
            w = FT.SendCPetscii(conn,path+p,(0 if waitkey else delay))
        elif ext == pet_e[1] and turbo:
            w = FT.SendPETPetscii(conn,path+p)
        elif (ext in aud_e) and (conn.QueryFeature(TT.STREAM) < 0x80):
            if AA.PlayAudio(conn,path+p,None):
                break   # Abort the whole slideshow if an audio is aborted
            w = 1
        elif (ext in chip_e) and (conn.QueryFeature(TT.SIDSTREAM) < 0x80):
            if AA.CHIPStream(conn,path+p,None,False):
                break   # Abort the whole slideshow if a chiptune is aborted
            w = 1
        elif ext == '.TML':     #TML script
            with open(path+p,'r') as slide:
                tml = slide.read()
                conn.SendTML(tml)
            w = 1
        else:   # Dont wait for RETURN if file is not supported
            w = 1
        # Wait for the user to press RETURN
        if waitkey == True and w == 0:
            WaitRETURN(conn,60.0*5)
        else:
            time.sleep(delay)
        conn.SendTML(f'<TEXT page=0 border={conn.style.BoColor} backgroud={conn.style.BgColor}>')
    conn.SendTML('<CURSOR>')

################################################
# Wait for user to press RETURN
################################################
def WaitRETURN(conn:Connection,timeout = 60.0):
    _LOG('Waiting for the user to press RETURN...',id=conn.id,v=4)
    tecla = b''
    conn.socket.settimeout(timeout)
    while conn.connected == True and tecla != conn.encoder.nl.encode('latin1'):
        tecla = conn.Receive(1)
        if tecla == b'':
            conn.connected = False
    conn.socket.settimeout(_tout)
    if conn.connected == False:
        try:
            conn.socket.sendall(b'TIMEOUT - DISCONNECTED ')
        except socket.error:
            pass
    _LOG(bcolors.OKBLUE+str(tecla)+bcolors.ENDC,id=conn.id,v=4)

##############################################
# Wait 1 minute for the user to press any key
##############################################
def WaitKey(conn:Connection):
    _LOG('Waiting for the user to press a key...',id=conn.id,v=4)
    tecla = b''
    conn.socket.settimeout(60.0)
    tecla = conn.Receive(1)
    if tecla == b'':
        conn.connected = False
        try:
            conn.socket.sendall(b'TIMEOUT - DISCONNECTED ')
        except socket.error:
            pass
    conn.socket.settimeout(_tout)

################################################
# Logoff
################################################
def LogOff(conn:Connection, confirmation=True):

    lan = {'en':['Are you sure (Y/N)? ','yn','Disconnected'],'es':['Esta seguro (S/N)? ','sn','Desconectado']}
    l_str = lan.get(conn.bbs.lang,lan['en'])

    if confirmation == True:
        for k in conn.MenuDefs:
            if LogOff in conn.MenuDefs[k]:
                lolen = len(crop(conn.MenuDefs[k][2], conn.encoder.txt_geo[0]//2,conn.encoder.ellipsis))    # Logoff menu entry title len
                
                break
        lolen += len(conn.bbs.MenuList[conn.menu]['prompt']) + 1 # Add menu prompt len and the trailing space
        conn.SendTML(f'<DEL n={lolen}><LTGREEN>{l_str[0]}<WHITE><PAUSE n=1>')
        data = ''
        data = conn.ReceiveKey(l_str[1])
        if data == l_str[1][0]:
            _LOG('Disconnecting...\r',id=conn.id,v=3)
            conn.Sendall(data)
            conn.SendTML(f'<PAUSE n=1><WHITE><BR><BR>{"".join(formatX(conn.bbs.GBMess,conn.encoder.txt_geo[0]))}<BR><PAUSE n=1><LTBLUE><BR>{l_str[2]}<BR><WHITE><PAUSE n=1>')
            # Execute session logoff TML
            if exists(conn.bbs.Paths['bbsfiles']+'logoff.tml'):
                with open(conn.bbs.Paths['bbsfiles']+'logoff.tml','r') as slide:
                    tml = slide.read()
                    conn.SendTML(tml)
                    time.sleep(1)
            conn.connected = False	#break
            return True
        else:
            return False
    else:
        conn.connected = False
        return True

#####################################
# Switch menu
#####################################
def SwitchMenu(conn:Connection, id):
    if id-1 != conn.menu:
        if len(conn.MenuDefs) != 0:
            conn.MenuStack.append([conn.MenuDefs,conn.menu])
        conn.menu = id-1
        conn.MenuDefs = GetKeybindings(conn,id-1)

########################################
# Generate menu keybindings
########################################
def GetKeybindings(conn:Connection,id):

    menu = conn.bbs.MenuList[id]
    kb = {}
    for cat in menu['entries']:
        for e in cat['entrydefs']:
            entry = cat['entrydefs'][e].get(conn.mode, cat['entrydefs'][e].get('',None))
            if entry != None:
                if e == '\r':
                    e = conn.encoder.nl
                if e == '_':
                    e = conn.encoder.decode(conn.encoder.back)
                kb[e] = entry.copy()
                if isinstance(kb[e][2],tuple):
                    kb[e][2]=kb[e][2][0]
                kb[e][1] = (conn,)+kb[e][1]
    return kb

############################
# Show BBS/User statistics
############################
def Stats(conn:Connection):
    _LOG("Displaying stats",v=4,id=conn.id)
    conn.SendTML(f'<SPLIT row=0 multi=False bgtop={conn.encoder.colors.get("BLACK",0)} bgtop={conn.encoder.colors.get("BLACK",0)} mode={conn.mode}>') # Cancel any split screen/window
    RenderMenuTitle(conn,"BBS Stats")
    scwidth,scheight = conn.encoder.txt_geo
    conn.SendTML(f'<WINDOW top=3 bottom={scheight-1}>')
    bstats = conn.bbs.database.bbsStats()
    if bstats != None:
        utime = bstats.get('uptime',0)
        visits = bstats.get('visits',1)
        latest = bstats.get('latest',conn.username)
    else:
        utime = 0
        visits = 1
        latest = [conn.username]
    tt = datetime.timedelta(seconds= round(utime + (time.time() - conn.bbs.runtime)))
    st = datetime.timedelta(seconds=round(time.time()-conn.bbs.runtime))
    text = ['<BR>']
    if len(f'{st}') > (scwidth-21):
        text += ['<CYAN>BBS Session uptime:<BR>',
               f'<WHITE>  {st}<BR>']
    else:
        text += [f'<CYAN>BBS Session uptime: <WHITE>{st}<BR>']
    if len(f'{tt}') > (scwidth-19):
        text += ['<CYAN>BBS Total uptime:<BR>',
                 f'<WHITE>  {tt}<BR>']
    else:
        text += [f'<CYAN>BBS Total uptime: <WHITE>{tt}<BR>']
    text += [f'<CYAN>Total visits to the BBS: <WHITE>{visits}<BR>',
            f'<CYAN>Registered users: <WHITE>{len(conn.bbs.database.getUsers())}<BR>',
            '<BR>',
            '<CYAN>Last 10 visitors:<BR>',
            '<BR>']
    for i,l in enumerate(latest):
        text += [f'<YELLOW><RVSON><L-NARROW>{i}<R-NARROW><RVSOFF><WHITE>{l}<BR>']
    text += [f'<YELLOW><HLINE n={conn.encoder.txt_geo[0]}>',
             f'<LTGREEN>Your Stats:<BR>',
             f'<BR>']
    st = datetime.timedelta(seconds= round(time.time() - conn.stime))
    if len(f'{st}') > (scwidth-20) :
        text += ['<CYAN>This session time:<BR>',
                f'<WHITE>{st}<BR>']
    else:
        text += [f'<CYAN>This session time: <WHITE>{st}<BR>']
    ud = format_bytes(conn.inbytes)
    dd = format_bytes(conn.outbytes)
    if (len(ud) + len(dd)) > (scwidth - 27):
        text += ['<CYAN>Session Upload/Download:<BR>',
                 f'<WHITE>  {ud}<YELLOW>/<WHITE>{dd}<BR>']
    else:
        text += [f'<CYAN>Session Upload/Download: <WHITE>{ud}<YELLOW>/<WHITE>{dd}<BR>']
    if conn.userclass > 0:
        udata = conn.bbs.database.chkUser(conn.username)
        tt = datetime.timedelta(seconds=round(udata.get('totaltime',0) + (time.time() - conn.stime)))
        tup  = format_bytes(udata.get('upbytes',0) + conn.inbytes)
        tdwn = format_bytes(udata.get('downbytes',0) + conn.outbytes)
        if len(f'{tt}') > (scwidth - 21):
            text += ['<CYAN>Total session time:<BR>',
                     f'<WHITE>  {tt}<BR>']
        else:
            text += [f'<CYAN>Total session time: <WHITE>{tt}<BR>']
        if (len(tup) + len(tdwn)) > (scwidth - 25):
            text += ['<CYAN>Total Upload/Download:<BR>',
                     f'<WHITE>  {tup}<YELLOW>/<WHITE>{tdwn}<BR>']
        else:
            text += [f'<CYAN>Total Upload/Download: <WHITE>{tup}<YELLOW>/<WHITE>{tdwn}<BR>']
    More(conn,text,scheight-3)
    conn.SendTML(f'<WINDOW top=0 bottom={scheight-1}>')

#############################
# SignIn/SignUp
#############################
def SignIn(conn:Connection):
    _dec = conn.encoder.decode
    st = conn.style
    keys = string.ascii_letters + string.digits + ' +-_,.$%&'
    conn.SendTML('<CYAN>Username:')
    Done = False
    while not Done:
        name = conn.ReceiveStr(keys, 16, False)
        if not conn.connected:
            return
        while len(name) > 0 and len(name) < 6:
            conn.SendTML('<BR>Username must be 6 to 16 characters<BR>long, try again:')
            name = conn.ReceiveStr(keys, 16, False)
            if not conn.connected:
                return
        if len(name) > 0 and _dec(name) != '_guest_':
            uentry = conn.bbs.database.chkUser(_dec(name))
            if uentry != None:
                retries = 3
                if uentry['online'] == 1:
                    Done = True
                    conn.SendTML('<BR>User already logged in<BR>>')
                while (not Done) and (retries > 0):
                    conn.SendTML('<BR>Password:')
                    if conn.bbs.database.chkPW(uentry, _dec(conn.ReceiveStr(keys, 16, True))):
                        conn.SendTML(f'<INK c={conn.style.OKTxtColor}><BR>Login successful<BELL><CHECKMARK><PAUSE n=1>')
                        conn.username = _dec(name)
                        conn.userid = uentry.doc_id
                        conn.userclass = uentry['uclass']
                        conn.user_prefs.update(uentry.get('preferences',{}))
                        Done = True
                    else:
                        retries -= 1
                        conn.SendTML(f'<INK c={conn.style.BADTxtColor}><BR>Password incorrect<CYAN><PAUSE n=1>')
                if retries == 0:
                    Done = True
                if not conn.connected:
                    return
            else:
                conn.SendTML('<BR>User not found, register (Y/N)?')
                if conn.ReceiveKey('yn') == 'y':
                    datestr = date_strings[conn.bbs.dateformat][0]
                    dout = date_strings[conn.bbs.dateformat][1]
                    if not conn.connected:
                        return
                    if conn.QueryFeature(179) < 0x80:
                        lines = 13
                    else:
                        lines = conn.encoder.txt_geo[1]
                    FT.SendText(conn,conn.bbs.Paths['bbsfiles']+'terms/rules.txt','',lines)
                    conn.SendTML(f'<BR>Registering user {_dec(name)}<BR>Insert your password:')
                    pw = conn.ReceiveStr(keys, 16, True)
                    if not conn.connected:
                        return
                    while len(pw) < 6:
                        conn.SendTML('<BR>Password must be 6 to 16 characters long<BR>Insert your password:')
                        pw = conn.ReceiveStr(keys, 16, True)
                        if not conn.connected:
                            return
                    conn.SendTML('<BR>First name:')
                    fname = conn.ReceiveStr(keys, 16)
                    if not conn.connected:
                        return
                    conn.SendTML('<BR>Last name:')
                    lname = conn.ReceiveStr(keys, 16)
                    if not conn.connected:
                        return
                    conn.SendTML('<BR>Country:')
                    country = conn.ReceiveStr(keys, 16)
                    if not conn.connected:
                        return
                    bday = conn.ReceiveDate('<BR>bIRTHDATE: ',datetime.date(1900,1,1),datetime.date.today(),datetime.date(1970,1,1))
                    conn.username = _dec(name)
                    conn.userid = conn.bbs.database.newUser(_dec(name), _dec(pw), _dec(fname), _dec(lname), bday.strftime("%d/%m/%Y"), _dec(country))
                    _LOG('NEW USER: '+name,v=3)
                    conn.userclass = 1
                    conn.SendTML(f'<BR>Registration complete, welcome!<PAUSE n=1>'
                                f'<INK c={st.WRNTxtColor}><BR>Your user data:<BR><INK c={st.OKTxtColor}><HLINE n=14><BR>'
                                f'<INK c={st.HlColor}>User name: <INK c={st.TxtColor}>{_dec(name)}<BR>'
                                f'<INK c={st.HlColor}>Password: <INK c={st.TxtColor}>{"*"*len(pw)}<BR>'
                                f'<INK c={st.HlColor}>First name: <INK c={st.TxtColor}>{_dec(fname)}<BR>'
                                f'<INK c={st.HlColor}>Last name: <INK c={st.TxtColor}>{_dec(lname)}<BR>'
                                f'<INK c={st.HlColor}>Birthdate: <INK c={st.TxtColor}>{bday.strftime(datestr)}<BR>'
                                f'<INK c={st.HlColor}>Country: <INK c={st.TxtColor}>{_dec(country)}<BR><PAUSE n=1>'
                                f'<BR><YELLOW>Do you want to edit your data (Y/N)?')
                    if conn.ReceiveKey('yn') == 'y':
                        if not conn.connected:
                            return
                        # Edit user data
                        EditUser(conn)
                    Done = True
                else:
                    Done = True
                if not conn.connected:
                    return
        else:
            Done = True

######################################################################
# Edit logged in user
# This always runs outside the mainloop regardless of where is called
######################################################################
def EditUser(conn:Connection):
    u_items = [('a','Username','uname'),('b','First name','fname'),('c','Last name','lname'),('d','Birthdate','bday'),('e','Country','country')]

    _dec = conn.encoder.decode
    _LOG('Editing user '+conn.username, v=3)
    keys = string.ascii_letters + string.digits + ' +-_,.$%&'
    scwidth = conn.encoder.txt_geo[0]
    if conn.userid == 0:
        return
    conn.SendTML(f'<SPLIT row=0 multi=False bgtop={conn.encoder.colors.get("BLACK",0)} bgbottom={conn.encoder.colors.get("BLACK",0)} mode={conn.mode}>') # Cancel any split screen/window
    done = False
    line = 64 if 'PET' in conn.mode else 23
    back = conn.encoder.decode(conn.encoder.back)
    while (not done) and conn.connected:
        uentry = conn.bbs.database.chkUser(conn.username)
        prefs = uentry.get('preferences',{'datef':conn.bbs.dateformat})
        datestr = date_strings[prefs.get('datef',conn.bbs.dateformat)][0]
        dout = date_strings[prefs.get('datef',conn.bbs.dateformat)][1]
        RenderMenuTitle(conn,"Edit User Data")
        conn.SendTML('<CRSRD n=2>')
        for k,l,f in u_items:
            label = crop(l, scwidth-(6+len(uentry[f])),conn.encoder.ellipsis)
            KeyLabel(conn,k,f'{label}: {uentry[f]}',True)
            conn.SendTML('<BR>')
        KeyLabel(conn,'f','Change password',False)
        conn.SendTML('<BR>')
        KeyLabel(conn,'g','Preferences',False)
        conn.SendTML('<BR>')
        KeyLabel(conn,back,'Exit',True)
        conn.SendTML('<BR><BR>')
        if conn.QueryFeature(TT.LINE_FILL) < 0x80:
            conn.Sendall(TT.Fill_Line(13,line))
        else:
            conn.SendTML(f'<CRSRU><HLINE n={scwidth}>')
        conn.SendTML('Press option')
        k = conn.ReceiveKey('abcdefg' + back)
        if k == back:
            done = True
        elif k == 'a': # Username
            n = False
            conn.SendTML('<BR><CRSRU>')
            while not n:
                if conn.QueryFeature(TT.LINE_FILL) < 0x80:
                    conn.Sendall(TT.Fill_Line(14,32))
                else:
                    conn.SendTML(f'<AT x=0 y=14><SPC n={scwidth}><CRSRU>')
                conn.SendTML('<YELLOW>New username:')
                name = _dec(conn.ReceiveStr(keys, 16, False))
                if not conn.connected:
                    return
                if len(name) < 6:
                    conn.SendTML('<ORANGE><BR>Username must be 6 to 16 characters<BR>long, try again<BR><PAUSE n=2>')
                    if conn.QueryFeature(TT.LINE_FILL) < 0x80:
                        conn.SendTML('<LFILL row=15 code=32><LFILL row=16 code=32><CRSRU n=3>')
                    else:
                        conn.SendTML(f'<AT x=0 y=15><SPC n={scwidth*2}><CRSRU n=3>')
                elif name == '_guest_':
                    conn.SendTML('<ORANGE><BR>Invalid name<BR><try again<BR><PAUSE n=2>')
                    if conn.QueryFeature(TT.LINE_FILL) < 0x80:
                        conn.SendTML('<LFILL row=15 code=32><LFILL row=16 code=32><CRSRU n=3>')
                    else:
                        conn.SendTML(f'<AT x=0 y=15><SPC n={scwidth*2}><CRSRU n=3>')
                elif name != conn.username:
                    tentry = conn.bbs.database.chkUser(name)
                    if tentry != None:
                        conn.SendTML('<ORANGE><BR>Username already taken<BR>try again<BR><PAUSE n=2>')
                        if conn.QueryFeature(TT.LINE_FILL) < 0x80:
                            conn.SendTML('<LFILL row=15 code=32><LFILL row=16 code=32><CRSRU n=3>')
                        else:
                            conn.SendTML(f'<AT x=0 y=15><SPC n={scwidth*2}><CRSRU n=3>')
                    else:
                        conn.bbs.database.updateUser(uentry.doc_id,name,None,None,None,None,None,None)
                        conn.username = name
                        n = True
                else:   # Same old username
                    n = True
        elif k == 'b': # First name
            conn.SendTML('<BR><CRSRU>')
            if conn.QueryFeature(TT.LINE_FILL) < 0x80:
                conn.Sendall(TT.Fill_Line(14,32))
            else:
                conn.SendTML(f'<AT x=0 y=14><SPC n={scwidth}><CRSRU>')
            conn.SendTML('First name:')
            fname = _dec(conn.ReceiveStr(keys, 16))
            if not conn.connected:
                return
            conn.bbs.database.updateUser(uentry.doc_id,None,None,fname,None,None,None,None)
        elif k == 'c': # Last name
            conn.SendTML('<BR><CRSRU>')
            if conn.QueryFeature(TT.LINE_FILL) < 0x80:
                conn.Sendall(TT.Fill_Line(14,32))
            else:
                conn.SendTML(f'<AT x=0 y=14><SPC n={scwidth}><CRSRU>')
            conn.SendTML('Last name:')
            lname = _dec(conn.ReceiveStr(keys, 16))
            if not conn.connected:
                return
            conn.bbs.database.updateUser(uentry.doc_id,None,None,None,lname,None,None,None)
        elif k == 'd': # Birthdate
            conn.SendTML('<BR><CRSRU>')
            if conn.QueryFeature(TT.LINE_FILL) < 0x80:
                conn.Sendall(TT.Fill_Line(14,32))
            else:
                conn.SendTML(f'<AT x=0 y=14><SPC n={scwidth}><CRSRU>')
            bday = conn.ReceiveDate('<BR>Birthdate: ',datetime.date(1900,1,1),datetime.date.today(),datetime.date(1970,1,1))
            if not conn.connected:
                return
            conn.bbs.database.updateUser(uentry.doc_id,None,None,None,None,bday.strftime("%d/%m/%Y"),None,None)
        elif k == 'e': # Country
            conn.SendTML('<BR><CRSRU>')
            if conn.QueryFeature(TT.LINE_FILL) < 0x80:
                conn.Sendall(TT.Fill_Line(14,32))
            else:
                conn.SendTML(f'<AT x=0 y=14><SPC n={scwidth}><CRSRU>')
            conn.SendTML('Country:')
            country = _dec(conn.ReceiveStr(keys, 16))
            if not conn.connected:
                return
            conn.bbs.database.updateUser(uentry.doc_id,None,None,None,None,None,country,None)
        elif k == 'f': # Password
            n = 0
            conn.SendTML('<BR><CRSRU>')
            while n < 3:
                if conn.QueryFeature(TT.LINE_FILL) < 0x80:
                    conn.Sendall(TT.Fill_Line(14,32))
                else:
                    conn.SendTML(f'<AT x=0 y=14><SPC n={scwidth}><CRSRU>')
                conn.SendTML('Old password:')
                pw = _dec(conn.ReceiveStr(keys, 16, True))
                if not conn.connected:
                    return
                if conn.bbs.database.chkPW(uentry,pw,False):
                    m = False
                    conn.SendTML('<BR><CRSRU>')
                    while not m:
                        if conn.QueryFeature(TT.LINE_FILL) < 0x80:
                            conn.Sendall(TT.Fill_Line(14,32))
                        else:
                            conn.SendTML(f'<AT x=0 y=14><SPC n={scwidth}><CRSRU>')                      
                        conn.SendTML('New password:')
                        pw = _dec(conn.ReceiveStr(keys, 16, True))
                        if not conn.connected:
                            return
                        if len(pw) < 6:
                            conn.SendTML('<ORANGE><BR>Password must be 6 to 16 characters<BR>long, try again<BR><PAUSE n=2>')
                            if conn.QueryFeature(TT.LINE_FILL) < 0x80:
                                conn.SendTML('<LFILL row=15 code=32><LFILL row=16 code=32><CRSRU n=3>')
                            else:
                                conn.SendTML(f'<AT x=0 y=15><SPC n={scwidth*2}><CRSRU n=3>')
                        else:
                            conn.bbs.database.updateUser(uentry.doc_id,None,pw,None,None,None,None,None)
                            m = True
                            n = 3
                else:
                    conn.SendTML('<BR>Incorrect password<BR>try again<BR><PAUSE n=2>')
                    if conn.QueryFeature(TT.LINE_FILL) < 0x80:
                        conn.SendTML('<LFILL row=15 code=32><LFILL row=16 code=32><CRSRU n=3>')
                    else:
                        conn.SendTML(f'<AT x=0 y=15><SPC n={scwidth*2}><CRSRU n=3>')
                    n += 1
        elif k == 'g': # Preferences
            EditPrefs(conn)


###############################
# Edit user preferences
###############################
def EditPrefs(conn:Connection):
    conn.SendTML(f'<SPLIT row=0 multi=False btop=f{conn.encoder.colors.get("BLACK",0)} bgbottom={conn.encoder.colors.get("BLACK",0)} mode={conn.mode}>')    # Cancel any split screen/window
    done = False
    scwidth = conn.encoder.txt_geo[0]
    line = 64 if 'PET' in conn.mode else 23
    back = conn.encoder.decode(conn.encoder.back)
    while (not done) and conn.connected:
        uentry = conn.bbs.database.chkUser(conn.username)
        options = 'ab' + back
        prefs = uentry.get('preferences',{'intro':True,'datef':conn.bbs.dateformat})
        RenderMenuTitle(conn,"Edit User Preferences")
        conn.SendTML('<CRSRD n=2>')
        label = crop('Login to Main menu', scwidth-9,conn.encoder.ellipsis)
        KeyLabel(conn,'a',f'{label}: {"No" if prefs.get("intro",True) else "Yes"}',True)
        conn.SendTML('<BR>')
        label = crop('Date format', scwidth-(6+len(date_strings[prefs.get('datef',conn.bbs.dateformat)][1])),conn.encoder.ellipsis)
        KeyLabel(conn,'b',f'{label}: {date_strings[prefs.get("datef",conn.bbs.dateformat)][1]}',True)
        conn.SendTML('<BR>')
        x = 2
        st = True
        opdic = {}
        for p in bbs_instance.plugins:
            ppf = bbs_instance.plugins[p][2]    # Plugin preferences function present?
            if ppf != None:
                pp = ppf()  # Get plugin preferences
                for i in pp:
                    pv = i['values']
                    value = ppf(conn,i['name'])
                    if type(pv) == dict:    # Preference can have a given set of values
                        value = pv[value]   # Translate preference value to a verbose string
                    label = crop(i['title'], scwidth-(6+len(value)),conn.encoder.ellipsis)
                    KeyLabel(conn,valid_keys[x],label+': '+value, st)
                    conn.SendTML('<BR>')
                    options += valid_keys[x]
                    opdic[valid_keys[x]] = (ppf, i)
                    x += 1
                    st = not st

        KeyLabel(conn,back,'Exit',True)
        conn.SendTML('<BR><BR>')
        if conn.QueryFeature(TT.LINE_FILL) < 0x80:
            conn.Sendall(TT.Fill_Line(6+x,line))  # TODO: paginate preferences
        else:
            conn.SendTML(f'<CRSRU><HLINE n={conn.encoder.txt_geo[0]}>')
        conn.SendTML('Press option')
        k = conn.ReceiveKey(options)
        if k == back:
            done = True
        elif k == 'a':
            conn.SendTML('<BR><CRSRU>Login directly to Main menu? (Y/N) ')
            k = conn.ReceiveKey('yn')
            if k == 'n':
                conn.SendTML('NO<PAUSE n=1>')
                prefs['intro'] = True
            else:
                conn.SendTML('YES<PAUSE n=1>')
                prefs['intro'] = False
            conn.bbs.database.updateUserPrefs(uentry.doc_id,prefs)
        elif k == 'b':
            conn.SendTML('<BR><CRSRU>Date format:<BR><BR>0) DD/MM/YYYY<BR>1) MM/DD/YYYY<BR>2) YYYY/MM/DD<CRSRU n=4>')
            k = conn.ReceiveKey('012')
            conn.Sendall(k)
            time.sleep(1)
            prefs['datef'] = int(k)
            conn.bbs.database.updateUserPrefs(uentry.doc_id,prefs)
        else:   # Plugin preferences
            option = opdic[k][1]
            conn.SendTML('<BR><CRSRU>'+option['prompt'])
            if type(option['values']) == dict:
                # Render options
                conn.SendTML('<BR>')
                options = ''
                ans = {}
                for x,o in enumerate(option['values']):
                    KeyLabel(conn,valid_keys[x],option['values'][o], st)
                    conn.SendTML('<BR>')
                    st = not st
                    ans[valid_keys[x]] = o
                    options += valid_keys[x]
                k = conn.ReceiveKey(options)
                conn.bbs.database.updateUserPrefs(uentry.doc_id,{option['name']:ans[k]})
                # print(option['name'],ans[k])
            else:
                #TODO: Implement string and integer preferences
                ...
            time.sleep(2)


###############################
# Display user list
###############################
def UserList(conn:Connection):
    if conn.menu != -1:
        conn.MenuStack.append([conn.MenuDefs,conn.menu])
        conn.menu = -1
    # Init Menu parameter dictionary if needed
    if conn.MenuParameters == {}:
        conn.MenuParameters['current'] = 0
    # Start with barebones MenuDic
    MenuDic = { 
                conn.encoder.decode(conn.encoder.back): (MenuBack,(conn,),"Previous Menu",0,False),
                conn.encoder.nl: (UserList,(conn,),"",0,False)
              }	
    # Select screen output
    conn.SendTML(f'<SETOUTPUT><NUL n=2><TEXT border={conn.style.BoColor} background={conn.style.BgColor}><CLR><MTITLE t="User list">')
    users = conn.bbs.database.getUsers()
    users = sorted(users, key= lambda l:l[0])
    digits = len(str(max(users[:])[0]))
    tml = '<WHITE> ID         Username<BR><BR><LTGREEN>'
    if conn.QueryFeature(TT.LINE_FILL) < 0x80:
        tml += f'<LFILL row=4 code={64 if "PET" in conn.mode else 0x17}>'
    else:
        tml += f'<CRSRU><HLINE n={conn.encoder.txt_geo[0]}>'
    conn.SendTML(tml)
    pages = int((len(users)-1) / 18) + 1
    count = len(users)
    start = conn.MenuParameters['current'] * 18
    end = start + 17
    if end >= count:
        end = count - 1
    # Add pagination keybindings to MenuDic
    if pages > 1:
        if conn.MenuParameters['current'] == 0:
            page = pages-1
        else:
            page = conn.MenuParameters['current']-1
        MenuDic['<'] = (SetPage,(conn,page),'Previous Page',0,False)
        if conn.MenuParameters['current'] == pages-1:
            page = 0
        else:
            page = conn.MenuParameters['current']+1
        MenuDic['>'] = (SetPage,(conn,page),'Next Page',0,False)
    x = 0
    for x in range(start, end + 1):
        KeyLabel(conn, str(users[x][0]).zfill(digits), f'   {users[x][1]}<BR>', x % 2)
    else:
        lineasimpresas = end - start + 1
        if lineasimpresas < 18:
            for x in range(18 - lineasimpresas):
                conn.SendTML('<BR>')
    conn.SendTML(f' <GREY3><RVSON><BACK> <LTGREEN>Back <GREY3>&lt; <LTGREEN>Prev.Page <GREY3>&gt; <LTGREEN>Next Page  <RVSOFF><BR>'
                f'<WHITE> [{conn.MenuParameters["current"]+1}/{pages}]<CYAN> Selection:<WHITE> ')
    if conn.T56KVer > 0:
        conn.Sendall(TT.to_Speech() + 'seleksioneunaopsion,')
        time.sleep(1)
        # Select screen output
        conn.Sendall(TT.to_Screen())
    return MenuDic

##########################################################
# Check terminal for some basic features on connection
##########################################################
def GetTerminalFeatures(conn:Connection, display = True):
    conn.SendTML(f'<RESET><SETOUTPUT o=True><TEXT border={conn.style.BoColor} background={conn.style.BgColor}>'
                 f'<CLR><LOWER><LTBLUE>Terminal ID: <WHITE>{conn.TermString.decode("utf-8")}<BR>'
                f'<LTBLUE>Turbo56K version: <WHITE>{conn.T56KVer}<BR><PAUSE n=0.5>')
    if b"RETROTERM-SL" in conn.TermString:
        _LOG('SwiftLink mode, audio streaming at 7680Hz',id=conn.id,v=3)
        conn.samplerate = 7680
    elif (b"RETROTERM-P4" in conn.TermString) or (b"RETROTERM-M1" in conn.TermString):
        if b'M138' in conn.TermString:
            _LOG('MSX 38K mode, audio streaming at 7680Hz',id=conn.id,v=3)
            conn.samplerate = 7680
        else:
            _LOG('Plus/4 / MSX mode, audio streaming at 3840Hz',id=conn.id,v=3)
            conn.samplerate = 3840
    elif b'UNKNOWN-' in conn.TermString:   # Unknown Turbo56k terminal
        conn.SendTML('<BR>Enter your baudrate<BR>(57600): ')
        conn.samplerate = conn.ReceiveInt(1200,115200,57600)//5
        conn.SendTML('<BR>')
    grey = f'<INK c={conn.style.TxtColor}>'
    if conn.T56KVer > 0.5:
        good = f"<INK c={conn.style.OKTxtColor}>+" if "MSX" in conn.mode else f"<INK c={conn.style.OKTxtColor}><CHECKMARK>"
        conn.SendTML(f'<LTBLUE>{conn.encoder.nl.join(formatX("Checking some terminal features...",conn.encoder.txt_geo[0]),)}<BR>')
        for cmd in [129,130,179]:
            conn.SendTML(f'{grey}{TT.T56K_CMD[cmd]}: {good if conn.QueryFeature(cmd)< 0x80 else f"<INK c={conn.style.BADTxtColor}>x"}<BR>')
    conn.SendTML('<BR>')
    if conn.QueryFeature(131) < 0x80:
        conn.SendTML(f'{grey}PCM audio samplerate <YELLOW>{conn.samplerate}Hz<BR>')
    time.sleep(0.5)

##############################
# Main BBS Loop
##############################
def BBSLoop(conn:Connection):

    try:
        # Sync
        conn.SendTML('<NUL n=2>')
        if conn.bbs.lang == 'es':
            pt = "intentando detectar terminal,<BR>presione su tecla BACKSPACE (INS/DEL en Commodore)...<BR>"
        else:
            pt = "trying to detect terminal,<BR>press your BACKSPACE key, (INS/DEL on Commodore)...<BR>"

        welcome = f'''<FORMAT>{conn.bbs.WMess.upper()}<BR>
RETROBBS V{conn.bbs.version:.2f}<BR>
RUNNING UNDER:<BR>
{conn.bbs.OSText.upper()}<BR>
{pt.upper()}<BR></FORMAT>'''

        conn.Flush(0.5) # Flush for 0.5 seconds
        conn.SendTML(welcome)
        backspaces = []
        for encoder in conn.bbs.encoders:
            if conn.bbs.encoders[encoder].bs not in backspaces:
                backspaces.append(conn.bbs.encoders[encoder].bs)

        n = 0
        backspace = ''
        while conn.connected:
           data = conn.NBReceive(1,10)
           if len(data) == 0:
               conn.SendTML('\nTIMEOUT - DISCONNECTED\n')
               conn.connected = False
               return
           elif chr(data[0]) in backspaces:
               backspace = chr(data[0])
               break
           n += 1
           if n < 3:
               conn.SendTML(pt.upper())
           else:
               conn.SendTML('SORRY, UNKNOWN TERMINAL - DISCONNECTED')
               conn.connected = False
               return

        # WaitRETURN(conn)
        conn.Flush(0.5) # Flush for 0.5 seconds

        # Ask for ID and supported TURBO56K version
        time.sleep(1)
        datos = b""
        conn.Sendall(chr(TT.CMDON) + chr(TT.VERSION) + chr(TT.CMDOFF))
        datos = conn.NBReceive(2,5)
        _LOG('ID:', datos[0:2],id=conn.id,v=4)
        if datos[0:2] == b"RT":
            datos = datos[2:]
            datos += conn.Receive(20-len(datos))
            _LOG('Terminal: ['+ bcolors.OKGREEN + str(datos) + bcolors.ENDC + ']',id=conn.id,v=4)
            dato1 = conn.Receive(1)
            dato2 = conn.Receive(1)
            _LOG('TURBO56K version: '+ bcolors.OKGREEN + str(ord(dato1)) + '.' + str(ord(dato2)) + bcolors.ENDC,id=conn.id,v=4) 
            t56kver = ord(dato1)+((ord(dato2))/10)
            if t56kver > 0.4:
                mode = 'PET64' if b'-' not in datos else conn.bbs.clients.get(datos.split(b' ')[0].split(b'-')[1],None)
                if mode == None:    # Unknown Turbo56k terminal
                    encoders = []
                    for encoder in conn.bbs.encoders:       # Get Turbo56k encoders
                        if conn.bbs.encoders[encoder].minT56Kver > 0:
                            encoders.append(conn.bbs.encoders[encoder])
                    conn.SendTML("<FORMAT>UNKNOWN TURBO56K CLIENT, PLEASE SELECT THE CLIENT THAT MORE CLOSELY MATCH YOURS:</FORMAT><BR><BR>")
                    count = 0
                    clist = []
                    for encoder in encoders:
                        for client in encoder.clients:
                            conn.SendTML(f'{count+1}:{encoder.clients[client].upper()}<BR>')
                            count += 1
                            clist.append([encoder.name,client])
                    conn.SendTML('<BR>YOUR CHOICE:')
                    sel = conn.ReceiveInt(1,len(clist),1)-1
                    t_mode = (b'UNKNOWN-'+clist[sel][1]) if clist[sel][1] !='default' else b'RETROTERM'
                    conn.SendTML('<BR>')
                    conn.SetMode(t_mode,t56kver)
                else:
                    conn.SetMode(datos,t56kver)

            else:
                _LOG('Old terminal detected - Terminating',id=conn.id)
                conn.SendTML('Please use RETROTERM v0.13 or posterior<BR> For the latest version visit<BR>WWW.PASTBYTES.COM/RETROTERM<BR><WHITE>')
                conn.connected = False
        else:
            conn.SendTML(   '<FORMAT><BR>FOR THE BEST EXPERIENCE, THIS BBS REQUIRES A TERMINAL COMPATIBLE WITH TURBO56K 0.3 OR NEWER.<BR>'
                            'FOR THE LATEST VERSION VISIT<BR>WWW.PASTBYTES.COM/RETROTERM<BR><BR></FORMAT>')
            conn.Flush(1)
            encoders = []
            for encoder in conn.bbs.encoders:       # Get encoders which use the same backspace character
                if conn.bbs.encoders[encoder].bs == backspace and conn.bbs.encoders[encoder].minT56Kver == 0:
                    encoders.append(conn.bbs.encoders[encoder])
            if encoders != []:
                conn.SetMode(b'temp-'+next(iter(encoders[0].clients.keys())),0)  # Temporarily set the first valid encoder
                conn.SendTML("<FORMAT>SELECT THE PLATFORM THAT MORE CLOSELY MATCH YOURS:</FORMAT><BR><BR>")
                count = 0
                clist = []
                for encoder in encoders:
                    for client in encoder.clients:
                        if client != b'_default_':
                            conn.SendTML(f'{count+1}:{encoder.clients[client].upper()}<BR>')
                            count += 1
                            clist.append([encoder.name,client])
                conn.SendTML('<BR>YOUR CHOICE:')
                mode = b'Standard-'+clist[conn.ReceiveInt(1,len(clist),1)-1][1]
                conn.SendTML('<BR>')
                conn.SetMode(mode,0)
                conn.SendTML(f'<TEXT><WHITE><CLR><FORMAT><YELLOW>BBS mode set to:<WHITE> {conn.mode}</FORMAT><BR><BR><PAUSE n=2>')
            else:
                conn.SendTML('<FORMAT>SORRY, UNKNOWN CLIENT TYPE, DISCONNECTED...</FORMAT><BR>')
                conn.connected = False
        if conn.connected:
            # Get Turbo56K terminal features and send splash screen if possible
            if conn.T56KVer > 0.4:
                GetTerminalFeatures(conn)
            conn.SendTML(conn.templates.GetTemplate('main/splash'),**{})
            time.sleep(1)
            Done = False
            tml = f'<NUL n=2><SPLIT bgbottom={conn.encoder.colors.get("BLACK",0)} mode="_C.mode">{"<CLR>" if conn.encoder.features["windows"]!= 0 else ""}'
            # Login and intro slideshow
            while True:
                r = conn.SendTML(f'<BR><INK c={conn.style.TxtColor}>(L)ogin OR (G)uest?<PAUSE n=1><INKEYS k="lgs"><BR>')
                if not conn.connected:
                    return()
                t = r['_A']
                if t == 'l':
                    SignIn(conn)
                    if conn.username != '_guest_':
                        conn.SendTML(tml)
                        uentry = conn.bbs.database.chkUser(conn.username)
                        prefs = uentry.get('preferences',{'intro':True})
                        if prefs['intro']:
                            SlideShow(conn,'',conn.bbs.Paths['bbsfiles']+'intro/')
                        conn.SendTML('<CURSOR>')
                        break
                elif t == 'g':
                    conn.SendTML(tml)
                    SlideShow(conn,'',conn.bbs.Paths['bbsfiles']+'intro/')
                    conn.SendTML('<CURSOR>')
                    break
                else:
                    conn.SendTML(tml)
                    break

            # Increment visit counters
            conn.bbs.visits += 1                        # Session counter
            conn.bbs.database.newVisit(conn.username)   # Total counter
            # Execute session startup TML
            if exists(conn.bbs.Paths['bbsfiles']+'newsession.tml'):
                with open(conn.bbs.Paths['bbsfiles']+'newsession.tml','r') as slide:
                    tml = slide.read()
                    conn.SendTML(f'<CLR>{tml}')
            # Display the main menu
            conn.menu = 0		# Starting at the main menu
            conn.MenuDefs = GetKeybindings(conn,0)
            SendMenu(conn)
            while conn.connected == True and _run == True:
                data = conn.Receive(1)
                _LOG('received "'+bcolors.OKBLUE+str(data)+bcolors.ENDC+'"',id=conn.id,v=4)
                if data != b'' and conn.connected == True:
                    data = conn.encoder.decode(data.decode('latin1'))
                    if data in conn.MenuDefs:
                        if conn.userclass >= conn.MenuDefs[data][3]:
                            prompt = crop(conn.MenuDefs[data][2], conn.encoder.txt_geo[0]//2,conn.encoder.ellipsis)
                            conn.SendTML(f'{prompt}<PAUSE n=1>')
                            wait = conn.MenuDefs[data][4]
                            Function = conn.MenuDefs[data][0]
                            res = Function(*conn.MenuDefs[data][1])
                            if isinstance(res,dict):
                                conn.MenuDefs = res
                            elif data!=conn.encoder.nl:
                                # Only wait for RETURN if the function suceeded <<< ATTENTION: if the function returns 0 on success this check will fail
                                if wait and (res != False):
                                    WaitRETURN(conn,60.0*5)
                                    if conn.T56KVer > 0:
                                        conn.SendTML('<NUL n=2><CURSOR>')   #Enable cursor blink just in case
                                Function = conn.MenuDefs[conn.encoder.nl][0]
                                res = Function(*conn.MenuDefs[conn.encoder.nl][1])
                                if isinstance(res,dict):
                                    conn.MenuDefs = res
                        else:
                            conn.SendTML("You can't access this area<PAUSE n=2>")
                            SendMenu(conn)
                    else:
                        continue
                else:
                    _LOG('no more data from', conn.addr, id=conn.id)
                    break


    finally:
        # Clean up the connection
        conn.socket.close()
        _LOG('Disconnected',id=conn.id,v=3)

###################################################
# Connection management thread
# Checks if connections are alive, once per second
# Reloads configuration file if it's modified and
# the BBS is idling
###################################################
def ConnTask():
    global conlist
    global bbs_instance
    global _semaphore

    while _run:
        time.sleep(1) # check once per second

        # Reload configuration file if it has been modified and there's nobody online
        if len(conlist) == 0:
            if getmtime(config_file) != bbs_instance.cfgmts:
                _LOG('Config file modified',v=2)
                _semaphore = True
                ConfigRead()
                bbs_instance.start()    #Restart
                _semaphore = False

        for t in range(1,bbs_instance.lines+1):
            if t in conlist:                        # Find closed connections
                conn = conlist[t][1]
                if not conlist[t][0].is_alive():
                    conn.Close()
                    if conn.userclass != 0:
                        bbs_instance.database.logoff(conn.userid,conn.outbytes,conn.inbytes)
                    del conn
                    try:
                        conlist[t][0].join()
                    except:
                        pass
                    conlist.pop(t)
                    _LOG('Slot freed - Awaiting a connection',v=3)
                else:                               # Do housekeeping tasks (just updating spinners for now)
                    if conn.on_hold:
                        if conn.spinner != None:
                            conn._HoldUpdate()


#######################################################
# MAIN
#######################################################

# Initialize variables
parser = argparse.ArgumentParser(description='Python BBS server for Turbo56K enabled terminals')
parser.add_argument('-v', dest='verb', type=int, choices=range(1,5),nargs='?', const=1, default=1, help='Verbosity level (1-4): 1 = Errors only | 4 = All logs')
parser.add_argument('-c', dest='config', type=str, nargs='?', const='config.ini', default='config.ini', help='Path to the configuration file to be used')

if AA.wavs != True:
    _LOG('Audio fileformats not available!', v=2)
if AA.meta != True:
    _LOG('Audio Metadata not available!', v=2)

args = parser.parse_args()
set_verbosity(args.verb)

# Set configuration file
config_file = args.config

_semaphore = False  #

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

print('\n\nRetroBBS v%.2f (c)2021-2025\nby Pablo Roldán(durandal) and\nJorge Castillo(Pastbytes)\n\n'%_version)

# Init plugins
bbs_instance.plugins = EX.RegisterPlugins()
# Init encoders
bbs_instance.encoders = EX.RegisterEncoders()
# Init Client ID -> encoder dictionary
for encoder in bbs_instance.encoders:
    for client in bbs_instance.encoders[encoder].clients:
        bbs_instance.clients[client] = encoder
        # if bbs_instance.encoders[encoder].minT56Kver > 0:
        #     _LOG(f'Turbo56K client: {client}',v=4)
        # else:
        #     _LOG(f'Standard client: {client}',v=4)
# Register TML tags
EX.RegisterTMLtags()

# Read config file
ConfigRead()

bbs_instance.start()

# Register CTRL-C handler
signal.signal(signal.SIGINT, signal_handler)
# Create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
# Bind the socket to the port
server_address = (bbs_instance.ip, bbs_instance.port)
_LOG('Initializing server on %s port %s' % server_address,v=3)
sock.bind(server_address)
# Listen for incoming connections. Max 2 connections in queue
sock.listen(2)
#List of current active connections
conlist = {}
conthread = threading.Thread(target = ConnTask, args = ())
conthread.start()
_LOG('READY.',v=1)
while True:
    # Wait for a connection
    _LOG('Awaiting a connection',v=3)
    c, c_addr = sock.accept()

    while _semaphore:   # Wait for _semaphore to be False (config finished updating)
        pass

    newid = 1
    for r in range(1,bbs_instance.lines+1):			#Find free id
        if r not in conlist:
            newid = r
            newconn = Connection(c,c_addr,bbs_instance,newid)
            conlist[newid] = [threading.Thread(target = BBSLoop, args=(newconn,)),newconn]
            conlist[newid][0].start()
            break
    else:   # No free slot, refuse connection
        c.sendall(bytes(bbs_instance.BSYMess,'latin1'))
        c.close()
