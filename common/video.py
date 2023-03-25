####################################
#       Video file handling        #
####################################

import cv2
from PIL import Image
import common.filetools as FT
from random import randrange
from common.bbsdebug import _LOG,bcolors
import common.petscii as P
import common.turbo56k as TT
from common.connection import Connection

def Grabframe(conn:Connection,path, crop, length = None, pos = None):

	conn.Sendall(chr(P.YELLOW)+chr(P.COMM_B)+chr(P.CRSR_LEFT))
	loop = True
	if crop != None:
		crop = tuple([int(e) if e.isdigit() else 0 for e in crop.split(',')])
	try:
		capture = cv2.VideoCapture()
		capture.open(path)
	except:
		_LOG(bcolors.WARNING+"Error video file not found"+bcolors.ENDC,id=conn.id,v=1)
		conn.Sendall('...error'+chr(TT.CMDON)+chr(TT.CURSOR_EN)+chr(1)+chr(TT.CMDOFF)) #Enable cursor
		return()
	if length == None:
		fps = capture.get(cv2.CAP_PROP_FPS)      # OpenCV v2.x used "CV_CAP_PROP_FPS"
		if (frame_count := int(capture.get(cv2.CAP_PROP_FRAME_COUNT)))<= 0:
			length = 0 
		else:
			length = int(frame_count/fps)*1000

	while loop == True:
		cimg = None
		try:
			if length != 0.0:
				capture.set(cv2.CAP_PROP_POS_MSEC,pos if pos != None else randrange(0,length-1))
			else:
				capture.set(cv2.CAP_PROP_POS_MSEC,randrange(0,1000))

			ret, frame = capture.read()
			if ret:
				img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
				cimg = Image.fromarray(img)
				if crop != None:
					try:
						cimg = cimg.crop(crop)
					except:
						pass
			else:
				_LOG('Video grab plugin - '+bcolors.FAIL+'ERROR'+bcolors.ENDC,v=1)
		except Exception as e:
			print(e)
			_LOG(bcolors.WARNING+"Error grabbing video frame"+bcolors.ENDC,id=conn.id,v=1)
			conn.Sendall('...error'+chr(TT.CMDON)+chr(TT.CURSOR_EN)+chr(1)+chr(TT.CMDOFF)) #Enable cursor
			capture.release()
			cv2.destroyAllWindows()
			return()
		if cimg != None:
			FT.SendBitmap(conn,cimg)
			if conn.connected == False:
				return()
			_LOG("Waiting for a key to continue",id=conn.id,v=4)
			tecla = conn.ReceiveKey(b'\r_')
			if conn.connected == False:
				return()
			if tecla == b'_' or tecla == b'':
				loop = False
		else:
			conn.Sendall('...error'+chr(TT.CMDON)+chr(TT.CURSOR_EN)+chr(1)+chr(TT.CMDOFF)) #Enable cursor
			loop = False
			#return()
	capture.release()
	cv2.destroyAllWindows()
	conn.Sendall(chr(TT.CMDON)+chr(TT.CURSOR_EN)+chr(1)+chr(TT.CMDOFF)) #Enable cursor
	return(1)


