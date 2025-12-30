from HersheyFonts import HersheyFonts
from math import pi,sin,cos
import numpy as np

import common.turbo56k as TT
from common.connection import Connection

the_font = HersheyFonts()
bbs_font = None

#####################################
# Draw a text using a vector font
# dir : 0 = 0 (normal left to right)
#       1 = 90
#       2 = 180
#       3 = 270
#       Clockwise
#####################################

############################
# Font list
#  0:
#  1: astrology
#  2: cursive
#  3: cyrilc_1
#  4: cyrillic
#  5: futuram
#  6: gothgbt
#  7: gothgrt
#  8: gothiceng
#  9: gothicger
# 10: 
def vectorText(conn:Connection, pen:int, x:int, y:int, font:int=0, size:int=8, text:str='', dir:int=0):
    global the_font, bbs_font
    if conn.QueryFeature(TT.LINE) < 0x80 or conn.QueryFeature(TT.PLOT) < 0x80:
        pen = pen & 0xff
        dir = dir % 4
        font = int(font if font <= len(the_font.default_font_names) else 0)

        the_font.load_default_font(the_font.default_font_names[font])
        my_font = the_font
        # if font > 0:
            # the_font.load_default_font(the_font.default_font_names[font-1])
            # my_font = the_font
        # else:
        #     if bbs_font == None:
        #         bbs_font = HersheyFonts()
        #         bbs_font.load_font_file('common/fifteen.jhf')
        #     my_font = bbs_font
        # the_font.normalize_rendering(size)
        scale_factor = float(size) / (my_font.render_options['bottom_line'] - my_font.render_options['cap_line'])
        my_font.render_options.scaley = scale_factor*(1 if dir in [0,3] else -1)
        my_font.render_options.scalex = scale_factor*(1 if dir in [0,1] else -1)
        my_font.render_options.yofs = my_font.render_options['bottom_line'] * scale_factor
        my_font.render_options.xofs = 0

        conn.Sendall(chr(TT.CMDON))
        x1p = x2p = y1p = y2p = -100000
        prev_coords = []
        for (x1,y1), (x2,y2) in my_font.lines_for_text(text):
            if dir in [0,2]:
                _x1 = int(x1+x).to_bytes(2,'little',signed=True)
                _y1 = int(y1+y).to_bytes(2,'little',signed=True)
                _x2 = int(x2+x).to_bytes(2,'little',signed=True)
                _y2 = int(y2+y).to_bytes(2,'little',signed=True)
            else:
                _x1 = int(y1+x).to_bytes(2,'little',signed=True)
                _y1 = int(x1+y).to_bytes(2,'little',signed=True)
                _x2 = int(y2+x).to_bytes(2,'little',signed=True)
                _y2 = int(x2+y).to_bytes(2,'little',signed=True)
            if (x1p == _x1) and (x2p == _x2) and (y1p == _y1) and (y2p == _y2): # skip
                continue
            if (_x1 == _x2) and (_y1 == _y2):   # dot
                if (_x1,_y1) not in prev_coords:
                    conn.Sendallbin(bytes([TT.PLOT,pen,_x1[0],_x1[1],_y1[0],_y1[1]]))
                else:
                    continue
            else:   # line
                conn.Sendallbin(bytes([TT.LINE,pen,_x1[0],_x1[1],_y1[0],_y1[1],_x2[0],_x2[1],_y2[0],_y2[1]]))
            x1p = _x1
            x2p = _x2
            y1p = _y1
            y2p = _y2
            prev_coords.append((_x1,_y1))
            prev_coords.append((_x2,_y2))
        conn.Sendall(chr(TT.CMDOFF))
        return True
    else:
        return False
    

###############################
# Draw a regular polygon
###############################
def polygon(conn:Connection, pen:int, x:int, y:int, r:int, sides:int=4, rot=0):
    if conn.QueryFeature(TT.LINE) < 0x80:
        pen = pen & 0xff
        rot = rot*(pi/180)
        steps = np.linspace(0,2*pi,sides+1)
        conn.Sendall(chr(TT.CMDON))
        x1 = sin(rot)*r
        y1 = cos(rot)*r
        for step in steps[1:]:
            x2 = sin(step+rot)*r
            y2 = cos(step+rot)*r
            _x1 = int(x1+x).to_bytes(2,'little',signed=True)
            _y1 = int(y1+y).to_bytes(2,'little',signed=True)
            _x2 = int(x2+x).to_bytes(2,'little',signed=True)
            _y2 = int(y2+y).to_bytes(2,'little',signed=True)
            conn.Sendallbin(bytes([TT.LINE,pen,_x1[0],_x1[1],_y1[0],_y1[1],_x2[0],_x2[1],_y2[0],_y2[1]]))
            x1 = x2
            y1 = y2
        conn.Sendall(chr(TT.CMDOFF))
        return True
    else:
        return False

###############################
# Draw a regular star
###############################
def star(conn:Connection, pen:int, x:int, y:int, r1:int, r2:int, sides:int=4, rot=0):
    if conn.QueryFeature(TT.LINE) < 0x80:
        sides = sides if sides >= 3 else 3
        pen = pen & 0xff
        rot = rot*(pi/180)
        steps = np.linspace(0,2*pi,(sides*2)+1)
        conn.Sendall(chr(TT.CMDON))
        x1 = sin(rot)*r2
        y1 = cos(rot)*r2
        r = (r1,r2)
        for i,step in enumerate(steps[1:]):
            x2 = sin(step+rot)*r[i%2]
            y2 = cos(step+rot)*r[i%2]
            _x1 = int(x1+x).to_bytes(2,'little',signed=True)
            _y1 = int(y1+y).to_bytes(2,'little',signed=True)
            _x2 = int(x2+x).to_bytes(2,'little',signed=True)
            _y2 = int(y2+y).to_bytes(2,'little',signed=True)
            conn.Sendallbin(bytes([TT.LINE,pen,_x1[0],_x1[1],_y1[0],_y1[1],_x2[0],_x2[1],_y2[0],_y2[1]]))
            x1 = x2
            y1 = y2
        conn.Sendall(chr(TT.CMDOFF))
        return True
    else:
        return False

##############
# TML tags
##############
t_mono = {	'STAR':(lambda c,pen,x,y,r1,r2,sides,rot:star(c,pen,x,y,r1,r2,sides,rot),[('c','_C'),('pen',1),('x',0),('y',0),('r1',50),('r2',20),('sides',5),('rot',0)]),
            'POLYGON':(lambda c,pen,x,y,r,sides,rot:polygon(c,pen,x,y,r,sides,rot),[('c','_C'),('pen',1),('x',0),('y',0),('r',50),('sides',4),('rot',45)]),
            'VECTORTXT':(lambda c,pen,x,y,font,size,text,dir:vectorText(c,pen,x,y,font,size,text,dir),[('c','_C'),('pen',1),('x',0),('y',0),('font',0),('size',8),('text',''),('dir',0)]),
            }
