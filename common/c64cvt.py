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

# Colodore palette
PaletteRGB = [[0x00,0x00,0x00],[0xff,0xff,0xff],[0x81,0x33,0x38],[0x75,0xce,0xc8],[0x8e,0x3c,0x97],[0x56,0xac,0x4d],[0x2e,0x2c,0x9b],[0xed,0xf1,0x71],
    [0x8e,0x50,0x29],[0x55,0x33,0x00],[0xc4,0x6c,0x71],[0x4a,0x4a,0x4a],[0x7b,0x7b,0x7b],[0xa9,0xff,0x9f],[0x70,0x6d,0xeb],[0xb2,0xb2,0xb2]]

PaletteHither = hitherdither.palette.Palette([0x000000,0xffffff,0x813338,0x75cec8,0x8e3c97,0x56ac4d,0x2e2c9b,0xedf171,
    0x8e5029,0x553300,0xc46c71,0x4a4a4a,0x7b7b7b,0xa9ff9f,0x706deb,0xb2b2b2])

# Value and Hue 'Palettes' derived from the above
ValueHither = hitherdither.palette.Palette([0x000000,0x3b3b3b,0x4a4a4a,0x5f5f5f,0x7b7b7b,0x909090,0xb2b2b2,0xebebeb,0xffffff])

HueHither = hitherdither.palette.Palette([0x000000,0xfcfcfc,0xd0d0d0,0xababab,0x7c7c7c,0x515151,0x2c2c2c,0x101010,0x1a1a1a])

#bgcolor = 12

#Create a 320x200 Indexed PIL image with the C64 color palette
def GetIndexedImg(bgcolor = 0):
    cc = np.ndarray([200,320])
    cc.fill(bgcolor)
    return PaletteHither.create_PIL_png_from_closest_colour(cc)

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
# Custom ordered dither
# code derived from hitherdither

def B(m):
    """Get the Bayer matrix with side of length ``n``.
    Will only work if ``n`` is a power of 2.
    Reference: http://caca.zoy.org/study/part2.html
    :param int n: Power of 2 side length of matrix.
    :return: The Bayer matrix.
    """
    return (1 + m) / (1 + (m.shape[0] * m.shape[1]))

def custom_dithering(image, palette, thresholds, type=0):
    """Render the image using the ordered Bayer matrix dithering pattern.
    :param :class:`PIL.Image` image: The image to apply
        Bayer ordered dithering to.
    :param :class:`~hitherdither.colour.Palette` palette: The palette to use.
    :param thresholds: Thresholds to apply dithering at.
    :param int order: Custom matrix type.
    :return:  The Bayer matrix dithered PIL image of type "P"
        using the input palette.
    """
    dMatrix = np.asarray([
        [[4,1],[2,3]],
        [[1,13,4,16],[9,5,12,7],[3,15,2,14],[11,8,10,8]],
        [[1,2,3,4],[9,10,11,12],[5,6,7,8],[13,14,15,16]],
        [[1,9,4,12],[5,13,6,14],[3,11,2,10],[7,15,8,16]],
        [[10,1,12,6],[4,9,3,15],[14,2,13,7],[8,11,5,16]],
        [[0,32,8,40,2,34,10,42],[48,16,56,24,50,18,58,26],
        [12,44,4,36,14,46,6,38],[60,28,52,20,62,30,54,22],
        [3,35,11,43,1,33,9,41],[51,19,59,27,49,17,57,25],
        [15,47,7,39,13,45,5,37],[63,31,55,23,61,29,53,21]]],dtype=object)


    bayer_matrix = B(np.asarray(dMatrix[type]))
    ni = np.array(image, "uint8")
    thresholds = np.array(thresholds, "uint8")
    xx, yy = np.meshgrid(range(ni.shape[1]), range(ni.shape[0]))
    xx %= bayer_matrix.shape[0]
    yy %= bayer_matrix.shape[1]
    factor_threshold_matrix = np.expand_dims(bayer_matrix[yy, xx], axis=2) * thresholds
    new_image = ni + factor_threshold_matrix
    return palette.create_PIL_png_from_rgb_array(new_image)


