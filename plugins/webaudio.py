import urllib
import subprocess

import librosa
import numpy as np
import time
import pafy

import sys

import common.petscii as P
import common.turbo56k as TT
from common.bbsdebug import _LOG,bcolors
import common.connection
import common.filetools as FT
from common.helpers import formatX
from common.style import KeyPrompt

#p = pyaudio.PyAudio()

#stream = p.open(format=pyaudio.paInt16,channels=1,rate=11520,output=True)

#############################
#Plugin setup
def setup():
    fname = "WEBAUDIO" #UPPERCASE function name for config.ini
    parpairs = [('url',"http://relay4.slayradio.org:8000/")] #config.ini Parameter pairs (name,defaultvalue)
    return(fname,parpairs)
#############################

##########################################
#Plugin callable function

#Send Audio file
def plugFunction(conn,url):
    time.sleep(1)
    #_LOG('Sending audio',id=conn.id)
    CHUNK = 16384

    conn.Sendall(chr(P.COMM_B)+chr(P.CRSR_LEFT))

    #Streaming mode
    binario = b'\xFF\x83'

    try:
        pa = pafy.new(url)
        s= pa.streams[0]
        sURL = s.url
        _LOG("WebAudio - Now streaming from YouTube: "+pa.title,id=conn.id)
        #logo = 'plugins/youtubelogo.png'
        sTitle = formatX('YouTube Stream: '+pa.title)
    except:
        sURL = None
    if sURL == None:
        try:
            req = urllib.request.Request(url)
            req.add_header('Icy-MetaData', '1')
            req.add_header('User-Agent', 'WinAmp/5.565')
            req_data = urllib.request.urlopen(req)
            #print(req_data.headers)
            if req_data.msg != 'OK':
                _LOG("WebAudio -"+bcolors.FAIL+" ERROR"+bcolors.ENDC,id=conn.id)
                return
            sURL = url
            _LOG("WebAudio - Now streaming from Icecast/Shoutcast: "+req_data.getheader('icy-name'),id=conn.id)
            #logo = 'plugins/shoutlogo.png'
            sTitle = formatX('Shoutcast Stream: '+req_data.getheader('icy-name'))
        except:
            _LOG("WebAudio -"+bcolors.FAIL+" ERROR"+bcolors.ENDC,id=conn.id)
            return

    #Display info
    #FT.SendBitmap(conn,logo,9,False,False,False)
    #conn.Sendall(TT.split_Screen(9,False,0,0))
    conn.Sendall(TT.to_Text(0,6,6)+chr(P.CLEAR)+chr(P.YELLOW))
    for l in sTitle:
        conn.Sendall(l)
        if len(l)<40:
            conn.Sendall('\r')
    conn.Sendall('\r\rpRESS '+KeyPrompt('return')+chr(P.YELLOW)+' TO START\r')
    conn.Sendall('\rpRESS '+KeyPrompt('x')+chr(P.YELLOW)+' TO STOP\r')

    conn.ReceiveKey()
    #conn.Sendall(TT.split_Screen(0,False,0,0)+chr(P.CLEAR))


    audioP = subprocess.Popen(["ffmpeg", "-i", sURL, "-loglevel", "panic", "-vn", "-ac", "1", "-ar", str(conn.samplerate), "-dither_method", "modified_e_weighted", "-f", "s16le", "pipe:1"],
                            stdout=subprocess.PIPE)
    pcm_stream = MiniaudioDecoderPcmStream(audioP,conn.samplerate)

    t0 = time.time()

    streaming = True

    while streaming == True:
        t1 = time.time()
        audio = pcm_stream.read(CHUNK)
        t2 = time.time()-t1
        if t2 > 15:
            streaming = False
        a_len = len(audio)
        print(a_len)
        for b in range(0,a_len,2):
            lnibble = int(audio[b])
            if lnibble == 0:
                lnibble = 1
            if b+1 <= a_len:
                hnibble = int(audio[b+1])
            else:
                hnibble = 0
            binario += (lnibble+(16*hnibble)).to_bytes(1,'big')

            conn.Sendallbin(binario)
            sys.stderr.flush()
            #Check for terminal cancelation
            conn.socket.setblocking(0)	# Change socket to non-blocking
            try:
                hs = conn.socket.recv(1)
                if hs == b'\xff':
                    conn.socket.setblocking(1)
                    binario = b''
                    _LOG('USER CANCEL',id=conn.id)
                    streaming = False
                    break
            except:
                pass
            conn.socket.setblocking(1)
            binario = b''

    binario += b'\x00\x00\x00\x00\x00\x00\xFE'
    t = time.time() - t0
    audioP.terminate()
    #print(bcolors.ENDC)
    #print('['+str(conn.id)+'] ',datetime.datetime.now().isoformat(sep=' ', timespec='milliseconds'),'Stream completed in '+bcolors.OKGREEN+str(t)+bcolors.ENDC+' seconds')	#This one cannot be replaced by _LOG()... yet
    _LOG('Stream completed in '+bcolors.OKGREEN+str(round(t,2))+bcolors.ENDC+' seconds',id=conn.id)
    conn.Sendallbin(binario)
    time.sleep(1)
    conn.socket.settimeout(60*5)    #Needs access to _tout



class MiniaudioDecoderPcmStream:
    def __init__(self, stream, sr):
        self.pcm_stream = stream

    def read(self, size):
        try:
            a = self.pcm_stream.stdout.read(size)
            na = np.frombuffer(a, dtype=np.short)
            #nl = na[::2]
            #nr = na[1::2]
            na = na/32768
            np.clip(na,-1,1,na)
            #print(na.max())
            
            norm = librosa.mu_compress(na,mu=15, quantize=True)
            #norm = norm*2048
            norm = norm +8

            bin8 = np.uint8(norm)

            #norm = norm.astype(np.short)
            return bin8
        except StopIteration:
            return b""

