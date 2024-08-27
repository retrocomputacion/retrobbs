import sys
import time
import numpy
import re
import os
from os import walk
import random
import subprocess
import signal
import math
import asyncio
from PIL import Image, ImageDraw
from io import BytesIO

from common.bbsdebug import _LOG,bcolors
from common import helpers as H
from common import style as S
from common.connection import Connection
from common import turbo56k as TT
from common.style import RenderMenuTitle, KeyLabel
from common.imgcvt import convert_To, cropmodes, PreProcess, gfxmodes, dithertype, get_ColorIndex
from common.filetools import SendBitmap


import audioread
wavs = True
#Audio Metadata
try:
    import mutagen
    meta = True
except:
    meta = False

#SIDStreaming
import common.siddumpparser as sd
import common.ymparse as ym

##########################################################
# Display list of audio files, with playtime
##########################################################
def AudioList(conn:Connection,title,speech,logtext,path):

    if conn.menu != -1:
        conn.MenuStack.append([conn.MenuDefs,conn.menu])
        conn.menu = -1
    # Init Menu parameter dictionary if needed
    if conn.MenuParameters == {}:
        conn.MenuParameters['current'] = 0

    fcount = conn.encoder.txt_geo[1]-5
    scwidth = conn.encoder.txt_geo[0]
    # Start with barebones MenuDic
    MenuDic = { 
                conn.encoder.back: (H.MenuBack,(conn,),"Previous Menu",0,False),
                conn.encoder.nl: (AudioList,(conn,title,speech,logtext,path),title,0,False)
            }

    _LOG(logtext,id=conn.id,v=4)
    _LOG('Displaying Page: '+str(conn.MenuParameters['current']+1),id=conn.id,v=4)
    # Send speech message
    conn.Sendall(TT.to_Speech() + speech)
    time.sleep(1)
    # Selects screen output
    conn.Sendall(TT.to_Screen())
    # Sync
    conn.Sendall(chr(0)*2)
    # # Text mode
    conn.Sendall(TT.to_Text(0,conn.style.BoColor,conn.style.BgColor))

    RenderMenuTitle(conn,title)

    # Sends menu options
    files = []	#all files
    audios = []	#filtered list
    #Read all the files from 'path'
    for entries in walk(path):
        files.extend(entries[2])
        break

    wext = ('.wav','.mp3')  # PCM file extensions
    sidext = ('.sid','.mus')    # SID file extensions
    ymext = ('.ym','.vtx','.vgz')   #  YM file extensions

    filefilter = sidext+ymext   #('.sid','.mus','.ym','.vtx','.vgz')
    if wavs == True:
        filefilter = filefilter + wext

    #Filters only the files matching 'filefilter'
    for f in files:
        if f.lower().endswith(filefilter):
            audios.append(f)


    audios.sort()	#Sort list

    #for t in range(0,len(audios)):
    #	length.append(0.0)
    length = [0.0]*len(audios)	#Audio length list

    #Calc pages
    pages = int((len(audios)-1) / fcount) + 1
    count = len(audios)
    start = conn.MenuParameters['current'] * fcount
    end = start + fcount -1
    if end >= count:
        end = count - 1

    #Add pagination keybindings to MenuDic
    if pages > 1:
        if conn.MenuParameters['current'] == 0:
            page = pages-1
        else:
            page = conn.MenuParameters['current']-1
        MenuDic['<'] = (H.SetPage,(conn,page),'Previous Page',0,False)
        if conn.MenuParameters['current'] == pages-1:
            page = 0
        else:
            page = conn.MenuParameters['current']+1
        MenuDic['>'] = (H.SetPage,(conn,page),'Next Page',0,False)

    row = 3
    for x in range(start, end + 1, 1):
        afunc = PlayAudio
        bname = os.path.splitext(os.path.basename(audios[x]))[0]
        KeyLabel(conn, H.valid_keys[x-start],H.crop(bname,scwidth-10,conn.encoder.ellipsis)+' ', x % 2)
        tml = f'<AT x={scwidth-6} y={row}><SPINNER><CRSRL>'
        if (wavs == True) and (audios[x].lower().endswith(wext)):   #PCM file
            conn.SendTML(tml)
            tsecs = _GetPCMLength(path+audios[x])
            tmins = int(tsecs / 60)
            length[x] = int(tsecs)
            tsecs = tsecs - (tmins * 60)
        else:   #SID/YM files
            conn.SendTML(tml)
            afunc = CHIPStream
            tsecs = _GetCHIPLength(path+audios[x])
            tmins = int(tsecs[0] / 60)
            length[x] = tsecs
            tsecs = tsecs[0] - (tmins * 60)

        conn.SendTML(f'<WHITE>{tmins:0>2}:{tsecs:0>2}<BR>')
        row += 1
        #Add keybinding to MenuDic
        MenuDic[H.valid_keys[x-start]] = (afunc,(conn,path+audios[x],length[x],True),H.valid_keys[x-start],0,False)
    else:
        lineasimpresas = end - start + 1
        if lineasimpresas < fcount:
            for x in range(fcount - lineasimpresas):
                conn.Sendall(conn.encoder.nl)

    if 'PET' in conn.mode:
        conn.SendTML(f' <GREY3><RVSON><BACK> <LTGREEN>Prev. Menu <GREY3>&lt; <LTGREEN>Prev.Page <GREY3>&gt; <LTGREEN>Next Page  <RVSOFF><BR>')
    else:
        conn.SendTML(f' <GREY><RVSON> <BACK> <LTGREEN>Go Back <GREY>&lt; <LTGREEN> P.Page <GREY>&gt; <LTGREEN>N.Page <RVSOFF><BR>')
    conn.SendTML(f'<WHITE> [{conn.MenuParameters["current"]+1}/{pages}]<CYAN> Selection:<WHITE> ')
    conn.Sendall(chr(255) + chr(161) + 'seleksioneunaopsion,')
    # Selects screen output
    conn.SendTML('<PAUSE n=1><SETOUTPUT>')
    return MenuDic

