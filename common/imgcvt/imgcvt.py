#from ctypes.wintypes import RGB
import cv2
import numpy as np
import math
from PIL import Image, ImageEnhance, ImageStat
import hitherdither

from common.imgcvt import common as CC
from common.imgcvt import c64 as c64
from common.imgcvt import plus4 as p4
from common.imgcvt import msx as msx
#import cvtmods.zxspectrum as zx
from common.imgcvt import palette as Palette
from common.imgcvt import dither as DT
import os

from enum import IntEnum

#Gfx modes
GFX_MODES = []
gfxmodes = IntEnum('gfxmodes',['C64HI','C64MULTI','P4HI','P4MULTI','MSXSC2'], start=0)

#Mode conversion mapping
mode_conv = {'PET64':{gfxmodes.P4HI:gfxmodes.C64HI,gfxmodes.P4MULTI:gfxmodes.C64MULTI,gfxmodes.MSXSC2:gfxmodes.C64MULTI},
             'PET264':{gfxmodes.C64HI:gfxmodes.P4HI,gfxmodes.C64MULTI:gfxmodes.P4MULTI,gfxmodes.MSXSC2:gfxmodes.P4MULTI},
             'MSX1':{gfxmodes.P4HI:gfxmodes.MSXSC2,gfxmodes.P4MULTI:gfxmodes.MSXSC2,gfxmodes.C64HI:gfxmodes.MSXSC2,gfxmodes.C64MULTI:gfxmodes.MSXSC2}}

#Image scale/crop modes
cropmodes = IntEnum('cropmodes',['LEFT','TOP','RIGHT','BOTTOM','T_LEFT','T_RIGHT','B_LEFT','B_RIGHT','CENTER','FILL','FIT','H_FIT','V_FIT'], start=0)

#Native format filename extensions
im_extensions = c64.Native_Ext + p4.Native_Ext + msx.Native_Ext

######## Image preprocess class ########
class PreProcess:
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
####################################
def build_modes():
    for m in c64.GFX_MODES:
        GFX_MODES.append(m)
    for m in p4.GFX_MODES:
        GFX_MODES.append(m)
    for m in msx.GFX_MODES:
        GFX_MODES.append(m)
    # for m in zx.GFX_MODES:
    #     GFX_MODES.append(m)

