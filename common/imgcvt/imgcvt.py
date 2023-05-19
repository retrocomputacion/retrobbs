#from ctypes.wintypes import RGB
import cv2
import numpy as np
import math
from PIL import Image, ImageEnhance, ImageStat
import hitherdither
import datetime as dt

import common.imgcvt.common as CC
import common.imgcvt.c64 as c64
#import cvtmods.plus4 as p4
#import cvtmods.msx as msx
#import cvtmods.zxspectrum as zx
import common.imgcvt.palette as Palette
import common.imgcvt.dither as DT

from enum import Enum

#Gfx modes
GFX_MODES = []

gfxmodes = Enum('gfxmodes',['C64HI','C64MULTI'], start=0)

class ColorProcess:

    brightness:float
    contrast:float
    saturation:float
    hue:float
    sharpness:float


    def __init__(self, brightness=1, contrast=1, saturation=1,hue=180,sharpness=1):
        self.brightness = brightness
        self.contrast = contrast
        self.saturation = saturation
        self.hue = hue
        self.sharpness = sharpness


####################################
# Get GFX modes from loaded modules
# (We're not dynamically loading modules yet)
def build_modes():
    for m in c64.GFX_MODES:
        GFX_MODES.append(m)
    # for m in p4.GFX_MODES:
    #     GFX_MODES.append(m)
    # for m in msx.GFX_MODES:
    #     GFX_MODES.append(m)
    # for m in zx.GFX_MODES:
    #     GFX_MODES.append(m)


