import urllib

import time
#import pafy
import streamlink
import yt_dlp

import sys
import random
import re
from multiprocessing import Queue   #was from queue
import threading
import asyncio
import requests
import validators
from PIL import Image, ImageDraw
from io import BytesIO
from html import unescape, escape

from common.bbsdebug import _LOG,bcolors
from common import connection
from common.helpers import formatX
from common import helpers as H
from common import audio as AA
from common.imgcvt import convert_To, cropmodes, PreProcess, gfxmodes, dithertype, get_ColorIndex
from common.filetools import SendBitmap

### User Agent string used for some stingy content sources
hdrs = {'User-Agent':'Mozilla/5.0 (X11; Linux x86_64; rv:87.0) Gecko/20100101 Firefox/87.0'}


# This class left unused until a blocking problem somewhere can be resolved
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
            self.streams[key] = [AA.PcmStream(url,rate),{id:Queue()},chunk,False]   #Create new FFMPEG stream with url as key, a Queue for id, and the chunk size
            self.refresh = True
        else:                           #if url already in dict
            self.streams[key][1][id] = Queue()  #Just add a Queue for id to the url key
            self.refresh = True
        if len(self.streams) == 1:  #If True, we just added the first stream, we need to start the StreamThread
            self.sthread = threading.Thread(target = self.StreamThread, args = ())
            self.sthread.start()
        # if (1<<int(rate*1.5).bit_length()) > self.CHUNK:
        #     self.CHUNK = 1<<int(rate*1.5).bit_length()
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
                    self.sthread.join()         #Finish the StreamThread
        #self.lock.release()

    # Multi user streaming thread
    # (yes my naming standards are all over the place)
    def StreamThread(self):
        async def get_chunk(stream):
            if stream[3] == False:
                stream[3] = True
                print('reading:',stream[2])
                data = await stream[0].read(stream[2])    #Get data from FFMPEG stream
                for id in stream[1]:    #Iterate thru Queues
                    stream[1][id].put(data, False)        #Push data into the Queue
                print('done:',stream[2])
                stream[3] = False

        async def loop(streams):
            # tasks = []
            for url in streams:    #Iterate thru streams
                asyncio.ensure_future(get_chunk(streams[url]))
                # tasks.append(get_chunk(streams[url]))
                # data = S[url][0].read(S[url][2])    #Get data from FFMPEG stream
                # for id in S[url][1]:    #Iterate thru Queues
                #     S[url][1][id].put(data, False)        #Push data into the Queue
            # await asyncio.gather(*tasks)
            # print('---')

        l = asyncio.new_event_loop()

        while len(self.streams) > 0:

            #self.lock.acquire()
            S = self.streams    #.copy()
            l.run_until_complete(loop(S))
            time.sleep(0.5)

            # tasks = []
            # for url in S:    #Iterate thru streams
            #     tasks.append(get_chunk(S[url]))
                # data = S[url][0].read(S[url][2])    #Get data from FFMPEG stream
                # for id in S[url][1]:    #Iterate thru Queues
                #     S[url][1][id].put(data, False)        #Push data into the Queue
            # asyncio.gather(*tasks)
            #self.lock.release()
        l.close()


slsession = None
# AStreams = AudioStreams()

###############
# Plugin setup
###############
def setup():
    global slsession
    fname = "WEBAUDIO" #UPPERCASE function name for config.ini
    parpairs = [('url',"http://relay4.slayradio.org:8000/"),('image',''),('title','')] #config.ini Parameter pairs (name,defaultvalue)
    slsession = streamlink.Streamlink()
    return(fname,parpairs)

