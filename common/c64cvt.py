import cv2
import numpy as np
import math
import sys
from PIL import Image, ImageEnhance, ImageStat
import hitherdither
import os
import datetime as dt
import colorsys
import random

PaletteRGB = [[0x00,0x00,0x00],[0xff,0xff,0xff],[0x81,0x33,0x38],[0x75,0xce,0xc8],[0x8e,0x3c,0x97],[0x56,0xac,0x4d],[0x2e,0x2c,0x9b],[0xed,0xf1,0x71],
    [0x8e,0x50,0x29],[0x55,0x33,0x00],[0xc4,0x6c,0x71],[0x4a,0x4a,0x4a],[0x7b,0x7b,0x7b],[0xa9,0xff,0x9f],[0x70,0x6d,0xeb],[0xb2,0xb2,0xb2]]

PaletteHither = hitherdither.palette.Palette([0x000000,0xffffff,0x813338,0x75cec8,0x8e3c97,0x56ac4d,0x2e2c9b,0xedf171,
    0x8e5029,0x553300,0xc46c71,0x4a4a4a,0x7b7b7b,0xa9ff9f,0x706deb,0xb2b2b2])

#bgcolor = 12

#Image crop and resize
def frameResize(i_image):
    i_ratio = i_image.size[0] / i_image.size[1]
    dst_ratio = 320/200

    if dst_ratio > i_ratio:
        i_image = i_image.resize((320,320*i_image.size[1]//i_image.size[0]), Image.ANTIALIAS)
        box = (0,(i_image.size[1]-200)/2,i_image.size[0],(i_image.size[1]+200)/2)
        i_image = i_image.crop(box)
    elif dst_ratio < i_ratio:
        i_image = i_image.resize((200*i_image.size[0]//i_image.size[1],200),Image.ANTIALIAS)
        box = ((i_image.size[0]-320)/2,0,(i_image.size[0]+320)/2,i_image.size[1])
        i_image = i_image.crop(box)

    return(i_image)

#HiRes
def get2closest(colors):
    cd = [[0 for j in range(16)] for i in range(len(colors))]

    #print(cd)
    closest = []
    indexes = 0
    for x in range(0,len(colors)):
        for y in range(0,16):
            rd = colors[x][1][0] - PaletteRGB[y][0]
            gd = colors[x][1][1] - PaletteRGB[y][1]
            bd = colors[x][1][2] - PaletteRGB[y][2]
            cd[x][y] = math.sqrt(rd * rd + gd * gd + bd * bd)
        m = PaletteRGB[cd[x].index(min(cd[x]))]
        closest.append(m[2]+m[1]*256+m[0]*65536)
        indexes += cd[x].index(min(cd[x]))<<(4*x)
    if len(closest) == 1:
        closest.append(closest[0])
    #print(closest)
    return(indexes,hitherdither.palette.Palette(closest))

#Multicolor
def get4closest(colors, bgcolor):
    cd = [[0 for j in range(16)] for i in range(len(colors))]

    brgb = PaletteRGB[bgcolor][2]+PaletteRGB[bgcolor][1]*256+PaletteRGB[bgcolor][0]*65536
    closest = [brgb,0x0,0x0,0x813338]

    #Attr
    indexes = 0#0x33
    cram = 2

    #Find least used color
    if len(colors) >= 4:
        c_counts = [colors[i][0] for i in range(len(colors))]
        bi = c_counts.index(min(c_counts))
    else:
        bi = 5

    xx = 1
    for x in range(0,len(colors)):
        if x == bi:
            continue
        for y in range(0,16):
            rd = colors[x][1][0] - PaletteRGB[y][0]
            gd = colors[x][1][1] - PaletteRGB[y][1]
            bd = colors[x][1][2] - PaletteRGB[y][2]
            cd[x][y] = math.sqrt(rd * rd + gd * gd + bd * bd)
        m = PaletteRGB[cd[x].index(min(cd[x]))]
        closest[xx] = m[2]+m[1]*256+m[0]*65536
        if xx < 3:
            indexes += cd[x].index(min(cd[x]))<<(4*(1-(xx-1)))
        else:
            cram = cd[x].index(min(cd[x]))
        xx += 1
    #if len(closest) == 1:
    #    closest.append(closest[0])
    #print(closest)

    return(indexes,cram,hitherdither.palette.Palette(closest))

def packmulticolor(cell):
    out = b''
    for y in range(8):
        tbyte = 0
        for x in range(4):
            tbyte += int(cell[y,x])<<((3-x)*2)
        out+= tbyte.to_bytes(1,'big')
    return(out)


######################################
def c64imconvert(Source, gfxmode = 1):

    tstPic = Source.convert('RGB')

    o_img = frameResize(tstPic)

    stat = ImageStat.Stat(o_img)

    r,g,b = stat.rms
    perbright = math.sqrt(0.241*(r**2) + 0.691*(g**2) + 0.068*(b**2))

    if perbright < 25:
        perbright = 25
    elif perbright > 128:
        perbright = 128

    #Saturation
    tmpImg = o_img.convert('HSV')
    stat = ImageStat.Stat(tmpImg)
    h,s,v = stat.rms
    tmpImg.close()

    if s < 64:
        s = 64
    elif s > 128:
        s = 128

    enhPic = ImageEnhance.Brightness(o_img)
    tPic = enhPic.enhance(1.9*(60/perbright))
    enhPic = ImageEnhance.Color(tPic)
    tPic = enhPic.enhance(3.5-(2*(s/128)))
    enhPic = ImageEnhance.Sharpness(tPic)
    o_img = enhPic.enhance(3)

    if gfxmode == 1:
        o_img = o_img.resize((160,200),Image.ANTIALIAS)
        step = 4
        width = 160
        k = 4
    else:
        step = 8
        width = 320
        k = 2
    
    
    start = dt.datetime.now()

    threshold =[32]*3   #int(perbright/4)

    o_img = hitherdither.ordered.bayer.bayer_dithering(o_img, PaletteHither, threshold,order=8) #Fastest
    #o_img = hitherdither.ordered.yliluoma.yliluomas_1_ordered_dithering(o_img, PaletteHither,order=8) #Slow, must use order = 8
    #o_img = hitherdither.ordered.cluster.cluster_dot_dithering(o_img, PaletteHither,[32,32,32],order=8) #Fast
    #o_img = hitherdither.diffusion.error_diffusion_dithering(o_img, PaletteHither,order=2) #Slow, noisy.. dah


    d_colors = o_img.getcolors()

    d_counts = [d_colors[i][0] for i in range(len(d_colors))]
    bg_color = d_colors[np.abs(d_counts-np.percentile(d_counts,55)).argmin()][1]#d_counts.index(max(d_counts))

    o2_img = o_img.convert('RGB')

    n_img = np.asarray(o2_img)

    cells = b''
    #cells2 = []
    cells3 = []     #[[] for j in range(16)]
    screen = b''
    color = b''

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    #k = 4

    for j in range(0,200,8):
        for i in range(0,width,step):
            z = np.reshape(n_img[j:j+8,i:i+step],(-1,3))   #get 8x8 cell
            z = np.float32(z)
            ret,label,center=cv2.kmeans(z,k,None,criteria,10,cv2.KMEANS_RANDOM_CENTERS) #kmeans to k colors
            center = np.uint8(center)
            res = center[label.flatten()]
            pc = Image.fromarray(res.reshape((8,step,3)))
            #cells2.append(res.reshape((8,4,3)))
            cc = pc.getcolors()
            if gfxmode == 1:
                ix,cr,pal = get4closest(cc,bg_color)        #get 3 closest c64 colors to the kmeans palette + background color
                screen += ix.to_bytes(1,'big')   #screen color attributes
                color += cr.to_bytes(1,'big')   #color ram attributes
            else:
                ix,pal = get2closest(cc)        #get 2 closest c64 colors to the kmeans palette
                screen += ix.to_bytes(1,'big')   #screen color attributes
            pcc = hitherdither.ordered.bayer.bayer_dithering(pc, pal, [16,16,16],order=8) #Remap colors
            #print(np.asarray(pcc),packmulticolor(np.asarray(pcc)))
            if gfxmode == 1:
                cells+=packmulticolor(np.asarray(pcc)) #c64 cells
            else:
                cells+=np.packbits(np.asarray(pcc,dtype='bool')).tobytes() #c64 cells
            pcc = pcc.convert('RGB')
            cells3.append(np.asarray(pcc)) #bitmap cells

    en_img = np.zeros([200,width,3],dtype='uint8')   #[np.zeros([200,160,3],dtype='uint8') for j in range(16)]

    #Build final bitmap image
    for i,c in enumerate(cells3):
        sr = int(i/40)*8
        er = sr+8
        sc = (i*step)%width
        ec = sc+step
        en_img[sr:er,sc:ec] = c

    e_img = Image.fromarray(en_img)
    if gfxmode == 1:
        e_img = e_img.resize((320,200),Image.NEAREST)

    #print(len(cells),len(screen),len(color))
    return(e_img,cells,screen,color,bg_color)
#############################

