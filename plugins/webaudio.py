import urllib

import time
import pafy
import streamlink

import sys
import random
import re
from queue import Queue
import threading

import common.petscii as P
import common.turbo56k as TT
from common.bbsdebug import _LOG,bcolors
import common.connection
import common.filetools as FT
from common.helpers import formatX
from common.style import KeyPrompt
import common.audio as AA



class AudioStreams:
    def __init__(self) -> None:
        self.streams = {}
        self.sthread = None
        self.refresh = False
        #self.lock = threading.Lock()

    def new(self, url, rate, id):
        #self.lock.acquire()
        if not(url in self.streams):    #If url not in dict
            self.streams[url] = [AA.PcmStream(url,rate),{id:Queue()}]   #Create new FFMPEG stream with url as key, and a Queue for id
            self.refresh = True
        else:                           #if url already in dict
            self.streams[url][1][id] = Queue()  #Just add a Queue for id to the url key
            self.refresh = True

        if len(self.streams) == 1:  #If True, we just added the first stream, we need to start the StreamThread
            self.sthread = threading.Thread(target = self.StreamThread, args = ())
            self.sthread.start()

        #self.lock.release()
        return self.streams[url][1][id]

    def delete(self, url, id):
        #self.lock.acquire()
        if url in self.streams:
            self.streams[url][1].pop(id)        #Remove the Queue for id
            self.refresh = True
            if len(self.streams[url][1]) == 0:  #If no more users
                self.streams[url][0].stop()     #stop FFMPEG stream
                self.streams.pop(url)           #remove URL from dict
                if len(self.streams) == 0:      # No more streams
                    self.sthread.join()             #Finish the StreamThread
        #self.lock.release()


    # Multi user streaming thread
    # (yes my naming standards are all over the place)
    def StreamThread(self):
        CHUNK = 16384

        while len(self.streams) > 0:
            #self.lock.acquire()
            S = self.streams.copy()
            for url in S:    #Iterate thru streams
                data = S[url][0].read(CHUNK)    #Get data from FFMPEG stream
                for id in S[url][1]:    #Iterate thru Queues
                    S[url][1][id].put(data)        #Push data into the Queue
            #self.lock.release()


slsession = None
AStreams = AudioStreams()

#############################
#Plugin setup
def setup():
    global slsession
    fname = "WEBAUDIO" #UPPERCASE function name for config.ini
    parpairs = [('url',"http://relay4.slayradio.org:8000/")] #config.ini Parameter pairs (name,defaultvalue)
    slsession = streamlink.Streamlink()
    return(fname,parpairs)
#############################

##########################################
#Plugin callable function

#Send Audio file
def plugFunction(conn:common.connection.Connection,url):
    time.sleep(1)
    #_LOG('Sending audio',id=conn.id)
    CHUNK = 16384

    bnoise = b'\x10\x01'

    conn.Sendall(chr(P.COMM_B)+chr(P.CRSR_LEFT))

    #Streaming mode
    binario = b'\xFF\x83'

    try:
        pa = pafy.new(url)
        s= pa.streams[0]
        sURL = s.url
        _LOG("WebAudio - Now streaming from YouTube: "+pa.title,id=conn.id,v=3)
        #logo = 'plugins/youtubelogo.png'
        sTitle = formatX('YouTube Stream: '+pa.title)
    except:
        sURL = None
    # Pafy failed, try with streamlink
    # streamlink lacks metadata functionality
    if sURL == None:
        try:
            stl = slsession.resolve_url(url)
            source = stl[0].__name__
        except:
            source = ""
        if source != "":
            try:
                pa = slsession.streams(url)
                for k in list(pa.keys()):
                    s = pa[k]
                    try:
                        sURL = s.url
                    except:
                        sURL = None
                    if sURL != None:
                        _LOG("WebAudio - Now streaming from "+source, id=conn.id,v=3)
                        sTitle = formatX(source+' Stream')
                        break
            except:
                sURL = None
    #streamlink failed try icecast/shoutcast
    if sURL == None:
        try:
            req = urllib.request.Request(url)
            req.add_header('Icy-MetaData', '1')
            req.add_header('User-Agent', 'WinAmp/5.565')
            req_data = urllib.request.urlopen(req)
            if req_data.msg != 'OK':
                _LOG("WebAudio -"+bcolors.FAIL+" ERROR"+bcolors.ENDC,id=conn.id,v=1)
                return
            sURL = url
            _LOG("WebAudio - Now streaming from Icecast/Shoutcast: "+req_data.getheader('icy-name'),id=conn.id,v=3)
            #logo = 'plugins/shoutlogo.png'
            sTitle = formatX('Shoutcast Stream: '+req_data.getheader('icy-name'))
        except:
            _LOG("WebAudio -"+bcolors.FAIL+" ERROR"+bcolors.ENDC,id=conn.id,v=1)
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
    conn.Sendall('\rpRESS '+KeyPrompt('x')+chr(P.YELLOW)+' TO STOP/CANCEL\r')

    if conn.ReceiveKey(b'\rX') == b'X':
        return
    #conn.Sendall(TT.split_Screen(0,False,0,0)+chr(P.CLEAR))


    #pcm_stream = AA.PcmStream(sURL,conn.samplerate)
    pcm_stream = AStreams.new(sURL,conn.samplerate, conn.id)

    t0 = time.time()

    streaming = True

    while streaming == True:
        t1 = time.time()
        #audio = pcm_stream.read(CHUNK)
        try:
            audio = pcm_stream.get(True, 15)
        except:
            audio = []
        t2 = time.time()-t1
        if t2 > 15:
            streaming = False
        a_len = len(audio)
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

    binario += b'\x00\x00\x00\x00\x00\x00\xFE'
    t = time.time() - t0
    #pcm_stream.stop()
    AStreams.delete(sURL,conn.id)
    _LOG('Stream completed in '+bcolors.OKGREEN+str(round(t,2))+bcolors.ENDC+' seconds',id=conn.id,v=4)
    conn.Sendallbin(binario)
    time.sleep(1)
    conn.socket.settimeout(conn.bbs.TOut)