##################################################
# Plugin function
##################################################
def plugFunction(conn:connection.Connection,url,image,title):
    #_LOG('Sending audio',id=conn.id)
    CHUNK = 16384
    bnoise = b'\x10\x01\x11'
    conn.SendTML('<PAUSE n=1><SPINNER><CRSRL>')

    #Streaming mode
    binario = b'\xFF\x83'

    if title != '':
        title += '\n'
    sURL = None
    sTitle = None
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
    # Pafy failed, try with streamlink
    # streamlink lacks metadata functionality

    if sURL == None:
        try:
            req = urllib.request.Request(url)
            req.add_header('Icy-MetaData', '1')
            req.add_header('User-Agent', 'WinAmp/5.565')
            req.timeout = 15
            req_data = urllib.request.urlopen(req)
            if req_data.msg != 'OK':
                _LOG("WebAudio -"+bcolors.FAIL+" ERROR"+bcolors.ENDC,id=conn.id,v=1)
                return
            sURL = url
            _LOG("WebAudio - Now streaming from Icecast/Shoutcast: "+req_data.getheader('icy-name'),id=conn.id,v=3)
            #logo = 'plugins/shoutlogo.png'
            sTitle = formatX(title+'Shoutcast Stream: '+req_data.getheader('icy-name'),conn.encoder.txt_geo[0])
        except:
            sURL = None
    if sURL == None and '.m3u' not in url:
        try:
            sURL,sTitle = ytdlp_resolve(conn,url,title)
        except:
            sURL = None
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
                        sTitle = formatX(title+source+' Stream ',conn.encoder.txt_geo[0])
                        break
            except:
                _LOG("WebAudio -"+bcolors.FAIL+" ERROR"+bcolors.ENDC,id=conn.id,v=1)
                return
        else:
            _LOG("WebAudio -"+bcolors.FAIL+" ERROR"+bcolors.ENDC,id=conn.id,v=1)
            return
    if sURL == None:
        _LOG("WebAudio -"+bcolors.FAIL+" ERROR"+bcolors.ENDC,id=conn.id,v=1)
        return
    #try to open image if any
    img = None
    if image != '':
        im = None
        if validators.url(image):
            try:
                data = requests.get(image, allow_redirects=True, headers=hdrs, timeout=10)
                im = Image.open(BytesIO(data.content))
            except:
                pass
        else:
            try:
                im = Image.open(image)
            except:
                pass
        if im != None:
            im.thumbnail((128,128))
            # im.show()
            if conn.mode == "PET64":
                gm = gfxmodes.C64HI
            elif conn.mode == "PET264":
                gm = gfxmodes.P4HI
            else:
                gm = conn.encoder.def_gfxmode
            img = convert_To(im, cropmode=cropmodes.LEFT, preproc=PreProcess(contrast=1.5,saturation=1.5), gfxmode=gm)
    #Display info
    if img != None:
        c_black = (0,0,0)
        c_white = (0xff,0xff,0xff)
        c_yellow = (0xff,0xff,0x55)
        pwidth = img[0].size[0]
        pheight = img[0].size[1]
        draw = ImageDraw.Draw(img[0])
        # Fill unused space with black
        draw.rectangle([0,0,128,(pheight-128)//2],fill = c_black)
        draw.rectangle([0,((pheight-128)//2)+128,128,pheight],fill = c_black)
        draw.rectangle([128,0,pwidth,pheight],fill = c_black)
        y = 2
        for l in sTitle:
            l = unescape(l.replace('<BR>',''))
            draw.text((pwidth//2,y),H.gfxcrop(l,pwidth,H.font_bold),c_white,font=H.font_bold,anchor='mt')
            y += 16
        draw.text((pwidth//2,pheight-32),"Press <RETURN> to play",c_white,font=H.font_text,anchor='mt')
        if 'MSX' in conn.mode:
            draw.text((pwidth//2,pheight-20),"Press <STOP> and wait to stop",c_yellow,font=H.font_text,anchor='mt')
            draw.text((pwidth//2,pheight-8),"Press <X> to cancel",c_yellow,font=H.font_text,anchor='mt')
        else:
            draw.text((pwidth//2,pheight-20),"Press <X> and wait to stop or cancel",c_yellow,font=H.font_text,anchor='mt')
        #draw.text((136,168),"or cancel",c_yellow,font=H.font_text)
        SendBitmap(conn,img[0],gfxmode=gm,preproc=PreProcess(),dither=dithertype.NONE)
    else:
        conn.SendTML(f'<TEXT border={conn.encoder.colors["BLUE"]} background={conn.encoder.colors["BLUE"]}><CLR><YELLOW>')
        for l in sTitle:
            conn.SendTML(l)
        conn.SendTML(f'<BR><BR>Press <KPROMPT t=RETURN><YELLOW> to start<BR>')
        if 'MSX' in conn.mode:
            conn.SendTML(f'<BR>Press <KPROMPT t=STOP><YELLOW> to stop<BR><KPROMPT t=X><YELLOW> to cancel<BR>')
        else:
            conn.SendTML(f'<BR>Press <KPROMPT t=X><YELLOW> to stop/cancel<BR>')

    if conn.ReceiveKey('\rx') == 'x':
        return

    conn.SendTML('<SPINNER><CRSRL>')

    #pcm_stream,skey = AStreams.new(sURL,conn.samplerate, conn.id)
    pcm_stream = AA.PcmStream(sURL,conn.samplerate)
    CHUNK = 1<<int(conn.samplerate*1.5).bit_length()
    t0 = time.time()
    streaming = True
    while streaming == True:
        t1 = time.time()
        try:
            audio = asyncio.run(pcm_stream.read(CHUNK))   #pcm_stream.get(True, 15)
        except:
            audio = []
        t2 = time.time()-t1
        if t2 > 15:
            streaming = False
        a_len = len(audio)
        if a_len == 0:
            streaming = False
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
        ts = ((CHUNK/conn.samplerate)-(time.time()-t1))*0.95
        time.sleep(ts if ts>=0 else 0)
    binario += b'\x00\x00\x00\x00\x00\x00\xFE'
    t = time.time() - t0
    pcm_stream.stop()
    #AStreams.delete(skey,conn.id)
    _LOG('Stream completed in '+bcolors.OKGREEN+str(round(t,2))+bcolors.ENDC+' seconds',id=conn.id,v=4)
    conn.Sendallbin(binario)
    time.sleep(1)
    conn.socket.settimeout(conn.bbs.TOut)

def ytdlp_resolve(conn,url,title):
    sURL = None
    sTitle = None
    ydl_opts = {'quiet':False, 'socket_timeout':15}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        sTitle = formatX(title+info['webpage_url_domain']+': '+info['title'],conn.encoder.txt_geo[0])
        formats = info['formats']
        for f in formats:
            if f['resolution'] == 'audio only':
                sURL = f['url']
                break
            elif f.get('acodec',None) != 'none':
                sURL = f['url']
                break
    return sURL,sTitle