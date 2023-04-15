####################################
#          YouTube Plugin          #
####################################

import pafy
import cv2
import numpy as np
from common.bbsdebug import _LOG,bcolors
import common.petscii as P
import common.turbo56k as TT
from common.connection import Connection
import common.video as VV
import streamlink

#############################
#Plugin setup
def setup():
    fname = "GRABYT" #UPPERCASE function name for config.ini
    parpairs = [('url',"https://www.youtube.com/watch?v=46kn3thI-Mo"),('crop',None)] #config.ini Parameter pairs (name,defaultvalue)
    return(fname,parpairs)
#############################

##########################################
#Plugin callable function
def plugFunction(conn:Connection,url, crop):

	conn.Sendall(chr(P.YELLOW)+chr(P.COMM_B)+chr(P.CRSR_LEFT))#"yOUTUBE"
	loop = True
	if crop != None:
		crop = tuple([int(e) if e.isdigit() else 0 for e in crop.split(',')])

	try:
		video = pafy.new(url)
		tmsecs = video.length*1000
		best = video.getbestvideo()
		if best == None:
			best = video.getbest()
	except:
		_LOG(bcolors.WARNING+"YouTube: PAFY failed trying with Streamlinks"+bcolors.ENDC,id=conn.id,v=1)
		#conn.Sendall('...error'+chr(TT.CMDON)+chr(TT.CURSOR_EN)+chr(1)+chr(TT.CMDOFF)) #Enable cursor
		#return()
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
				pa = slsession.streams(url)
				for k in list(pa.keys()):
					s = pa[k]
					try:
						best = s.url
					except:
						best = None
					if best != None:
						break
				tmsecs = None
			except:
				_LOG(bcolors.WARNING+"YouTube: Video not found"+bcolors.ENDC,id=conn.id,v=1)
				conn.Sendall('...error'+TT.enable_CRSR()) #Enable cursor
				return()

	return(VV.Grabframe(conn,best,crop,tmsecs))


def adjust_gamma(image, gamma=1.0):
	# build a lookup table mapping the pixel values [0, 255] to
	# their adjusted gamma values
	invGamma = 1.0 / gamma
	table = np.array([((i / 255.0) ** invGamma) * 255
		for i in np.arange(0, 256)]).astype("uint8")
	# apply gamma correction using the lookup table
	return cv2.LUT(image, table)