###########################################################################
# Image crop and resize
###########################################################################
def frameResize(i_image, gfxmode:gfxmodes, mode:cropmodes=cropmodes.FILL):
    i_ratio = i_image.size[0] / i_image.size[1]
    in_size = GFX_MODES[gfxmode]['in_size']
    dst_ratio = in_size[0]/in_size[1]
    if mode == cropmodes.FILL:
        if dst_ratio >= i_ratio:
            i_image = i_image.resize((in_size[0],in_size[0]*i_image.size[1]//i_image.size[0]), Image.LANCZOS)
            box = (0,(i_image.size[1]-in_size[1])/2,i_image.size[0],(i_image.size[1]+in_size[1])/2)
        elif dst_ratio < i_ratio:
            i_image = i_image.resize((in_size[1]*i_image.size[0]//i_image.size[1],in_size[1]),Image.LANCZOS)
            box = ((i_image.size[0]-in_size[0])/2,0,(i_image.size[0]+in_size[0])/2,i_image.size[1])
    elif mode == cropmodes.FIT:
        if dst_ratio <= i_ratio:
            scale = i_image.size[0]/in_size[0]
            i_image = i_image.resize((in_size[0],int(i_image.size[1]//scale)), Image.LANCZOS)
            box = (0,(i_image.size[1]-in_size[1])/2,i_image.size[0],(i_image.size[1]+in_size[1])/2)
        elif dst_ratio > i_ratio:
            scale = i_image.size[1]/in_size[1]
            i_image = i_image.resize((int(i_image.size[0]//scale),in_size[1]), Image.LANCZOS)
            box = ((i_image.size[0]-in_size[0])//2,0,(i_image.size[0]+in_size[0])//2,i_image.size[1])
    elif mode == cropmodes.H_FIT:
        scale = i_image.size[0]/in_size[0]
        i_image = i_image.resize((in_size[0],i_image.size[1]//scale), Image.LANCZOS)
        box = (0,(i_image.size[1]-in_size[1])//2,i_image.size[0],(i_image.size[1]+in_size[1])//2)
    elif mode == cropmodes.V_FIT:
        scale = i_image.size[1]/in_size[1]
        i_image = i_image.resize((i_image.size[0]//scale,in_size[1]), Image.LANCZOS)
        box = ((i_image.size[0]-in_size[0])/2,0,(i_image.size[0]+in_size[0])/2,i_image.size[1])
    elif mode == cropmodes.LEFT:
        box = (0,(i_image.size[1]-in_size[1])/2,in_size[0],(i_image.size[1]+in_size[1])/2)
    elif mode == cropmodes.TOP:
        box = ((i_image.size[0]-in_size[0])/2,0,(i_image.size[0]+in_size[0])/2,in_size[1])
    elif mode == cropmodes.RIGHT:
        box = (i_image.size[0]-in_size[0],(i_image.size[1]-in_size[1])/2,i_image.size[0],(i_image.size[1]+in_size[1])/2)
    elif mode == cropmodes.BOTTOM:
        box = ((i_image.size[0]-in_size[0])/2,i_image.size[1]-in_size[1],(i_image.size[0]+in_size[0])/2,i_image.size[1])
    elif mode == cropmodes.T_LEFT:
        box = (0,0,in_size[0],in_size[1])
    elif mode == cropmodes.T_RIGHT:
        box = (i_image.size[0]-in_size[0],0,i_image.size[0],in_size[1])
    elif mode == cropmodes.B_LEFT:
        box = (0,i_image.size[1]-in_size[1],in_size[0],i_image.size[1])
    elif mode == cropmodes.B_RIGHT:
        box = (i_image.size[0]-in_size[0],i_image.size[1]-in_size[1],i_image.size[0],i_image.size[1])
    elif mode == cropmodes.CENTER:
        box = ((i_image.size[0]-in_size[0])/2,(i_image.size[1]-in_size[1])/2,(i_image.size[0]+in_size[0])/2,(i_image.size[1]+in_size[1])/2)
    i_image = i_image.crop(box)
    return i_image

########################################################
# Preset brightness/contrast/etc
########################################################
def imagePreset(o_img:Image.Image, cmatch)->PreProcess:
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
    return PreProcess(brightness, contrast, sat)

############################################################
# Adjust image brightness/contrast/etc
############################################################
def imageProcess(o_img:Image.Image, parameters:PreProcess):
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

################################################################################################################################################################################################
# Convert image
################################################################################################################################################################################################
def Image_convert(Source:Image.Image, in_pal:list, out_pal:list, gfxmode:gfxmodes=gfxmodes.C64MULTI, dither:DT.dithertype=DT.dithertype.BAYER8, threshold:int=4 , cmatch:int=None, bg_color=None):
    Matchmodes = {1: Palette.colordelta.EUCLIDEAN,2: Palette.colordelta.CCIR,3: Palette.colordelta.LAB}


    if bg_color == None:
        bg_color = [-1]
    Mode = GFX_MODES[gfxmode]

    if cmatch == None:
        cmatch = Mode.get('match',Palette.colordelta.EUCLIDEAN)
    else:
        cmatch = Matchmodes[cmatch]

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
    in_PaletteH.colordelta = cmatch
    out_PaletteH.colordelta = cmatch
    y_PaletteH.colordelta = cmatch
    c_count = len(rgb_in)   # Number of colors to quantize to
    o_img = Source
    if Mode['in_size']!=Mode['out_size']:
        o_img = o_img.resize(Mode['out_size'],Image.LANCZOS)
    width = Mode['out_size'][0]
    height = Mode['out_size'][1]
    k = 2<<(Mode['bpp']-1)
    x_step = Mode['attr'][0]
    y_step = Mode['attr'][1]
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
                    if len(np.unique(z)) >= k:  #More than k colors in the cell?
                        ucount = np.bincount(z) #Number of pixels for each color index
                        for l,t in enumerate(bg_color):
                            if t == -1 and Mode['global_colors'][l]:
                                ccount[l] = np.append(ccount[l],np.argmax(ucount))
                                ucount[np.argmax(ucount)] = -1  #Remove the color 
            for j in range(len(bg_color)):
                if bg_color[j] == -1 and Mode['global_colors'][j]:
                    if len(ccount[j]) > 0:
                        count = np.bincount(ccount[j])
                        tc = int(np.argmax(count))
                        while tc in bg_color:
                            count[tc] = -1
                            tc = int(np.argmax(count))
                        bg_color[j] = tc
                    else:
                        bg_color[j] = 0
        bestbg = [True if x == -2 else False for x in bg_color]
    if Mode['attr']!=(0,0):
        o2_img = o_img.convert('RGB')
        n_img = np.asarray(o2_img)
        if True in bestbg:
            cells3 = [[] for j in range(c_count)]
            buffers = [get_buffers() for j in range(c_count)]
        else:
            cells3 = []
            buffers = get_buffers()
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        pal:Palette.Palette
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
            e_img= Image.fromarray(np.uint8(mask))
            e_img.putpalette(tPal)
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
            e_img= Image.fromarray(np.uint8(mask))
            e_img.putpalette(tPal)
    else:   #Unrestricted
        n_img = np.asarray(o_img)
        mask = i_to[n_img]
        e_img= Image.fromarray(np.uint8(mask))
        e_img.putpalette(tPal)
        buffers =[]
    for i in range(len(bg_color)):
        if bg_color[i]<0:
            bg_color[i] = 0
    for i in range(len(buffers)):
        buffers[i] = bytes(buffers[i])
    return(e_img,buffers,bg_color)

###############################################################################################################################################################################################################################
# Convert image to specified graphic mode
###############################################################################################################################################################################################################################
def convert_To(Source:Image.Image, gfxmode:gfxmodes=gfxmodes.C64MULTI, preproc:PreProcess=None, cropmode:cropmodes=cropmodes.FILL, dither:DT.dithertype=DT.dithertype.BAYER8, threshold:int=4 , cmatch:int=None, g_colors=None ):
    if g_colors == None:
        g_colors = [-1]*len(GFX_MODES[gfxmode]['global_colors'])
    t_img = Source.convert('RGB')
    in_img = frameResize(t_img, gfxmode, cropmode)
    if preproc == None:
        preproc = imagePreset(in_img,cmatch)
        preproc.hue = 180
        preproc.sharpness = 1.5
    in_img = imageProcess(in_img,preproc)
    cv_img, data, gcolors = Image_convert(in_img, GFX_MODES[gfxmode]['palettes'][0][1], GFX_MODES[gfxmode]['palettes'][0][1], gfxmode,
                    dither, threshold, cmatch,g_colors)
    return cv_img, data, gcolors

#########################################################################################################
# Create a Indexed PIL image with the desired mode dimensions and color palette, and filled with bgcolor
#########################################################################################################
def get_IndexedImg(mode: gfxmodes = gfxmodes.C64HI, bgcolor = 0):
    hd_p = []
    cc = np.ndarray([GFX_MODES[mode]['in_size'][1],GFX_MODES[mode]['in_size'][0]])
    cc.fill(bgcolor)
    for c in GFX_MODES[mode]['palettes'][0][1]: # iterate colors
        if c['enabled']:
            rgb = CC.RGB24(c['RGBA'])
            hd_p.append(rgb)
        else:
            hd_p.append(0xFF00FF)   # Add pure purple for unused palette entries
    inPal = Palette.Palette(hd_p)
    return inPal.create_PIL_png_from_closest_colour(cc), inPal

###################################################################
# Returns the color palette index closest to the passed RGB values
###################################################################
def get_ColorIndex(mode: gfxmodes, rgb):
    pal = GFX_MODES[mode]['palettes'][0][1]
    dist = [2**1024]*len(pal)
    for c in pal:
        if c['enabled']:
            dist[c['index']] = CC.Redmean(rgb,c['RGBA'][:3])
    return dist.index(min(dist))

############################################################
# Returns the RGB values for the index in the color palette
############################################################
def get_RGB(mode: gfxmodes, index):
    pal = GFX_MODES[mode]['palettes'][0][1]
    rgb = [0,0,0]
    for c in pal:
        if c['enabled']:
            if c['index'] == index:
                return c['RGBA'][:3]
    return rgb

#####################################################################################
# Open a native image, return Image object, (Native image data if any, Graphic mode)
#####################################################################################
def open_Image(filename:str):
    extension = os.path.splitext(filename)[1].upper()
    if extension in c64.Native_Ext:
        result = c64.load_Image(filename)
        if result != None:
            result[1] = gfxmodes.C64HI + result[1]
    elif extension in p4.Native_Ext:
        result = p4.load_Image(filename)
        if result != None:
            result[1] = gfxmodes.P4HI + result[1]
    elif extension in msx.Native_Ext:
        result = msx.load_Image(filename)
        if result != None:
            result[1] = gfxmodes.MSXSC2 + result[1]
    else:
        return None
    return result

#########################################################################################
#Prepare a native image to be saved to disk, return a byte string and formatted filename
#########################################################################################
def build_File(buffers, gcolors, filename, gfxmode):
    return GFX_MODES[gfxmode]['save_output'][1](buffers,gcolors,filename)

##### On load
build_modes()
