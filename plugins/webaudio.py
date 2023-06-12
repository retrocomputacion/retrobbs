import urllib

import time
#import pafy
import streamlink

import sys
import random
import re
from queue import Queue
import threading

from common.bbsdebug import _LOG,bcolors
from common import connection
from common.helpers import formatX
from common import audio as AA



class AudioStreams:
    def __init__(self) -> None:
        self.streams = {}
        self.sthread = None
        self.refresh = False
        #self.lock = threading.Lock()
        self.CHUNK = 16384

    def new(self, url, rate, id):
        #self.lock.acquire()
        key = str([url,rate])    # Generate url+samplerate dictionary key
        if not(key in self.streams):    #If url not in dict
            chunk = 1<<int(rate*1.5).bit_length()
            self.streams[key] = [AA.PcmStream(url,rate),{id:Queue()},chunk]   #Create new FFMPEG stream with url as key, a Queue for id, and the chunk size
            self.refresh = True
        else:                           #if url already in dict
            self.streams[key][1][id] = Queue()  #Just add a Queue for id to the url key
            self.refresh = True

        if len(self.streams) == 1:  #If True, we just added the first stream, we need to start the StreamThread
            self.sthread = threading.Thread(target = self.StreamThread, args = ())
            self.sthread.start()

        self.CHUNK = 1<<int(rate*1.4).bit_length()  # <remove me

        #self.lock.release()
        return self.streams[key][1][id],key

    def delete(self, key, id):
        #self.lock.acquire()
        if key in self.streams:
            self.streams[key][1].pop(id)        #Remove the Queue for id
            self.refresh = True
            if len(self.streams[key][1]) == 0:  #If no more users
                self.streams[key][0].stop()     #stop FFMPEG stream
                self.streams.pop(key)           #remove URL from dict
                if len(self.streams) == 0:      # No more streams
                    self.sthread.join()             #Finish the StreamThread
        #self.lock.release()


    # Multi user streaming thread
    # (yes my naming standards are all over the place)
    def StreamThread(self):

        while len(self.streams) > 0:
            #self.lock.acquire()
            S = self.streams.copy()
            for url in S:    #Iterate thru streams
                data = S[url][0].read(S[url][2])    #Get data from FFMPEG stream
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
def plugFunction(conn:connection.Connection,url):
    #_LOG('Sending audio',id=conn.id)
    CHUNK = 16384
    bnoise = b'\x10\x01\x11'
    conn.SendTML('<PAUSE n=1><CBM-B><CRSRL>')

    #Streaming mode
    binario = b'\xFF\x83'


    # PAFY support commented out for now. Waiting for development to restart or confirmation of its demise
    # try:
    #     pa = pafy.new(url)
    #     s= pa.streams[0]
    #     sURL = s.url
    #     _LOG("WebAudio - Now streaming from YouTube: "+pa.title,id=conn.id,v=3)
    #     #logo = 'plugins/youtubelogo.png'
    #     sTitle = formatX('YouTube Stream: '+pa.title)
    # except:
    #     sURL = None
    sURL = None
    # Pafy failed, try with streamlink
    # streamlink lacks metadata functionality
    if sURL == None:
        try:
            stl = slsession.resolve_url(url)
            source = stl[0]
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
    conn.SendTML(f'<TEXT border={conn.encoder.colors["BLUE"]} background={conn.encoder.colors["BLUE"]}><CLR><YELLOW>')
    for l in sTitle:
        conn.SendTML(l)
    conn.SendTML(f'<BR><BR>Press <KPROMPT t=RETURN><YELLOW> to start<BR>'
                 f'<BR>Press <KPROMPT t=X><YELLOW> to stop/cancel<BR>')

    if conn.ReceiveKey(b'\rX') == b'X':
        return

    conn.SendTML('<CBM-B><CRSRL>')

    pcm_stream,skey = AStreams.new(sURL,conn.samplerate, conn.id)

    t0 = time.time()

    streaming = True

    while streaming == True:
        t1 = time.time()
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
            if b+1 <= a_len:
                hnibble = int(audio[b+1])
            else:
                hnibble = 0
            binario += (lnibble+(16*hnibble)).to_bytes(1,'big')

            conn.Sendallbin(re.sub(b'\\x00', lambda x:bnoise[random.randint(0,2)].to_bytes(1,'little'), binario))
            streaming = conn.connected
            sys.stderr.flush()
            #Check for terminal cancelation
            conn.socket.setblocking(0)	# Change socket to non-blocking
            try:
                hs = conn.socket.recv(1)
                if hs == b'\xff':
                    binario = b''
                    try:
                        t3 = time.time()
                        while time.time()-t3 < 1:   # Flush receive buffer for 1 second
                            conn.socket.recv(10)
                    except:
                        pass
                    _LOG('USER CANCEL',id=conn.id,v=3)
                    streaming = False
                    conn.socket.setblocking(1)
                    break
            except:
                pass
            conn.socket.setblocking(1)
            binario = b''

    binario += b'\x00\x00\x00\x00\x00\x00\xFE'
    t = time.time() - t0
    #pcm_stream.stop()
    AStreams.delete(skey,conn.id)
    _LOG('Stream completed in '+bcolors.OKGREEN+str(round(t,2))+bcolors.ENDC+' seconds',id=conn.id,v=4)
    conn.Sendallbin(binario)
    time.sleep(1)
    conn.socket.settimeout(conn.bbs.TOut)

