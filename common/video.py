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


######################################################################
# Grab a video frame from either a local file or an online source
######################################################################
def Grabframe(conn:Connection,path, crop, length = None, pos = None):

    conn.SendTML('<YELLOW><SPINNER><CRSRL>')
    if length == None:
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
            else:
                fpos = randrange(0,1000)
            process = subprocess.run(['ffmpeg', '-loglevel', 'panic', '-ss', str(fpos)+'ms', '-i', path, '-frames:v', '1', '-c:v' ,'png', '-f', 'image2pipe', 'pipe:1' ], 
                         stdout=subprocess.PIPE, 
                         universal_newlines=False)
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
        except Exception as e:
            print(e)
            _LOG(bcolors.WARNING+"Error grabbing video frame"+bcolors.ENDC,id=conn.id,v=1)
            conn.SendTML('...ERROR<CURSOR>') #Enable cursor
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
    conn.SendTML('<CURSOR>') #Enable cursor
    return(1)

##########
# TML tag
##########
t_mono = {'GRABFRAME':(lambda c,path:Grabframe(c,path,None),[('c','_C'),('path','')])}