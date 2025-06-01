import common.turbo56k as TT
from common.connection import Connection

from math import sin, pi, sqrt
import numpy as np

###############
# Plugin setup
###############
def setup():
    fname = "3DGRAPH" #UPPERCASE function name for config.ini
    parpairs = [] #config.ini Parameter pairs (name,defaultvalue)
    return(fname,parpairs)


###################################
# Plugin function
###################################
def plugFunction(conn:Connection):

    valid = conn.QueryFeature(TT.LINE)|conn.QueryFeature(TT.HIRES)|conn.QueryFeature(TT.SCNCLR)
    if valid < 0x80:
        if 'PET' in conn.mode:
            scwidth = 320
            scheight = 200
        elif 'MSX' in conn.mode:
            scwidth = 256
            scheight = 192
        vx = [0]*150
        vy = [0]*150
        xmin = -4
        xmax = 4
        ymin = -4
        ymax = 4
        zmin = -1
        zmax = 1
        xsteps= np.linspace(xmin,xmax,16, endpoint=False)  #(xmax-xmin)/150
        xscale=20
        ysteps= np.linspace(ymin,ymax,16, endpoint=False)  #(ymax-ymin)/150
        yscale=20
        zscale=50
        _vx = 0
        _vy = 0
        xo = (scwidth/2)-(((xmax-xmin)*xscale)/2)   #100
        yo = (scheight/2)-(((ymax-ymin)*yscale)/2)   #50
        zo = 0

        pen0 = conn.encoder.colors.get('BLACK',1)
        pen1 = conn.encoder.colors.get('WHITE',1)
        conn.SendTML(f'<GRAPHIC><PENCOLOR pen=0 color={pen0}><PENCOLOR pen=1 color={pen1}><SCNCLR><CURSOR enable=False>')
        conn.Sendallbin(bytes([TT.CMDON]))

        my = 0
        for y in ysteps:
            i = 0
            for x in xsteps:
                z=sin(sqrt((x*x)+(y*y)))
                x1=xo+int((x-xmin)*xscale)
                y1=yo+int((y-ymin)*yscale)
                z1=zo+int((z-zmin)*zscale)
                xp=int(x1-z1*.3)
                yp=int(y1-z1*.5)
                if x == xsteps[0]:
                    _vy = yp
                    _vx = xp
                if y == ysteps[0]:
                    vy[i] = yp
                    vx[i] = xp
                _x1 = xp.to_bytes(2,'little',signed=True)
                _y1 = yp.to_bytes(2,'little',signed=True)
                _y2 = my.to_bytes(2,'little',signed=True)
                if yp < my:
                    conn.Sendallbin(bytes([TT.LINE,0,_x1[0],_x1[1],_y1[0],_y1[1],_x1[0],_x1[1],_y2[0],_y2[1]])) # linexp,yp,xp,199,0
                    # print(f'line(0,{xp},{yp},{xp},{my})')
                _x2 = vx[i].to_bytes(2,'little',signed=True)
                _y2 = vy[i].to_bytes(2,'little',signed=True)
                conn.Sendallbin(bytes([TT.LINE,1,_x1[0],_x1[1],_y1[0],_y1[1],_x2[0],_x2[1],_y2[0],_y2[1]]))# linexp,yp,vx(i),vy(i),1
                # print(f'line(1,{xp},{yp},{vx[i]},{vy[i]})')
                _x2 = _vx.to_bytes(2,'little',signed=True)
                _y2 = _vy.to_bytes(2,'little',signed=True)
                conn.Sendallbin(bytes([TT.LINE,1,_x1[0],_x1[1],_y1[0],_y1[1],_x2[0],_x2[1],_y2[0],_y2[1]]))# linexp,yp,vx,vy,1
                # print(f'line(1,{xp},{yp},{_vx},{_vy})')
                if yp > my:
                    my = yp
                vy[i] = yp
                vx[i] = xp
                _vy = yp
                _vx = xp
                i += 1
        conn.Sendallbin(bytes([TT.CMDOFF]))
        conn.ReceiveKey()
        conn.SendTML('<TEXT><CURSOR>')
        ...
    else:
        conn.SendTML('<FORMAT><CLR>ERROR: Your Terminal does not support drawing functions</FORMAT><PAUSE n=2>')
        return
    ...