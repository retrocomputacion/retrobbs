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

from common.bbsdebug import _LOG,bcolors
import common.helpers as H
import common.style as S
from common.connection import Connection
import common.petscii as P
import common.turbo56k as TT
import common.filetools as FT
from common.style import bbsstyle, default_style, RenderMenuTitle, KeyLabel


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

    # Start with barebones MenuDic
    MenuDic = { 
                b'_': (H.MenuBack,(conn,),"Previous Menu",0,False),
                b'\r': (AudioList,(conn,title,speech,logtext,path),title,0,False)
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

    filefilter = ('.sid', '.SID', '.mus', '.MUS')
    if wavs == True:
        filefilter = filefilter + wext

    #Filters only the files matching 'filefilter'
    for f in files:
        if f.endswith(filefilter):
            audios.append(f)


    audios.sort()	#Sort list

    #for t in range(0,len(audios)):
    #	length.append(0.0)
    length = [0.0]*len(audios)	#Audio length list

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
        MenuDic[b'<'] = (H.SetPage,(conn,page),'Previous Page',0,False)
        if conn.MenuParameters['current'] == pages-1:
            page = 0
        else:
            page = conn.MenuParameters['current']+1
        MenuDic[b'>'] = (H.SetPage,(conn,page),'Next Page',0,False)

    row = 3
    for x in range(start, end + 1, 1):
        afunc = PlayAudio
        bname = os.path.splitext(os.path.basename(audios[x]))[0]
        KeyLabel(conn, H.valid_keys[x-start],(bname)[:30]+' ', x % 2)
        if (wavs == True) and (audios[x].endswith(wext)):
            conn.Sendall(TT.set_CRSR(34,row)+chr(P.COMM_B)+chr(P.CRSR_LEFT))
            tsecs = _GetPCMLength(path+audios[x])
            tmins = int(tsecs / 60)
            length[x] = int(tsecs)
            tsecs = tsecs - (tmins * 60)
        else:	#SID file
            conn.Sendall(TT.set_CRSR(34,row)+chr(P.COMM_B)+chr(P.CRSR_LEFT))
            afunc = SIDStream
            tsecs = _GetSIDLength(path+audios[x])
            tmins = int(tsecs[0] / 60)
            length[x] = tsecs
            tsecs = tsecs[0] - (tmins * 60)
        conn.Sendall(chr(P.WHITE)+('00'+str(tmins))[-2:]+':'+('00'+str(tsecs))[-2:]+'\r')
        row += 1
        #Add keybinding to MenuDic
        MenuDic[H.valid_keys[x-start].encode('ascii','ignore')] = (afunc,(conn,path+audios[x],length[x],True),H.valid_keys[x-start],0,False)
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

#########################################
# Display audio dialog
#########################################
def _AudioDialog(conn:Connection, data):
    S.RenderDialog(conn, 15, data['title'])
    if data['album'] != '':
        conn.Sendall(chr(P.RVS_ON)+' aLBUM:\r'+chr(P.RVS_ON)+' '+P.toPETSCII(data['album'])+'\r\r')
    if data['artist'] != '':
        conn.Sendall(chr(P.RVS_ON)+' aRTIST:\r'+chr(P.RVS_ON)+' '+P.toPETSCII(data['artist'])+'\r\r')
    conn.Sendall(chr(P.RVS_ON)+' lENGTH: '+data['length']+'\r\r')
    conn.Sendall(chr(P.RVS_ON)+' fROM '+data['sr']+' TO '+str(conn.samplerate)+'hZ')
    conn.Sendall(TT.set_CRSR(0,12)+' pRESS <return> TO PLAY\r')
    conn.Sendall(chr(P.RVS_ON)+' pRESS <X> AND WAIT TO STOP\r')
    conn.Sendall(chr(P.RVS_ON)+' pRESS <_> TO CANCEL')
    if conn.ReceiveKey(b'\r_') == b'_':
        conn.Sendall(chr(P.COMM_B)+chr(P.CRSR_LEFT))
        return False
    return True

###########################################
# Get audio length for PCM file in seconds
###########################################
def _GetPCMLength(filename):
    if meta == True and filename[-4:] != '.wav' and filename[-4:] != '.WAV':
        #Load metadata
        audio = mutagen.File(filename, easy = True)
        tsecs = int(audio.info.length)
    else:
        #Load and compute audio playtime
        with audioread.audio_open(filename) as f:
            tsecs = int(f.duration)
    return tsecs

######################################################################
#Send Audio file
######################################################################
def PlayAudio(conn:Connection,filename, length = 60.0, dialog=False):
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
        a_meta['sr'] = str(a_data.info.sample_rate)+'hZ'
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
        if not _AudioDialog(conn,a_meta):
            return()
        if not conn.connected:
            return()
        conn.Sendall(chr(P.COMM_B)+chr(P.CRSR_LEFT))


    #Streaming mode
    binario = b'\xFF\x83'

    pcm_stream = PcmStream(filename,conn.samplerate)

    t0 = time.time()

    streaming = True
    t_samples = length * conn.samplerate # Total number of samples for the selected playtime
    c_samples = 0   # Sample counter

    while streaming == True:
        t1 = time.time()
        audio = pcm_stream.read(CHUNK)
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
        if c_samples >= t_samples:  # Finish streaming if number of samples equals or exceed playtime
            streaming = False

        #time.sleep(0.60)    #Dont send all the stream at once. Untested for 7680Hz
        time.sleep((CHUNK/conn.samplerate)*0.9)
        #while streaming and (time.time()-t1 < (CHUNK/conn.samplerate)): #This method should work for all samplerates
        #    pass                                        #and with different host performances
    binario += b'\x00\x00\x00\x00\x00\x00\xFE'
    t = time.time() - t0
    pcm_stream.stop()
    _LOG('Stream completed in '+bcolors.OKGREEN+str(round(t,2))+bcolors.ENDC+' seconds',id=conn.id,v=4)
    conn.Sendallbin(binario)
    time.sleep(1)
    #conn.Sendall(chr(P.DELETE))
    conn.socket.settimeout(conn.bbs.TOut)

#########################################    
# PcmStream Class
# Receive an audio stream through FFMPEG
#########################################
class PcmStream:
    def __init__(self, fn, sr):
        # self.pcm_stream = subprocess.Popen(["ffmpeg", "-i", fn, "-loglevel", "panic", "-vn", "-ac", "1", "-ar", str(sr), "-dither_method", "modified_e_weighted", "-f", "s16le", "pipe:1"],
        #                 stdout=subprocess.PIPE, preexec_fn=os.setsid)
        self.pcm_stream = subprocess.Popen(["ffmpeg", "-i", fn, "-loglevel", "panic", "-vn", "-ac", "1", "-ar", str(sr), "-dither_method", "modified_e_weighted", "-af", "acrusher=bits=4:mode=lin,acontrast=contrast=50", "-f", "u8", "pipe:1"],
                        stdout=subprocess.PIPE, preexec_fn=os.setsid)
 
    def read(self, size):
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

##################################
# Get SID playtimes from ssl file
##################################
def _GetSIDLength(filename):
    tstr = None
    if os.path.isfile(filename[:-3]+'ssl') == True:
        tf = open(filename[:-3]+'ssl')
        tstr = tf.read()
        tf.close()
    elif os.path.isfile(os.path.dirname(filename)+'/SONGLENGTHS/'+os.path.basename(filename)[:-3]+'ssl') == True:
        tf = open(os.path.dirname(filename)+'/SONGLENGTHS/'+os.path.basename(filename)[:-3]+'ssl')
        tstr = tf.read()
        tf.close()
    if tstr != None:
        length = []
        for i in range(0,len(tstr),2):
            tmins = int(hex(ord(tstr[i]))[2:])
            tsecs = int(hex(ord(tstr[i+1]))[2:])
            length.append((tmins*60)+tsecs) # Playtime for the 1st subtune
    else:
        length = [60*3]
    
    return length

############################################
# Display SID info dialog
############################################
def _DisplaySIDInfo(conn:Connection, info):
    
    def calctime():
        m = int(info['songlength'][subtune-1]/60)
        return m,info['songlength'][subtune-1]- (m*60)

    if isinstance(info,dict):
        subtune = info['startsong']
        minutes, seconds = calctime()
        S.RenderDialog(conn,12)
        conn.Sendall(chr(P.CRSR_DOWN)+' tITLE: '+H.formatX(info['title'])[0][0:30]+'\r')
        conn.Sendall(chr(P.RVS_ON)+' aRTIST: '+H.formatX(info['artist'])[0][0:29]+'\r')
        conn.Sendall(chr(P.RVS_ON)+' cOPYRIGHT: '+H.formatX(info['copyright'])[0][0:27]+'\r')
        conn.Sendall(chr(P.RVS_ON)+' pLAYTIME: '+ str(minutes).zfill(2)+':'+str(seconds).zfill(2)+'\r')
        if info['subsongs'] > 1:    #Subtune
            conn.Sendall(chr(P.RVS_ON)+chr(P.CRSR_DOWN)+' sUBTUNE: '+chr(P.GREY2)+'<'+chr(P.WHITE)+chr(P.RVS_OFF)+str(subtune).zfill(2)+chr(P.RVS_ON)+chr(P.GREY2)+'>'+chr(P.GREY3)+'\r')
        conn.Sendall(chr(P.RVS_ON)+chr(P.CRSR_DOWN)+" pRESS _ TO EXIT\r"+chr(P.RVS_ON)+" return TO PLAY\r"+chr(P.RVS_ON)+" aNY KEY TO STOP"+chr(P.RVS_OFF))
        conn.Sendall(TT.disable_CRSR())
        while True and conn.connected:
            k = conn.ReceiveKey(b'<>_\r')
            if k == b'_':
                subtune = -1
                break
            elif k == b'\r':
                break
            elif k == b'<' and subtune > 1:
                subtune -= 1
                minutes, seconds = calctime()
                conn.Sendall(chr(P.RVS_OFF)+TT.set_CRSR(11,6)+chr(P.WHITE)+str(subtune).zfill(2))
                conn.Sendall(chr(P.RVS_ON)+TT.set_CRSR(11,4)+chr(P.GREY3)+str(minutes).zfill(2)+':'+str(seconds).zfill(2))
            elif k == b'>' and subtune < info['subsongs']:
                subtune += 1
                minutes, seconds = calctime()
                conn.Sendall(chr(P.RVS_OFF)+TT.set_CRSR(11,6)+chr(P.WHITE)+str(subtune).zfill(2))
                conn.Sendall(chr(P.RVS_ON)+TT.set_CRSR(11,4)+chr(P.GREY3)+str(minutes).zfill(2)+':'+str(seconds).zfill(2))
    else:
        subtune = 1
        conn.Sendall(chr(P.CLEAR)+chr(P.ENABLE_CBMSHIFT)+chr(P.TOUPPER))
        conn.Sendallbin(info)
        conn.Sendall(chr(P.YELLOW)+'\rPRESS RETURN TO PLAY\r_ TO EXIT\rANY KEY TO STOP')
        conn.Sendall(TT.disable_CRSR())
        if conn.ReceiveKey(b'_\r') == b'_':
            subtune = -1
    conn.Sendall(TT.enable_CRSR())
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

#############################################################
# Stream SID/MUS files
#############################################################
def SIDStream(conn:Connection, filename,ptime, dialog=True, _subtune=None):

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

    tmp,ext = os.path.splitext(filename)

    if ptime == None:
        ptime = _GetSIDLength(filename)
    elif not isinstance(ptime,list):
        ptime = [ptime]
    try:
        with open(filename, "rb") as fh:
            content = fh.read()
            if (ext == '.sid') or (ext == '.SID'):
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
            elif (ext == '.mus') or (ext == '.MUS'):
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

        while subtune > 0:
            if dialog == True:
                subtune = _DisplaySIDInfo(conn, info)
            conn.Sendall(chr(P.COMM_B)+chr(P.CRSR_LEFT))
            if player != "" and subtune > 0:
                _LOG("Playing "+filename+" subtune "+str(subtune-1)+" for "+str(ptime[subtune-1])+" seconds",id=conn.id,v=4)
                if (ext == '.sid') or (ext == '.SID'):
                    data = sd.SIDParser(filename,ptime[subtune-1]*info['speed'], order, subtune)
                elif (ext == '.mus') or (ext == '.MUS'):
                    # Build a .sid file
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
                            conn.socket.setblocking(0)	# Change socket to non-blocking
                            try:
                                t0 = time.time()
                                while time.time()-t0 < 1:   # Flush receive buffer for 1 second
                                    conn.socket.recv(10)
                            except:
                                pass
                            conn.socket.setblocking(1)	# Change socket to blocking
                            conn.socket.settimeout(conn.bbs.TOut)
                            break
                    
                conn.Sendall(chr(0))	#End stream
                #conn.Receive(1)	#Receive last frame ack character
            if isinstance(info,bytes):
                subtune = -1
            elif info['subsongs'] == 1 or dialog == False:
                subtune = -1
            if not conn.connected:
                subtune = -1
    except:
        pass
