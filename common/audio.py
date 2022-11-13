import sys
import time
import numpy
import re
import os
from os import walk
import random
import warnings
import subprocess
import signal

from common.bbsdebug import _LOG,bcolors
import common.helpers as H
import common.style as S
from common.connection import Connection
import common.petscii as P
import common.turbo56k as TT
import common.filetools as FT
from common.style import bbsstyle, default_style, RenderMenuTitle, KeyLabel


#Audio
try:
    import librosa
    wavs = True
except:
    wavs = False
#Audio Metadata
try:
    import mutagen
    meta = True
except:
    meta = False

#SIDStreaming
import common.siddumpparser as sd

#Ignore LibRosa filetype Warnings
warnings.filterwarnings("ignore", message="PySoundFile failed. Trying audioread instead.")


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
        MenuDic[b'<'] = (H.SetPage,(conn,page),'Previous Page',0,False)
        if conn.MenuParameters['current'] == pages-1:
            page = 0
        else:
            page = conn.MenuParameters['current']+1
        MenuDic[b'>'] = (H.SetPage,(conn,page),'Next Page',0,False)

    for x in range(start, end + 1, 1):
        afunc = PlayAudio
        KeyLabel(conn, H.valid_keys[x-start],(audios[x][:len(P.toPETSCII(audios[x]))-4]+' '*30)[:30]+' ', x % 2)
        if (wavs == True) and (audios[x].endswith(wext)):
            conn.Sendall(chr(P.COMM_B)+chr(P.CRSR_LEFT))
            if meta == True and (audios[x])[-4:] != '.wav' and (audios[x])[-4:] != '.WAV':
                #Load metadata
                audio = mutagen.File(path+audios[x], easy = True)
                tsecs = int(audio.info.length)
            else:
                #Load and compute audio playtime
                y, sr = librosa.load(path+audios[x], sr = None, mono= True)
                tsecs = int(librosa.get_duration(y=y, sr=sr))
            tmins = int(tsecs / 60)
            length[x] = tsecs
            tsecs = tsecs - (tmins * 60)
        else:	#SID file
            afunc = SIDStream
            tstr = None
            if os.path.isfile(path+(audios[x])[:-3]+'ssl') == True:
                tf = open(path+(audios[x])[:-3]+'ssl')
                tstr = tf.read()
                tf.close()
            elif os.path.isfile(path+'SONGLENGTHS/'+(audios[x])[:-3]+'ssl') == True:
                tf = open(path+(audios[x])[:-3]+'ssl')
                tstr = tf.read()
                tf.close()
            if tstr != None:
                tmins = int(hex(ord(tstr[0]))[2:])
                tsecs = int(hex(ord(tstr[1]))[2:])
                length[x] = (tmins*60)+tsecs # Playtime for the 1st subtune
            else:
                length[x] = 60*3
                tmins = 3
                tsecs = 0

        conn.Sendall(chr(P.WHITE)+('00'+str(tmins))[-2:]+':'+('00'+str(tsecs))[-2:]+'\r')
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

# Display audio dialog
def _AudioDialog(conn:Connection, data):
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
def PlayAudio(conn:Connection,filename, length = 60.0, dialog=False):
    bnoise = b'\x10\x01'
    CHUNK = 16384

    conn.socket.settimeout(conn.bbs.TOut+length)	#<<<< This might be pointless
    _LOG('Timeout set to:'+bcolors.OKGREEN+str(length)+bcolors.ENDC+' seconds',id=conn.id,v=3)
    if filename[-4:] == '.raw' or filename[-4:] == '.RAW':
        conn.Sendall(chr(255) + chr(161) + '..enviando,')
        time.sleep(1)
        # Select screen output
        conn.Sendall(chr(255) + chr(160))
        # Send selected raw audio
        _LOG('Sending RAW audio: '+filename,id=conn.id,v=3)
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
        _LOG('Sending audio: '+filename,id=conn.id,v=3)

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
                        conn.socket.setblocking(1)
                        binario = b''
                        _LOG('USER CANCEL',id=conn.id,v=3)
                        streaming = False
                        break
                except:
                    pass
                conn.socket.setblocking(1)
                binario = b''
            #time.sleep(0.60)    #Dont send all the stream at once. Untested for 7680Hz
            while time.time()-t1 < (conn.samplerate/CHUNK): #This method should work for all samplerates
                pass                                        #and with different host performances
        binario += b'\x00\x00\x00\x00\x00\x00\xFE'
        t = time.time() - t0
        pcm_stream.stop()
        _LOG('Stream completed in '+bcolors.OKGREEN+str(round(t,2))+bcolors.ENDC+' seconds',id=conn.id,v=4)
    conn.Sendallbin(binario)
    time.sleep(1)
    #conn.Sendall(chr(P.DELETE))
    conn.socket.settimeout(conn.bbs.TOut)
    