######################################
def c64imconvert(Source, gfxmode = 1, lumaD = 0, fullD = 6, preproc = True):

    tstPic = Source.convert('RGB')

    o_img = frameResize(tstPic)

    if preproc:
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

        if s < 96:
            s = 96
        elif s > 128:
            s = 128

        enhPic = ImageEnhance.Brightness(o_img)
        tPic = enhPic.enhance(1.9*(64/perbright))
        enhPic = ImageEnhance.Contrast(tPic)
        tPic = enhPic.enhance(1+(s/256))
        enhPic = ImageEnhance.Color(tPic)
        tPic = enhPic.enhance(3-(2*(s/128)))
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
    
    #colorfilter(o_img)
    
    start = dt.datetime.now()

    threshold =[32]*3   #int(perbright/4)

    if lumaD > 0:
        Ybr_img = o_img.convert('YCbCr')
        Y,cb,cr = Ybr_img.split()

        #Y = hitherdither.ordered.bayer.bayer_dithering(Image.merge('RGB',(Y,Y,Y)), ValueHither, threshold,order=2)
        Y = custom_dithering(Image.merge('RGB',(Y,Y,Y)), ValueHither, [16,16,16],type=lumaD-1)
        #Y = ValueHither.create_PIL_png_from_rgb_array(Image.merge('RGB',(Y,Y,Y)))

        Y = Y.convert('RGB')

        t,t,Y = Y.split()

        Ybr_img = Image.merge('YCbCr',(Y,cb,cr))

        #H,S,V = Ybr_img.convert('HSV').split()

        #H = custom_dithering(Image.merge('RGB',(H,H,H)), HueHither, threshold,type=2)

        #H = H.convert('RGB')

        #H,t,t = H.split()

        #HSV_img = Image.merge('HSV',(H,S,V))

        o_img = Ybr_img.convert('RGB')

    if fullD > 0:
        o_img = custom_dithering(o_img, PaletteHither, threshold, type = fullD-1) # Fastest custom matrix
        #o_img = hitherdither.ordered.bayer.bayer_dithering(o_img, PaletteHither, threshold,order=8) #Fastest
        #o_img = hitherdither.ordered.yliluoma.yliluomas_1_ordered_dithering(o_img, PaletteHither,order=8) #Slow, must use order = 8
        #o_img = hitherdither.ordered.cluster.cluster_dot_dithering(o_img, PaletteHither,[32,32,32],order=8) #Fast
        #o_img = hitherdither.diffusion.error_diffusion_dithering(o_img, PaletteHither,order=2) #Slow, noisy.. dah
    else:
        o_img = PaletteHither.create_PIL_png_from_rgb_array(o_img)  # Fastest, no dither

    d_colors = o_img.getcolors()

    d_counts = [d_colors[i][0] for i in range(len(d_colors))]
    bg_color = d_colors[np.abs(d_counts-np.percentile(d_counts,55)).argmin()][1]#d_counts.index(max(d_counts))
    #print(d_colors[bg_color])

    o2_img = o_img.convert('RGB')
    #tmpImg = o2_img.resize((320,200),Image.NEAREST)
    #tmpImg.show('dithered')

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
            #pcc = hitherdither.ordered.bayer.bayer_dithering(pc, pal, [16,16,16],order=8) #Remap colors
            pcc = pal.create_PIL_png_from_rgb_array(pc)
            #print(np.asarray(pcc),packmulticolor(np.asarray(pcc)))
            if gfxmode == 1:
                cells+=packmulticolor(np.asarray(pcc)) #c64 cells
            else:
                cells+=np.packbits(np.asarray(pcc,dtype='bool')).tobytes() #c64 cells
            pcc = pcc.convert('RGB')
            cells3.append(np.asarray(pcc)) #bitmap cells

    en_img = np.zeros([200,width,3],dtype='uint8')   #[np.zeros([200,160,3],dtype='uint8') for j in range(16)]
    #q_img = np.zeros([200,160,3],dtype='uint8')

    #print(dt.datetime.now()-start)

    #diff = [0]*16
    #bg = 11
    #Build quantized bitmap image
    # for i,c in enumerate(cells2):
    #     sr = int(i/40)*8
    #     er = sr+8
    #     sc = (i*4)%160
    #     ec = sc+4
    #     q_img[sr:er,sc:ec] = c
    # e_img = Image.fromarray(q_img)
    # e_img = e_img.resize((320,200),Image.NEAREST)
    #e_img.show(title='Q')

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
    #e_img.show(title='Final')

    #print(len(cells),len(screen),len(color))
    return(e_img,cells,screen,color,bg_color)
#############################