################################
# Image crop and resize
def frameResize(i_image, gfxmode:gfxmodes):
    i_ratio = i_image.size[0] / i_image.size[1]
    in_size = GFX_MODES[gfxmode.value]['in_size']
    dst_ratio = in_size[0]/in_size[1]   #320/200

    if dst_ratio >= i_ratio:
        i_image = i_image.resize((in_size[0],in_size[0]*i_image.size[1]//i_image.size[0]), Image.LANCZOS)
        box = (0,(i_image.size[1]-in_size[1])/2,i_image.size[0],(i_image.size[1]+in_size[1])/2)
        i_image = i_image.crop(box)
    elif dst_ratio < i_ratio:
        i_image = i_image.resize((in_size[1]*i_image.size[0]//i_image.size[1],in_size[1]),Image.LANCZOS)
        box = ((i_image.size[0]-in_size[0])/2,0,(i_image.size[0]+in_size[0])/2,i_image.size[1])
        i_image = i_image.crop(box)

    return i_image



######################################
#   Preset brightness/contrast/etc
#
def imagePreset(o_img:Image.Image, cmatch)->ColorProcess:

    stat = ImageStat.Stat(o_img)

    r,g,b = stat.rms
    perbright = math.sqrt(0.241*(r**2) + 0.691*(g**2) + 0.068*(b**2))

    if perbright < 25:
        perbright = 25
    elif perbright > 128:
        perbright = 128

    brightness= (64/perbright)*(1.75 if cmatch == 3 else 1.9)

    #Saturation
    tmpImg = o_img.convert('HSV')
    stat = ImageStat.Stat(tmpImg)
    h,s,v = stat.rms
    c = tmpImg.getextrema()[2]

    tmpImg.close()

    if s < 96:
        s = 96
    elif s > 128:
        s = 128

    contrast = (1+((c[1]-c[0])/255))*(0.75 if cmatch == 3 else 1)
    sat = 3-(2*(s/128))

    return ColorProcess(brightness, contrast, sat)


#########################################
#   Adjust image brightness/contrast/etc
#
def imageProcess(o_img:Image.Image, parameters:ColorProcess):

    hue = int(((parameters.hue-180)/360)*255)
    enhPic = ImageEnhance.Brightness(o_img)
    tPic = enhPic.enhance(parameters.brightness)
    enhPic = ImageEnhance.Contrast(tPic)
    tPic = enhPic.enhance(parameters.contrast)
    enhPic = ImageEnhance.Color(tPic)
    tPic = enhPic.enhance(parameters.saturation)
    enhPic = ImageEnhance.Sharpness(tPic)
    tPic = enhPic.enhance(parameters.sharpness)
    H,S,V = tPic.convert('HSV').split()
    th = np.asarray(H,dtype=np.uint16)
    temp = np.mod(th+hue,255).astype(np.uint8)
    o_img = Image.merge('HSV',(Image.fromarray(temp),S,V)).convert('RGB')

    return o_img


######################################
#   Convert image
#
def Image_convert(Source:Image.Image, in_pal:list, out_pal:list, gfxmode:gfxmodes=gfxmodes.C64MULTI, dither:DT.dithertype=DT.dithertype.BAYER8, threshold:int=4 , cmatch:int=3, bg_color=None):

    Matchmodes = {1: Palette.colordelta.EUCLIDEAN,2: Palette.colordelta.CCIR,3: Palette.colordelta.LAB}

    if bg_color == None:
        bg_color = [-1]

    Mode = GFX_MODES[gfxmode.value]

    pixelcount = Mode['out_size'][0]*Mode['out_size'][1]

    # Callbacks
    bm_pack = Mode['bm_pack']
    get_buffers = Mode['get_buffers']
    get_attr = Mode['get_attr']
    attr_pack = Mode['attr_pack']

    # Generate palette(s)
    rgb_in = []     # contains the [[r,g,b],index values] of all the enabled colors
    rgb_out = [0]*len(out_pal)    # contains the r,g,b values of all the colors 
    rgb_y = []      # Luminance palette as r,g,b
    hd_in = []      # 24bit rgb values of enabled colors
    hd_out = [0]*len(out_pal)     # 24bit rgb values of all colors
    y_in = []       # '24bit' Luminance palette
    for c in in_pal: # iterate colors
        if c['enabled']:
            rgb = CC.RGB24(c['RGBA'])
            rgb_in.append([np.array(c['RGBA'][:3]),c['index']])   # ignore alpha for now
            hd_in.append(rgb)
            # Luminance mode fixed as over input palette for now
            # if  lmode == 'Over input palette':
            rgb_y.append([CC.Luma(c['RGBA']),CC.Luma(c['RGBA']),CC.Luma(c['RGBA'])])
            y_in.append(CC.RGB24([CC.Luma(c['RGBA']),CC.Luma(c['RGBA']),CC.Luma(c['RGBA'])]))

    # if lmode == 'Black & White':
    #     rgb_y = [[0,0,0],[255,255,255]]
    #     y_in = [0x000000,0xffffff]

    for c in out_pal:
        rgb = CC.RGB24(c['RGBA'])
        rgb_out[c['index']]=np.array(c['RGBA'][:3])   # ignore alpha for now
        hd_out[c['index']]=rgb

    # PIL Display palette
    i_to = np.array([x[1] for x in rgb_in])
    tPal = [element for sublist in rgb_out for element in sublist]
    plen = len(tPal)//3
    tPal.extend(tPal[:3]*(256-plen))


    in_PaletteH = Palette.Palette(hd_in)   #hitherdither.palette.Palette(hd_in)   #Palette to dither/quantize against
    out_PaletteH = Palette.Palette(hd_out)  #hitherdither.palette.Palette(hd_out) #Palette to display
    y_PaletteH = Palette.Palette(y_in)  #hitherdither.palette.Palette(y_in)     #Luminance palette to dither/quantize against

    # Set color compare method
    in_PaletteH.colordelta = Matchmodes[cmatch]
    out_PaletteH.colordelta = Matchmodes[cmatch]
    y_PaletteH.colordelta = Matchmodes[cmatch]

    c_count = len(rgb_in)   # Number of colors to quantize to

    o_img = Source

    if Mode['in_size']!=Mode['out_size']:
        o_img = o_img.resize(Mode['out_size'],Image.LANCZOS)
    width = Mode['out_size'][0]
    height = Mode['out_size'][1]
    k = 2<<(Mode['bpp']-1)
    x_step = Mode['attr'][0]
    y_step = Mode['attr'][1]

    start = dt.datetime.now()

    # Dither threshold
    Fthr =[2<<threshold]*3
    

    # Full dither
    if dither != DT.dithertype.NONE:
        if dither == DT.dithertype.FLOYDSTEINBERG:
            fsPal = [element for sublist in rgb_in for element in sublist[0]]
            plen = len(fsPal)//3
            fsPal.extend(fsPal[:3]*(256-plen))
            #create tmp PIL image with desired palette
            tmpI = Image.new('P',(1,1))
            tmpI.putpalette(fsPal)
            o_img = o_img.quantize(colors=len(rgb_in), palette=tmpI)
        elif dither == DT.dithertype.CLUSTER:
            o_img = hitherdither.ordered.cluster.cluster_dot_dithering(o_img, in_PaletteH,order=8, thresholds=Fthr) #Fast
        elif dither == DT.dithertype.YLILUOMA1:
            o_img = hitherdither.ordered.yliluoma.yliluomas_1_ordered_dithering(o_img, in_PaletteH, order=8) #Slow, must use order = 8
        else:
            o_img = DT.custom_dithering(o_img, in_PaletteH, Fthr, type = dither) # Fastest custom matrix
    else:
        o_img = in_PaletteH.create_PIL_png_from_rgb_array(o_img)  # Fastest, no dither

    d_colors = o_img.getcolors()
    d_counts = [d_colors[i][0] for i in range(len(d_colors))]

    #Prevent iterating for more than one best global color, replace with estimated
    for x in range(len(bg_color)):
        if (bg_color[x] == -2) and (bg_color.count(-2)>1):
            bg_color[x] = -1

    bestbg = [False]*k
    if Mode['global_colors'].count(True) > 0:
        if -1 in bg_color:  #Estimate best global colors
            n_img = np.asarray(o_img)
            ccount = [np.array([],np.int16)] * len(bg_color)
            for j in range(0,height,y_step):        # Step thru attribute cells
                for i in range(0,width,x_step):
                    z = np.reshape(n_img[j:j+y_step,i:i+x_step],(-1))   #get bitmap cell
                    if len(np.unique(z)) >= k:
                        ucount = np.bincount(z)
                        for l,t in enumerate(bg_color):
                            if t == -1:
                                ccount[l] = np.append(ccount[l],np.argmax(ucount))
                                ucount[np.argmax(ucount)] = -1  #Remove the color 
            for j in range(len(bg_color)):
                if bg_color[j] == -1:
                    if len(ccount[j]) > 0:
                        bg_color[j] = int(np.argmax(np.bincount(ccount[j])))
                    else:
                        bg_color[j] = 0
            #bg_color = rgb_in[d_colors[np.abs(d_counts-np.percentile(d_counts,55)).argmin()][1]][1] #d_counts.index(max(d_counts))
        bestbg = [True if x == -2 else False for x in bg_color]

    if Mode['attr']!=(0,0):
        o2_img = o_img.convert('RGB')
        n_img = np.asarray(o2_img)

        if True in bestbg:    #gfxmode == 2 and bestbg:
            cells3 = [[] for j in range(c_count)]     #[[] for j in range(16)]
            buffers = [get_buffers() for j in range(c_count)]
        else:
            cells3 = []     #[[] for j in range(16)]
            buffers = get_buffers()
        # cells3 = []
        # buffers = []

        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        #k = 4

        pal:Palette.Palette    #hitherdither.palette.Palette

        for j in range(0,height,y_step):        # Step thru attribute cells
            for i in range(0,width,x_step):
                z = np.reshape(n_img[j:j+y_step,i:i+x_step],(-1,3))   #get bitmap cell
                z = np.float32(z)
                ret,label,center=cv2.kmeans(z,k,None,criteria,10,cv2.KMEANS_RANDOM_CENTERS) #kmeans to k colors
                center = np.uint8(center)
                res = center[label.flatten()]
                pc = Image.fromarray(res.reshape((y_step,x_step,3)))
                cc = pc.getcolors() # Kmeans palette [count,[r,g,b]]
                if True in bestbg:
                    for bg in range(0,c_count):  #Iterate through background colors
                        bg_color[bestbg.index(True)] = bg
                        attr,pal = get_attr(cc,rgb_in,rgb_out,bg_color)        #get closest colors to the kmeans palette + background color
                        pcc = pal.create_PIL_png_from_rgb_array(pc)
                        bm_pack(i//x_step,j//y_step,pcc,buffers[bg])
                        attr_pack(i//x_step,j//y_step,attr,buffers[bg])
                        #i_to = np.array(attr)   #Translate to display palette
                        #t_img=np.asarray(pcc)
                        #mask = i_to[t_img-t_img.min()]
                        #pcc= Image.fromarray(np.uint8(mask))    #now it should be indexed to the display palette
                        #pcc.putpalette(tPal)
                        cells3[bg].append(np.asarray(pcc.convert('RGB'))) #bitmap cells
                else:
                    attr,pal = get_attr(cc,rgb_in,rgb_out,bg_color)     #get closest colors to the kmeans palette + background color
                    pcc = pal.create_PIL_png_from_rgb_array(pc)     #converted from rgb to dither palette colors
                    bm_pack(i//x_step,j//y_step,pcc,buffers)
                    attr_pack(i//x_step,j//y_step,attr,buffers)
                    cells3.append(np.asarray(pcc.convert('RGB'))) #bitmap cells
        columns=width//x_step
        if True in bestbg:
            bix = bestbg.index(True)
            en_img = [np.zeros([height,width,3],dtype='uint8') for j in range(c_count)]
            e_img = [None for j in range(c_count)]
            err = []
            for bg in range(0,c_count):
                for i,c in enumerate(cells3[bg]):
                    sr = int(i/columns)*y_step
                    er = sr+y_step
                    sc = (i*x_step)%width
                    ec = sc+x_step
                    en_img[bg][sr:er,sc:ec] = c
                err.append(1-(cv2.norm( n_img, en_img[bg], cv2.NORM_L2 ))/pixelcount)
                e_img[bg] = Image.fromarray(en_img[bg]).resize(Mode['in_size'],Image.NEAREST) 
            bg_color[bix] = err.index(max(err)) #Best bg color (index to...)
            n_img = np.asarray(in_PaletteH.create_PIL_png_from_rgb_array(np.asarray(e_img[bg_color[bix]])))
            mask = i_to[n_img]
            o_img= Image.fromarray(np.uint8(mask))
            #o_img = in_PaletteH.create_PIL_png_from_rgb_array(mask)
            o_img.putpalette(tPal)
            e_img = o_img.convert('RGB')
            buffers=buffers[bg_color[0]]
        else:
            en_img = np.zeros([height,width,3],dtype='uint8')   #[np.zeros([200,160,3],dtype='uint8') for j in range(16)]
            #Build final bitmap image
            for i,c in enumerate(cells3):
                sr = int(i/columns)*y_step
                er = sr+y_step
                sc = (i*x_step)%width
                ec = sc+x_step
                en_img[sr:er,sc:ec] = c
            e_img = Image.fromarray(en_img)
            if Mode['in_size']!=Mode['out_size']:
                e_img = e_img.resize(Mode['in_size'],Image.NEAREST)
            n_img = np.asarray(in_PaletteH.create_PIL_png_from_rgb_array(np.asarray(e_img)))
            mask = i_to[n_img]
            #rmap = i_to[mask.argmax(1)]
            o_img= Image.fromarray(np.uint8(mask))
            #o_img = in_PaletteH.create_PIL_png_from_rgb_array(mask)
            o_img.putpalette(tPal)
            e_img = o_img.convert('RGB')
    else:   #Unrestricted
        n_img = np.asarray(o_img)
        mask = i_to[n_img]
        #rmap = i_to[mask.argmax(1)]
        o_img= Image.fromarray(np.uint8(mask))
        #o_img = in_PaletteH.create_PIL_png_from_rgb_array(mask)
        o_img.putpalette(tPal)
        e_img = o_img.convert('RGB')
        buffers =[]
    #if bestbg:
    #    return(e_img[bg_color],buffers[bg_color],rgb_in[bg_color][1])
    #else:
    # if (bg_color[0]<0) or (Mode['global_colors'].count(True) == 0):
    #     bg_color[0]=0
    # else:
    #     bg_color[0]=next(i for i,x in enumerate(rgb_in) if x[1]==bg_color[0])
    for i in range(len(bg_color)):
        if bg_color[i]<0:
            bg_color[i] = 0
    for i in range(len(buffers)):
        buffers[i] = bytes(buffers[i])
    return(e_img,buffers,bg_color)


# Convert image
def convert_To(Source:Image.Image, gfxmode:gfxmodes=gfxmodes.C64MULTI, preproc:ColorProcess=None, dither:DT.dithertype=DT.dithertype.BAYER8, threshold:int=4 , cmatch:int=1, g_colors=None ):

    if g_colors == None:
        g_colors = [-1]
    t_img = Source.convert('RGB')
    in_img = frameResize(t_img, gfxmode)
    if preproc == None:
        preproc = imagePreset(in_img,cmatch)
        preproc.hue = 180
        preproc.sharpness = 1.5

    in_img = imageProcess(in_img,preproc)


    cv_img, data, gcolors = Image_convert(in_img, GFX_MODES[gfxmode.value]['palettes'][0][1], GFX_MODES[gfxmode.value]['palettes'][0][1], gfxmode,
                    dither, threshold, cmatch,g_colors)
    #cv_data = [data, bgcolor]
    return cv_img, data, gcolors

#Create a Indexed PIL image with the desired mode dimensions and color palette, and filled with bgcolor
def get_IndexedImg(mode: gfxmodes = gfxmodes.C64HI, bgcolor = 0):
    hd_p = []
    cc = np.ndarray([GFX_MODES[mode.value]['in_size'][1],GFX_MODES[mode.value]['in_size'][0]])
    cc.fill(bgcolor)
    for c in GFX_MODES[mode.value]['palettes'][0][1]: # iterate colors
        if c['enabled']:
            rgb = CC.RGB24(c['RGBA'])
            hd_p.append(rgb)
    inPal = Palette.Palette(hd_p)
    return inPal.create_PIL_png_from_closest_colour(cc), inPal


##### On load
build_modes()