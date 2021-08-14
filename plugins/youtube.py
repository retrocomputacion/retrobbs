####################################
#          YouTube Plugin          #
####################################

import pafy
import cv2
from PIL import Image
import numpy as np
from common.c64cvt import c64imconvert
import common.filetools as FT
from random import randrange
from common.bbsdebug import _LOG,bcolors
import common.petscii as P
import common.turbo56k as TT

#############################
#Plugin setup
def setup():
    fname = "GRABYT" #UPPERCASE function name for config.ini
    parpairs = [('url',"https://www.youtube.com/watch?v=46kn3thI-Mo"),('crop',None)] #config.ini Parameter pairs (name,defaultvalue)
    return(fname,parpairs)
#############################

##########################################
#Plugin callable function
def plugFunction(conn,url, crop):

	conn.Sendall(chr(P.YELLOW)+chr(P.COMM_B)+chr(P.CRSR_LEFT))#"yOUTUBE"
	loop = True
	while loop == True:
		try:
			cimg = YTframe(url,crop)
		except:
			_LOG(bcolors.WARNING+"Error connecting to YouTube"+bcolors.ENDC,id=conn.id)
			conn.Sendall('...error'+chr(TT.CMDON)+chr(TT.CURSOR_EN)+chr(1)+chr(TT.CMDOFF)) #Enable cursor
			return()

		FT.SendBitmap(conn,cimg)
		if conn.connected == False:
			return()
		_LOG("Waiting for a key to continue",id=conn.id)
		tecla = conn.ReceiveKey(b'\r_')
		if conn.connected == False:
			return()
		if tecla == b'_' or tecla == b'':
			loop = False
	conn.Sendall(chr(TT.CMDON)+chr(TT.CURSOR_EN)+chr(1)+chr(TT.CMDOFF)) #Enable cursor
	return(1)


def adjust_gamma(image, gamma=1.0):
	# build a lookup table mapping the pixel values [0, 255] to
	# their adjusted gamma values
	invGamma = 1.0 / gamma
	table = np.array([((i / 255.0) ** invGamma) * 255
		for i in np.arange(0, 256)]).astype("uint8")
	# apply gamma correction using the lookup table
	return cv2.LUT(image, table)

def YTframe(url = "https://www.youtube.com/watch?v=46kn3thI-Mo",crop = None, method=0):
    
    im_pil = None

    video = pafy.new(url)

    tmsecs = video.length*1000

    #print(tmsecs)

    best = video.getbest(preftype="mp4")

    capture = cv2.VideoCapture()
    capture.open(best.url)


    if tmsecs != 0.0:
        capture.set(cv2.CAP_PROP_POS_MSEC,randrange(0,tmsecs-1))

    ret, frame = capture.read()
    if ret:
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        #img = adjust_gamma(img, 1.2)
        im_pil = Image.fromarray(img)
        if crop != None:
            im_pil = im_pil.crop(crop)
    else:
        _LOG('YouTube plugin - '+bcolors.FAIL+'ERROR'+bcolors.ENDC)
    capture.release()
    cv2.destroyAllWindows()
    return(im_pil)