#########################################
# Display audio dialog
#########################################
def _AudioDialog(conn:Connection, data):
    if data.get('apic', None) != None:
        #im = convert_To(Image.open(BytesIO(data['apic'])), cropmode= cropmodes.LEFT)
        im = Image.open(BytesIO(data['apic']))
        im.thumbnail((128,128))
        if conn.mode == "PET64":
            gm = gfxmodes.C64HI
        elif conn.mode == "PET264":
            gm = gfxmodes.P4HI
        else:
            gm = conn.encoder.def_gfxmode

        c_black = (0,0,0)
        c_white = (0xff,0xff,0xff)
        c_yellow = (0xff,0xff,0x55)
        c_pink = (0xdd,0x66,0x66)

        img = convert_To(im, cropmode=cropmodes.LEFT, preproc=PreProcess(contrast=1.5,saturation=1.5), gfxmode=gm)
        pwidth = img[0].size[0]
        pheight = img[0].size[1]
        draw = ImageDraw.Draw(img[0])
        # Fill unused space with black
        draw.rectangle([0,0,128,(pheight-128)//2],fill = c_black)
        draw.rectangle([0,((pheight-128)//2)+128,128,pheight],fill = c_black)
        draw.rectangle([128,0,pwidth,pheight],fill = c_black)
        draw.text((pwidth//2,2),H.gfxcrop(data['title'],pwidth,H.font_bold),c_white,font=H.font_bold,anchor='mt')
        if data['album'] != '':
            draw.text((136,20),'Album:',c_white,font=H.font_bold)
            draw.text((136,32),H.gfxcrop(data['album'],pwidth-136),c_white,font=H.font_text)
        if data['artist'] != '':
            draw.text((136,48),'Artist:',c_white,font=H.font_bold)
            draw.text((136,60),H.gfxcrop(data['artist'],pwidth-136),c_white,font=H.font_text)			
        draw.text((136,72),'Length:',c_white,font=H.font_bold)
        draw.text((136,84),data['length'],c_white,font=H.font_text)			
        draw.text((136,108),f"From {data['sr']}",c_white,font=H.font_text)
        draw.text((136,120),f"To {conn.samplerate}Hz",c_white,font=H.font_text)
        draw.text((pwidth//2,pheight-32),"Press <RETURN> to play",c_white,font=H.font_text,anchor='mt')
        if 'MSX' in conn.mode:
            draw.text((pwidth//2,pheight-20),"Press <STOP> and wait to stop",c_yellow,font=H.font_text,anchor='mt')
            draw.text((pwidth//2,pheight-8),"Press <_> to cancel",c_yellow,font=H.font_text,anchor='mt')
        else:
            draw.text((pwidth//2,pheight-20),"Press <X> and wait to stop",c_yellow,font=H.font_text,anchor='mt')
            draw.text((pwidth//2,pheight-8),"Press <\u2190> to cancel",c_yellow,font=H.font_text,anchor='mt')
        # draw.text((136,136),"Press <RETURN> to play",c_white,font=H.font_text)
        # draw.text((136,152),"Press <X> and wait to stop",c_yellow,font=H.font_text)
        # draw.text((136,168),u"Press <\u2190> to cancel",c_pink,font=H.font_text)
        SendBitmap(conn,img[0],gfxmode=gm,preproc=PreProcess(),dither=dithertype.NONE)
    else:
        S.RenderDialog(conn, 15, data['title'])
        tml = ''
        if data['album'] != '':
            tml += f'<RVSON> Album:<BR><RVSON> {data["album"]}<BR><BR>'
        if data['artist'] != '':
            tml += f'<RVSON> Artist:<BR><RVSON> {data["artist"]}<BR><BR>'
        tml += f'''<RVSON> Length: {data['length']}<BR><BR>
<RVSON> From {data['sr']} to {conn.samplerate}Hz
<AT x=0 y=12> Press &lt;RETURN&gt; to play<BR>'''
        if 'MSX' in conn.mode:
            tml+='''<RVSON> Press &lt;STOP&gt; and wait to stop<BR>
<RVSON> Press &lt;<BACK>&gt; to cancel'''
        else:
            tml+='''<RVSON> Press &lt;x&gt; and wait to stop<BR>
<RVSON> Press &lt;<BACK>&gt; to cancel'''
        conn.SendTML(tml)
    if conn.ReceiveKey(conn.encoder.nl+conn.encoder.back) == conn.encoder.back:
        conn.SendTML('<CURSOR><SPINNER><CRSRL>')
        return False
    return True

###########################################
# Get audio length for PCM file in seconds
###########################################
def _GetPCMLength(filename):
    try:
        if meta == True and filename[-4:] != '.wav' and filename[-4:] != '.WAV':
            #Load metadata
            audio = mutagen.File(filename, easy = True)
            tsecs = int(audio.info.length)
        else:
            #Load and compute audio playtime
            with audioread.audio_open(filename) as f:
                tsecs = int(f.duration)
    except:
        tsecs = 0
    return tsecs

######################################################################
# Send Audio file
######################################################################
def PlayAudio(conn:Connection,filename, length = 60.0, dialog=False):
    if conn.QueryFeature(TT.STREAM) >= 0x80:	#Exit if terminal doesn't support PCM streaming
        return
    bnoise = b'\x10\x01'
    CHUNK = 1<<int(conn.samplerate*1.4).bit_length()   #16384
    if length == None:
        length = _GetPCMLength(filename)
    conn.socket.settimeout(conn.bbs.TOut+length)	#<<<< This might be pointless
    _LOG('Timeout set to:'+bcolors.OKGREEN+str(length)+bcolors.ENDC+' seconds',id=conn.id,v=3)
    #Send any other supported audio file format
    conn.Sendall(chr(255) + chr(161) + '..enviando,')
    time.sleep(1)
    # Select screen output
    conn.Sendall(chr(255) + chr(160))
    _LOG('Sending audio: '+filename,id=conn.id,v=3)
    if (dialog == True) and (meta == True):
        a_meta = {}
        a_data = mutagen.File(filename)
        a_min = int(length/60)
        a_sec = int(round(length,0)-(a_min*60))
        a_meta['length'] = ('00'+str(a_min))[-2:]+':'+('00'+str(a_sec))[-2:]
        a_meta['sr'] = str(a_data.info.sample_rate)+'Hz'
        a_meta['title'] = os.path.splitext(os.path.basename(filename))[0][:38]  #filename[filename.rfind('/')+1:filename.rfind('/')+39]
        a_meta['album'] = ''
        a_meta['artist'] = ''
        if a_data.tags != None:
            if a_data.tags.getall('TIT2') != []:
                a_meta['title'] = a_data.tags.getall('TIT2')[0][0][:38]
            if a_data.tags.getall('TALB') != []:
                a_meta['album'] = a_data.tags.getall('TALB')[0][0][:38]
            for ar in range(1,5):
                ars = 'TPE'+str(ar)
                if a_data.tags.getall(ars) != []:
                    a_meta['artist'] = a_data.tags.getall(ars)[0][0][:38]
                    break
            if a_data.tags.getall('APIC') != []:
                # print('APIC',a_data.tags.getall('APIC'))
                a_meta['apic'] = a_data.tags.getall('APIC')[0].data
                # im = Image.open(BytesIO(apic))
                # im.show()
        if not _AudioDialog(conn,a_meta):
            return()
        if not conn.connected:
            return()
        conn.SendTML('<SPINNER><CRSRL><NUL><NUL>')
    #Streaming mode
    binario = b'\xFF\x83'
    pcm_stream = PcmStream(filename,conn.samplerate)
    t0 = time.time()
    streaming = True
    t_samples = length * conn.samplerate # Total number of samples for the selected playtime
    c_samples = 0   # Sample counter
    while streaming == True:
        t1 = time.time()
        audio = asyncio.run(pcm_stream.read(CHUNK))
        t2 = time.time()-t1
        if t2 > 15:
            streaming = False
        a_len = len(audio)
        if a_len == 0:
            streaming = False
        if (a_len % 2) != 0:    #Odd number of samples
            audio = numpy.append(audio, 0)
            a_len += 1
        for b in range(0,a_len,2):
            lnibble = int(audio[b])
            #if lnibble == 0:
            #    lnibble = 1
            if b+1 <= a_len:
                hnibble = int(audio[b+1])
            else:
                hnibble = 0
            binario += (lnibble+(16*hnibble)).to_bytes(1,'big')

            conn.Sendallbin(re.sub(b'\\x00', lambda x:bnoise[random.randint(0,1)].to_bytes(1,'little'), binario))
            streaming = conn.connected
            sys.stderr.flush()
            #Check for terminal cancelation
            conn.socket.setblocking(0)	# Change socket to non-blocking
            try:
                hs = conn.socket.recv(1)
                if hs == b'\xff':
                    binario = b''
                    _LOG('USER CANCEL',id=conn.id,v=3)
                    streaming = False
                    try:
                        t3 = time.time()
                        while time.time()-t3 < 1:   # Flush receive buffer for 1 second
                            conn.socket.recv(10)
                    except:
                        pass
                    conn.socket.setblocking(1)
                    break
            except:
                pass
            conn.socket.setblocking(1)
            binario = b''
        c_samples += a_len
        if t_samples > 0 and c_samples >= t_samples:  # Finish streaming if number of samples equals or exceed playtime
            streaming = False

        ts = ((CHUNK/conn.samplerate)-(time.time()-t1))*0.95
        time.sleep(ts if ts>=0 else 0)
        #while streaming and (time.time()-t1 < (CHUNK/conn.samplerate)): #This method should work for all samplerates
        #    pass                                        #and with different host performances
    binario += b'\x00\x00\x00\x00\x00\x00\xFE'
    t = time.time() - t0
    pcm_stream.stop()
    _LOG('Stream completed in '+bcolors.OKGREEN+str(round(t,2))+bcolors.ENDC+' seconds',id=conn.id,v=4)
    conn.Sendallbin(binario)
    time.sleep(1)
    conn.socket.settimeout(conn.bbs.TOut)
    conn.SendTML('<CURSOR>')

############# PcmStream Class ############
# Receive an audio stream through FFMPEG #
class PcmStream:
    def __init__(self, fn, sr):
        # self.pcm_stream = subprocess.Popen(["ffmpeg", "-i", fn, "-loglevel", "panic", "-vn", "-ac", "1", "-ar", str(sr), "-dither_method", "modified_e_weighted", "-f", "s16le", "pipe:1"],
        #                 stdout=subprocess.PIPE, preexec_fn=os.setsid)
        self.pcm_stream = subprocess.Popen(["ffmpeg", "-i", fn, "-loglevel", "panic", "-vn", "-ac", "1", "-ar", str(sr), "-dither_method", "modified_e_weighted", "-af", "acrusher=bits=4:mode=lin,acontrast=contrast=50", "-f", "u8", "pipe:1", "-nostdin"],
                        stdout=subprocess.PIPE, preexec_fn=os.setsid)

    async def read(self, size):
        try:
            a = self.pcm_stream.stdout.read(size)
            na = numpy.frombuffer(a, dtype=numpy.ubyte)
            norm = na/16
            bin8 = numpy.uint8(norm)

            return bin8
        except StopIteration:
            return b""
    
    def stop(self):
        self.pcm_stream.stdout.flush()
        self.pcm_stream.send_signal(signal.SIGINT)
        self.pcm_stream.terminate()
        #os.killpg(self.pcm_stream.pid, signal.SIGKILL)

###################################################
# Get CHIPtune playtimes from ssl file or metadata
###################################################
def _GetCHIPLength(filename):
    length = [60*3]
    tstr = None
    if os.path.isfile(filename[:-3]+'ssl') == True:
        with open(filename[:-3]+'ssl') as tf:
            tstr = tf.read()
    elif os.path.isfile(os.path.dirname(filename)+'/SONGLENGTHS/'+os.path.basename(filename)[:-3]+'ssl') == True:
        with open(os.path.dirname(filename)+'/SONGLENGTHS/'+os.path.basename(filename)[:-3]+'ssl') as tf:
            tstr = tf.read()
    data = ym.YMOpen(filename)
    if tstr != None:
        length = []
        for i in range(0,len(tstr),2):
            tmins = int(hex(ord(tstr[i]))[2:])
            tsecs = int(hex(ord(tstr[i+1]))[2:])
            length.append((tmins*60)+tsecs) # Playtime for the 1st subtune
    elif data != None:
        meta= ym.YMGetMeta(data)
        if meta != None:
            length = meta['songlength']
    
    return length

#############################################
# Display CHIPtune info dialog
#############################################
def _DisplayCHIPInfo(conn:Connection, info):
    
    def calctime():
        m = int(info['songlength'][subtune-1]/60)
        return m,info['songlength'][subtune-1]- (m*60)


    scwidth = conn.encoder.txt_geo[0]
    if isinstance(info,dict):   #.SID file
        subtune = info['startsong']
        minutes, seconds = calctime()
        S.RenderDialog(conn,12,info['type'])
        tml = f'''<RVSON> Title: {H.crop(info['title'],scwidth-10)}<BR>
<RVSON> Artist: {H.crop(info['artist'],scwidth-11)}<BR>
<RVSON> Copyright: {H.crop(info['copyright'],scwidth-13)}<BR>
<RVSON> Playtime: {minutes:0>2}:{seconds:0>2}<BR>'''
        if info['subsongs'] > 1:    #Subtune
            tml += f'<RVSON><CRSRD> Subtune: <GREY2>&lt;<WHITE><RVSOFF>{subtune:0>2}<RVSON><GREY2>&gt;<GREY3><BR>'
        tml += '<RVSON><CRSRD> Press <BACK> to exit<BR><RVSON> RETURN to play<BR><RVSON> Any key to stop<RVSOFF><CURSOR enable=False>'
        conn.SendTML(tml)
        while True and conn.connected:
            k = conn.ReceiveKey('<>'+conn.encoder.back+conn.encoder.nl)
            if k == conn.encoder.back:
                subtune = -1
                break
            elif k == conn.encoder.nl:
                break
            elif k == '<' and subtune > 1:
                subtune -= 1
                minutes, seconds = calctime()
                conn.SendTML(f'<RVSOFF><AT x=11 y=6><WHITE>{subtune:0>2}<RVSON><AT x=11 y=4><GREY3>{minutes:0>2}:{seconds:0>2}')
            elif k == '>' and subtune < info['subsongs']:
                subtune += 1
                minutes, seconds = calctime()
                conn.SendTML(f'<RVSOFF><AT x=11 y=6><WHITE>{subtune:0>2}<RVSON><AT x=11 y=4><GREY3>{minutes:0>2}:{seconds:0>2}')
    else:   #.MUS file
        subtune = 1
        conn.SendTML('<CLR><CBMSHIFT-E><UPPER>')
        conn.Sendallbin(info)
        conn.SendTML('<YELLOW><BR>press return to play<BR><BACK> to exit<BR>any key to stop<CURSOR enable=False>')
        if conn.ReceiveKey(conn.encoder.back+conn.encoder.nl) == conn.encoder.back:
            subtune = -1
    conn.SendTML('<CURSOR enable=True>')
    return subtune

#  SID player ID - commented out until better functionality is built into RetroTerm
# def _SIDid(binary):
#     with open('bbsfiles/sidid.cfg','rb') as sidf:

#         sigs = re.split(b'\s',sidf.read())

#         escape = b'.\|*?+$^{}[]()'

#         name = 'default'
#         IDList = {}
#         pat = b''
#         patterns = []
#         for s in sigs:
#             t = s.decode("utf-8")
#             if t == "END":
#                 patterns.append(pat)
#                 pat = b''
#             elif t == "??":
#                 pat += b"[\x00-\xff]"
#             elif t == "AND":
#                 pat += b"+"
#             else:
#                 try:
#                     h = bytearray.fromhex(t)
#                 except:
#                     h = None
#                 if h != None:
#                     if len(h) == 1:
#                         if h in escape:
#                             pat += b'\x5c'
#                         pat += h
#                 else:
#                     IDList[name]  = patterns
#                     name = t
#                     patterns = []


#         for st in IDList:
#             for pat in IDList[st]:
#                 if re.search(pat, binary) != None:
#                     return st
#     return 'default'

##########################################
# Stream SID/MUS files >>> DEPRECATED <<<
# Use CHIPStream instead
##########################################
SIDStream = lambda conn,filename,ptime,dialog=True,_subtune=None:CHIPStream(conn,filename,ptime,dialog,_subtune)

#############################################################################
# Stream register writes to the guest's sound chip
#############################################################################
def CHIPStream(conn:Connection, filename,ptime, dialog=True, _subtune=None):

    # V1f = '\x00\x01'    #Voice 1 Frequency
    # V1p = '\x02\x03'    #Voice 1 Pulse Width
    # V1c = '\x04'        #Voice 1 Control
    # V1e = '\x05\x06'    #Voice 1 Envelope
    
    # V2f = '\x07\x08'    #Voice 2 Frequency
    # V2p = '\x09\x0a'    #Voice 2 Pulse Width
    # V2c = '\x0b'        #Voice 2 Control
    # V2e = '\x0c\x0d'    #Voice 2 Envelope

    # V3f = '\x0e\x0f'    #Voice 3 Frequency
    # V3p = '\x10\x11'    #Voice 3 Pulse Width
    # V3c = '\x12'        #Voice 3 Control
    # V3e = '\x13\x14'    #Voice 3 Envelope

    # Fco = '\x15\x16'    #Filter Cutoff Frequency
    # Frs = '\x17'        #Filter Resonance
    # Vol = '\x18'        #Filter and Volume Control

    player = ""
    subtune = 1
    order = 0

    if conn.QueryFeature(TT.CHIPSTREAM) >= 0x80:	#Exit if terminal doesn't support chiptune streaming
        conn.SendTML('<CLR><ORANGE>Not supported!<PAUSE n=1>')
        return

    tmp,ext = os.path.splitext(filename)

    if ptime == None:
        ptime = _GetCHIPLength(filename)
    elif not isinstance(ptime,list):
        ptime = [ptime]
    try:
        if (ext.lower() in ['.sid','.mus']) and 'PET64' in conn.mode:	# SID music
            with open(filename, "rb") as fh:
                content = fh.read()
                if ext.lower() == '.sid':
                    info = {}
                    info['type'] = (content[:4].decode("iso8859-1"))
                    info['version'] = (content[5])
                    info['subsongs'] = (content[15])
                    info['startsong'] = (content[17])
                    subtune = info['startsong'] if _subtune == None else _subtune
                    info['title'] = (content[22:54].decode('iso8859-1')).strip(chr(0))
                    info['title'] = info['title'] if len(info['title'])>0 else '???'
                    info['artist'] = (content[54:86].decode('iso8859-1')).strip(chr(0))
                    info['artist'] = info['artist'] if len(info['artist'])>0 else '???'
                    info['copyright'] = (content[86:118].decode('iso8859-1')).strip(chr(0))
                    info['copyright'] = info['copyright'] if len(info['copyright'])>0 else '???'
                    if len(ptime)<info['subsongs']: #If no ssl file found or ptime list has insuficient entries
                        for i in range(info['subsongs']-len(ptime)):
                            ptime.append(ptime[0])
                    info['songlength'] = ptime
                    if info['version'] > 1:
                        info['speed'] = 1.2 if content[119]&12 == 8 else 1
                    else:
                        info['speed'] = 1
                else:
                    offset = (content[2]+content[3]*256)+(content[4]+content[5]*256)+(content[6]+content[7]*256)+8
                    info = content[offset:]

                #  SID player register order - commented out until better functionality is built into RetroTerm
                # player = _SIDid(content)
                # if (conn.T56KVer > 0.5):
                #     # If Turbo56K > 0.5 send SID register write order
                #     if (player == "MoN/Bjerregaard"):
                #         conn.Sendall(chr(TT.CMDON)+chr(TT.SIDORD))
                #         conn.Sendall(Frs+Fco + V3e+V3c+V3f+V3p + V2e+V2c+V2f+V2p + V1e+V1c+V1f+V1p + Vol)
                #         conn.Sendall(chr(TT.CMDOFF))
                #         order = 1
                #     else:
                #         #Sending the default write sequence shouldnt be needed, but is here just in case, and as reference
                #         conn.Sendall(chr(TT.CMDON)+chr(TT.SIDORD))
                #         conn.Sendall(V1f+V1p+V1c+V1e + V2f+V2p+V2c+V2e + V3f+V3p+V3c+V3e + Fco+Frs+Vol)
                #         conn.Sendall(chr(TT.CMDOFF))
                player = 'x'    # <<<< Delete this line when player ID is properly implemented
        elif (ext.lower() in ['.ym','.vtx','.vgz']):	# YM music
            data = ym.YMOpen(filename)
            if data != None:
                info= ym.YMGetMeta(data)
            player = 'x'
        else:
            subtune = -1

        while subtune > 0:
            if dialog == True:
                subtune = _DisplayCHIPInfo(conn, info)
            conn.SendTML('<SPINNER><CRSRL>')
            if player != "" and subtune > 0:
                _LOG("Playing "+filename+" subtune "+str(subtune-1)+" for "+str(ptime[subtune-1])+" seconds",id=conn.id,v=4)
                if ext.lower() == '.sid' and 'PET64' in conn.mode:
                    data = sd.SIDParser(filename,ptime[subtune-1]*info['speed'], order, subtune)
                elif ext.lower() == '.mus' and 'PET64' in conn.mode:
                    # Build a temporal .sid file
                    with open(filename, "rb") as fh:
                        with open(conn.bbs.Paths['temp']+'tmp0'+str(conn.id)+'.sid',"wb") as oh:
                            content = fh.read()
                            oh.write(b'PSID')   #Header
                            oh.write(b'\x00\x01') #Version
                            oh.write(b'\x00\x76') #Data offset
                            oh.write(b'\x09\x00') #Load Address
                            oh.write(b'\xec\x8f') #Init Address ($EC60)
                            oh.write(b'\xec\x80') #Play Address
                            oh.write(b'\x00\x01') #Default tune
                            oh.write(b'\x00\x01') #Max tune
                            oh.write(b'\x00\x00\x00\x01') #Flags
                            oh.write(b'\x00'*32*3) #Metadata
                            oh.write(content[2:])   #Music data
                            oh.write(b'\x00'*(0xe000-((len(content)-2)+0x900))) #padding
                            oh.write(sd.mus_driver[2:])
                            #oh.write(mus_driver[2:0xc6e+2]) #Player
                            #oh.write((0xa000).to_bytes(2,'little'))  #Music data address
                            #oh.write(mus_driver[0xc6e+4:]) #Player-cont     
                    data = sd.SIDParser(conn.bbs.Paths['temp']+'tmp0'+str(conn.id)+'.sid',math.ceil(ptime[0]*1.2), order)
                elif ext.lower() in ['.ym','.vtx','.vgz']:
                    if 'MSX' in conn.mode:
                        data = ym.YMParser(filename)
                    else:
                        data = sd.AYtoSID(filename)
                else:
                    data = []
                conn.Sendall(chr(TT.CMDON)+chr(TT.SIDSTREAM))
                count = 0
                #tt0 = time.time()
                for frame in data:
                    conn.Sendallbin(frame[0]) #Register count
                    conn.Sendallbin(frame[1]) #Register bitmap
                    conn.Sendallbin(frame[2]) #Register data
                    conn.Sendallbin(b'\xff')	 #Sync byte
                    count += 1

                    if count%100 == 0:
                        ack = b''
                        ack = conn.Receive(1)
                        count = 0
                        if (b'\xff' in ack) or not conn.connected:
                            #Abort stream
                            conn.Flush(1)   # Flush receive buffer for 1 second
                            # conn.socket.setblocking(0)	# Change socket to non-blocking
                            # t0 = time.time()
                            # while time.time()-t0 < 1:   # Flush receive buffer for 1 second
                            #     try:
                            #         conn.socket.recv(10)
                            #     except:
                            #         pass
                            # conn.socket.setblocking(1)	# Change socket to blocking
                            # conn.socket.settimeout(conn.bbs.TOut)
                            break
                    
                conn.Sendall(chr(0))	#End stream
                #conn.Receive(1)	#Receive last frame ack character
            if isinstance(info,bytes):
                subtune = -1
            elif info['subsongs'] == 1 or dialog == False:
                subtune = -1
            if not conn.connected:
                subtune = -1
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        _LOG(f'SIDStream error:{exc_type} on {fname} line {exc_tb.tb_lineno}',id=conn.id)
