####################################
#          YouTube Plugin          #
####################################

#import pafy
import cv2
import numpy as np
from common.bbsdebug import _LOG,bcolors
from common import turbo56k as TT
from common.connection import Connection
from common import video as VV
import streamlink

###############
# Plugin setup
###############
def setup():
    fname = "GRABYT" #UPPERCASE function name for config.ini
    parpairs = [('url',"https://www.youtube.com/watch?v=46kn3thI-Mo"),('crop',None)] #config.ini Parameter pairs (name,defaultvalue)
    return(fname,parpairs)

#############################################
# Plugin function
#############################################
def plugFunction(conn:Connection,url, crop):

    conn.SendTML('<YELLOW><SPINNER><CRSRL>')
    best = ''
    if crop != None:
        crop = tuple([int(e) if e.isdigit() else 0 for e in crop.split(',')])

    # PAFY support commented out for now. Waiting for development to restart or confirmation of its demise
    # try:
    # 	video = pafy.new(url)
    # 	tmsecs = video.length*1000
    # 	best = video.getbestvideo()
    # 	if best == None:
    # 		best = video.getbest()
    # except:
    # 	_LOG(bcolors.WARNING+"YouTube: PAFY failed trying with Streamlinks"+bcolors.ENDC,id=conn.id,v=1)
    # 	#conn.Sendall('...error'+chr(TT.CMDON)+chr(TT.CURSOR_EN)+chr(1)+chr(TT.CMDOFF)) #Enable cursor
    # 	#return()
    # 	video = None
    video = None
    if video == None:
        slsession = streamlink.Streamlink()
        try:
            stl = slsession.resolve_url(url)
            source = stl[0]
        except:
            source = ""
        if source != "":
            crop = None #Don't use crop parameters, we dont know the dimensions of the video returned by Streamlink
            try:
                plug = stl[1](slsession,url)	#Create plugin object
                pa = plug.streams()	#slsession.streams(url)
                for k in ['240p','360p','480p','720p','1080p','144p']:
                    s = pa.get(k,None)
                    #s = pa[k]
                    if s != None:
                        if type(s) == streamlink.stream.MuxedStream:
                            best = s.substreams[0].url #Index 0 seems to always be the video stream
                            break
                        else:
                            best = s.url
                            break
                    # try:
                    # 	best = s.url
                    # except:
                    # 	best = None
                    # if best != None:
                    # 	break
                tmsecs = None
            except Exception as e:
                _LOG(bcolors.WARNING+"YouTube: Video not found"+bcolors.ENDC,id=conn.id,v=1)
                conn.Sendall('...error'+TT.enable_CRSR()) #Enable cursor
                return
    conn.SendTML(f'<TEXT border={conn.encoder.colors["BLUE"]} background={conn.encoder.colors["BLUE"]}><CLR>'
                 f'<BR><BR>Press <KPROMPT t=RETURN><YELLOW> for a new image<BR>'
                 f'<BR>Press <KPROMPT t=_><YELLOW> to exit<BR>')
    if conn.ReceiveKey(b'\r_') == b'_':
        return
    return(VV.Grabframe(conn,best,crop,tmsecs))

####################################
# Adjust image gamma
####################################
def adjust_gamma(image, gamma=1.0):
    # build a lookup table mapping the pixel values [0, 255] to
    # their adjusted gamma values
    invGamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** invGamma) * 255
        for i in np.arange(0, 256)]).astype("uint8")
    # apply gamma correction using the lookup table
    return cv2.LUT(image, table)

