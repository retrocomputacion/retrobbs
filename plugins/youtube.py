####################################
#          YouTube Plugin          #
####################################

import cv2
import numpy as np
from common.bbsdebug import _LOG,bcolors
from common import turbo56k as TT
from common.connection import Connection
from common import video as VV
import streamlink
import yt_dlp

##################
# Plugin setup
##################
def setup():
    fname = "GRABYT"    # UPPERCASE function name for config.ini
    parpairs = [('url',"https://www.youtube.com/watch?v=46kn3thI-Mo"),('crop',None)]    # config.ini Parameter pairs (name,defaultvalue)
    return(fname,parpairs)

#####################
# Plugin function
#####################
def plugFunction(conn:Connection,url, crop):

    if conn.QueryFeature(TT.BLKTR) >= 0x80:
        conn.SendTML('<BR>Terminal not compatible...<PAUSE n=3>')
        return
    conn.SendTML('<YELLOW><SPINNER>')
    best = None
    title = ''
    if crop != None:
        crop = tuple([int(e) if e.isdigit() else 0 for e in crop.split(',')])

    tmsecs = None
    slsession = streamlink.Streamlink()
    ydl_opts = {'quiet':True, 'socket_timeout':15, 'listformats':True}
    cookies = conn.bbs.PlugOptions.get('ytcookies','')
    if cookies != '':
        ydl_opts['cookiefile'] = cookies
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats',None)
            if formats != None:
                crop = None # Don't use crop parameters, we dont know the dimensions of the video returned by Streamlink
                try:
                    res = 320*200   # Hardcoded pixel count
                    for f in formats:
                        if f['resolution'] not in ['none','audio only']:
                            if eval(f['resolution'].replace('x','*')) >= res:
                                best = f['url']
                                break
                    tmsecs = None
                except Exception as e:
                    best = None
    except:
        best = None
    if best == None:
        try:
            stl = slsession.resolve_url(url)
            source = stl[0]
            if source != "":
                crop = None # Don't use crop parameters, we dont know the dimensions of the video returned by Streamlink
                tmsecs = None
                plug = stl[1](slsession,url)	# Create plugin object
                pa = plug.streams()
                for k in ['240p','360p','480p','720p','1080p','144p']:
                    s = pa.get(k,None)
                    if s != None:
                        if type(s) == streamlink.stream.MuxedStream:
                            best = s.substreams[0].url # Index 0 seems to always be the video stream
                            break
                        elif type(s) == streamlink.stream.HLSStream:
                            best = s.url_master
                            break
                        else:
                            best = s.url
                            break
        except Exception as e:
            pass
    if best in [None,'']:
        _LOG(bcolors.WARNING+"YouTube: Video not found"+bcolors.ENDC,id=conn.id,v=1)
        conn.SendTML('...error<CURSOR>')
        return
    conn.SendTML(f'<TEXT border={conn.encoder.colors["BLUE"]} background={conn.encoder.colors["BLUE"]}><CLR>'
                 f'<BR><BR>Press <KPROMPT t=RETURN><YELLOW> for a new image<BR>'
                 f'<BR>Press <KPROMPT t=_><YELLOW> to exit<BR>')
    back = conn.encoder.decode(conn.encoder.back)
    if conn.ReceiveKey(back + conn.encoder.nl) == back:
        return
    return(VV.Grabframe(conn,best,crop,tmsecs))

#######################
# Adjust image gamma
#######################
def adjust_gamma(image, gamma=1.0):
    # build a lookup table mapping the pixel values [0, 255] to
    # their adjusted gamma values
    invGamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** invGamma) * 255
        for i in np.arange(0, 256)]).astype("uint8")
    # apply gamma correction using the lookup table
    return cv2.LUT(image, table)

