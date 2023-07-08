####################################
#       Video file handling        #
####################################

import cv2
import subprocess
import io
from PIL import Image
from common import filetools as FT
from random import randrange
from common.bbsdebug import _LOG,bcolors
from common.connection import Connection

def Grabframe(conn:Connection,path, crop, length = None, pos = None):

    conn.SendTML('<YELLOW><CBM-B><CRSRL>')
    loop = True
    # try:
    # 	capture = cv2.VideoCapture()
    # 	capture.open(path)
    # except:
    # 	_LOG(bcolors.WARNING+"Error video file not found"+bcolors.ENDC,id=conn.id,v=1)
    # 	conn.SendTML('...ERROR<CURSOR>')
    # 	return()
    if length == None:
        # fps = capture.get(cv2.CAP_PROP_FPS)      # OpenCV v2.x used "CV_CAP_PROP_FPS"
        # frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) 
        # if frame_count<= 0:
        # 	length = 0 
        # else:
        # 	length = int((frame_count/fps)*1000)
        process = subprocess.run(['ffprobe', path, '-v', 'quiet', '-show_entries' ,'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1'], 
                         stdout=subprocess.PIPE, 
                         universal_newlines=True)
        try:
            length = int(float(process.stdout)*1000)
        except:
            length = 0

    while True:
        cimg = None
        try:
            if length != 0.0:
                fpos = pos if pos != None else randrange(0,length-1)
                #capture.set(cv2.CAP_PROP_POS_MSEC,pos if pos != None else randrange(0,length-1))
            else:
                fpos = randrange(0,1000)
                #capture.set(cv2.CAP_PROP_POS_MSEC,randrange(0,1000))

            process = subprocess.run(['ffmpeg', '-loglevel', 'panic', '-ss', str(fpos)+'ms', '-i', path, '-frames:v', '1', '-c:v' ,'png', '-f', 'image2pipe', 'pipe:1' ], 
                         stdout=subprocess.PIPE, 
                         universal_newlines=False)
            
            #print(process.stdout)
            pic = io.BytesIO(process.stdout)
            try:
                cimg = Image.open(pic)
                if crop != None:
                    try:
                        cimg = cimg.crop(crop)
                    except:
                        pass
            except:
                cimg = None



            #ret, frame = capture.read()
            # if ret:
            # 	img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # 	cimg = Image.fromarray(img)
            # 	if crop != None:
            # 		try:
            # 			cimg = cimg.crop(crop)
            # 		except:
            # 			pass
            # else:
            # 	_LOG('Video grab - '+bcolors.FAIL+'ERROR'+bcolors.ENDC,v=1)
        except Exception as e:
            print(e)
            _LOG(bcolors.WARNING+"Error grabbing video frame"+bcolors.ENDC,id=conn.id,v=1)
            conn.SendTML('...ERROR<CURSOR>') #Enable cursor
            # capture.release()
            # cv2.destroyAllWindows()
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
                break
        else:
            _LOG(bcolors.WARNING+"Error grabbing video frame"+bcolors.ENDC,id=conn.id,v=1)
            conn.SendTML('...ERROR<CURSOR>') #Enable cursor
            break
            #return()
    # capture.release()
    # cv2.destroyAllWindows()
    conn.SendTML('<CURSOR>') #Enable cursor
    return(1)


t_mono = {'GRABFRAME':(lambda c,path:Grabframe(c,path,None),[('c','_C'),('path','')])}