# PcmStream Class
# Receive an audio stream through FFMPEG
class PcmStream:
    def __init__(self, fn, sr):
        self.pcm_stream = subprocess.Popen(["ffmpeg", "-i", fn, "-loglevel", "panic", "-vn", "-ac", "1", "-ar", str(sr), "-dither_method", "modified_e_weighted", "-f", "s16le", "pipe:1"],
                        stdout=subprocess.PIPE, preexec_fn=os.setsid)

    def read(self, size):
        try:
            a = self.pcm_stream.stdout.read(size)
            na = numpy.frombuffer(a, dtype=numpy.short)
            #nl = na[::2]
            #nr = na[1::2]
            na = na/32768
            numpy.clip(na,-1,1,na)
            
            norm = librosa.mu_compress(na,mu=15, quantize=True)
            #norm = norm*2048
            norm = norm +8

            bin8 = numpy.uint8(norm)

            #norm = norm.astype(numpy.short)
            return bin8
        except StopIteration:
            return b""
    
    def stop(self):
        self.pcm_stream.stdout.flush()
        self.pcm_stream.send_signal(signal.SIGINT)
        self.pcm_stream.terminate()
        #os.killpg(self.pcm_stream.pid, signal.SIGKILL)



def _DisplaySIDInfo(conn:Connection, info):
    minutes = int(info['songlength']/60)
    seconds = info['songlength']- (minutes*60)
    conn.Sendall(chr(P.CLEAR)+chr(P.GREY3)+chr(P.RVS_ON)+chr(TT.CMDON))
    for y in range(0,10):
        conn.Sendall(chr(TT.LINE_FILL)+chr(y)+chr(160))
    conn.Sendall(chr(TT.CMDOFF)+chr(P.GREY1)+TT.Fill_Line(10,226)+chr(P.GREY3))
    # text = format40('\r Titulo: '+info['title']+'\r Artista: '+info['artist']+'\r Copyright: '+info['copyright']+'\r Duracion: '+ ('00'+str(minutes))[-2:]+':'+('00'+str(seconds))[-2:]+'\r\r pRESIONE return PARA REPRODUCIR\r cUALQUIER TECLA PARA DETENER\r')
    # for line in text:
    # 	conn.Sendall(chr(P.RVS_ON)+line+'\r')
    conn.Sendall(chr(P.CRSR_DOWN)+' tITLE: '+H.formatX(info['title'])[0][0:30]+'\r')
    conn.Sendall(chr(P.RVS_ON)+' aRTIST: '+H.formatX(info['artist'])[0][0:29]+'\r')
    conn.Sendall(chr(P.RVS_ON)+' cOPYRIGHT: '+H.formatX(info['copyright'])[0][0:27]+'\r')
    conn.Sendall(chr(P.RVS_ON)+' pLAYTIME: '+ ('00'+str(minutes))[-2:]+':'+('00'+str(seconds))[-2:]+'\r')
    conn.Sendall(chr(P.RVS_ON)+chr(P.CRSR_DOWN)+" pRESS return TO PLAY\r"+chr(P.RVS_ON)+" aNY KEY TO STOP"+chr(P.RVS_OFF))

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

def SIDStream(conn:Connection, filename,ptime, dialog=True):

    V1f = '\x00\x01'    #Voice 1 Frequency
    V1p = '\x02\x03'    #Voice 1 Pulse Width
    V1c = '\x04'        #Voice 1 Control
    V1e = '\x05\x06'    #Voice 1 Envelope
    
    V2f = '\x07\x08'    #Voice 2 Frequency
    V2p = '\x09\x0a'    #Voice 2 Pulse Width
    V2c = '\x0b'        #Voice 2 Control
    V2e = '\x0c\x0d'    #Voice 2 Envelope

    V3f = '\x0e\x0f'    #Voice 3 Frequency
    V3p = '\x10\x11'    #Voice 3 Pulse Width
    V3c = '\x12'        #Voice 3 Control
    V3e = '\x13\x14'    #Voice 3 Envelope

    Fco = '\x15\x16'    #Filter Cutoff Frequency
    Frs = '\x17'        #Filter Resonance
    Vol = '\x18'        #Filter and Volume Control

    player = ""
    order = 0
    with open(filename, "rb") as fh:
        content = fh.read()
        if dialog == True:
            info = {}
            info['type'] = (content[:4].decode("iso8859-1"))
            info['version'] = (content[5])
            info['subsongs'] = (content[15])
            info['startsong'] = (content[17])
            info['title'] = (content[22:54].decode('iso8859-1')).strip(chr(0))
            info['artist'] = (content[54:86].decode('iso8859-1')).strip(chr(0))
            info['copyright'] = (content[86:118].decode('iso8859-1')).strip(chr(0))
            info['songlength'] = ptime
            _DisplaySIDInfo(conn, info)
            conn.ReceiveKey()
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

    if player != "":
        data = sd.SIDParser(filename,ptime, order)
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
                    break	#Abort stream
            
        conn.Sendall(chr(0))	#End stream
        #conn.Receive(1)	#Receive last frame ack character
