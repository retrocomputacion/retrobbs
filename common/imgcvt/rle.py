##################
# RLE Routines
##################
import numpy as np
import os
from PIL import Image

from common.imgcvt import common as CC
from common.imgcvt import palette as Palette
from common.imgcvt.types import gfxmodes


# Palette structure
Palette_RLE = [{'color':'Background','RGBA':[0x00,0x00,0x00,0xff],'enabled':True,'index':0},
    {'color':'Foreground','RGBA':[0xff,0xff,0xff,0xff],'enabled':True,'index':1}]

RLEPalettes = [['RLE',Palette_RLE]]

Native_Ext = ['.RLE']


def rle_get2closest(colors,p_in,p_out,fixed):
    _indexes = [0,1]
    closest = [0,16581375]
    return(_indexes,Palette.Palette(closest))


def bmpackrle(column,row,cell,buffers):
    npim = np.array(cell).ravel()
    count = 0
    white = False
    for p in npim:
        if not white:  # Black pixels
            if not p:
                count += 1
                if count == 94: # Max run
                    buffers[0].append(32+count)
                    white = True
                    count = 0
                    continue
            else:
                buffers[0].append(32+count)
                white = True
                count = 1
        else:   # White pixels
            if p:
                count += 1
                if count == 94: # Max run
                    buffers[0].append(32+count)
                    white = False
                    count = 0
            else:
                buffers[0].append(32+count)
                white = False
                count = 1
    buffers[0].append(32+count) # Add last pixels

def attrpack(column,row,attr,buffers):
    pass
    ...


# Returns a list of lists
def get_buffers(mode=False):
    buffers=[]
    if mode:
        buffers.append([0x1b,ord('G'),ord('M')])    # [0] Bitmap
    else:
        buffers.append([0x1b,ord('G'),ord('H')])    # [0] Bitmap
    buffers.append([])    # [1]
    buffers.append([])    # [2]
    return buffers

def buildfile(buffers,filename):
    t_data = buffers[0] + b'\x1bGN\x00\x00\x00'
    return(t_data,os.path.splitext(filename)[0]+'rle')

#######################################################################################################################
# Graphic modes structure
# name: Name displayed in the combobox
# bpp: bits per pixel
# attr: attribute size in pixels
# global_colors: a boolean tuple of 2^bpp elements, True if the color for that index is global for the whole screen
# palettes: a list of name/palette pairs
# in_size: input image dimensions, converted image will also be displayed with these dimensions
# out_size: native image dimensions
# get_attr: function call to get closest colors for an attribute cell
# bm_pack:  function call to pack the bitmap from 8bpp into the native format order
# attr_pack: function call to pack the individual cell colors into attribute byte(s)
# get_buffers: function call returns the native bitmap and attribute buffers
# save_output: a list of lists in the format ['name','extension',save_function]
#######################################################################################################################

GFX_MODES=[{'name':'RLE HI','bpp':1,'attr':(256,192),'global_colors':(False,False),'palettes':RLEPalettes,
            'global_names':[], 'match':Palette.colordelta.CCIR,
            'in_size':(256,192),'out_size':(256,192),'get_attr':rle_get2closest,'bm_pack': bmpackrle,'attr_pack':attrpack,
            'get_buffers':lambda :get_buffers(False),'save_output':['RLE HI',lambda buf,c,fn: buildfile(buf,fn)]},
            {'name':'RLE MED','bpp':1,'attr':(128,96),'global_colors':(False,False),'palettes':RLEPalettes,
            'global_names':[], 'match':Palette.colordelta.CCIR,
            'in_size':(128,96),'out_size':(128,96),'get_attr':rle_get2closest,'bm_pack': bmpackrle,'attr_pack':attrpack,
            'get_buffers':lambda :get_buffers(True),'save_output':['RLE HI',lambda buf,c,fn: buildfile(buf,fn)]}]

##############################
# Load native image format
##############################
def load_Image(filename:str):
    multi = gfxmodes.VTHI
    data = [None]*3
    gcolors = [0]*2  # Border, Background
    extension = os.path.splitext(filename)[1].upper()
    # Read file
    if (extension == '.RLE'):
        with open(filename,'rb') as ifile:
            mode = ifile.read(3)
            if mode == b'\x1bGH':
                multi = gfxmodes.VTHI
                shape = (192,256)
                pixels = 49152
                text = 'HIRES RLE'
            elif mode == b'\x1bGM':
                multi = gfxmodes.VTMED
                shape = (96,128)
                pixels = 25476
                text = 'MEDRES RLE'
            else:
                return None
            data[0] = mode
            bb = ifile.read(1)
            esc = False
            while bb != b'':
                if bb == b'\x1b':
                    esc = True
                if esc:
                    bb = ifile.read(2)
                    if bb == b'GN':  # Back to Text
                        break
                    else:
                        data[0] = data[0] + bb
                else:
                    if bb[0] >= 32:
                        data[0] = data[0] + bb
                bb = ifile.read(1)
    else:
        return None
    # Render image
    # Generate palette(s)
    rgb_in = []
    for c in Palette_RLE: # iterate colors
        rgb_in.append(np.array(c['RGBA'][:3]))   # ignore alpha for now
    fsPal = [element for sublist in rgb_in for element in sublist]
    plen = len(fsPal)//3
    fsPal.extend(fsPal[:3]*(256-plen))

    nimg = np.zeros(shape[0]*shape[1],dtype=np.uint8)

    ix = 0  # Pixel position
    color = 0
    # Data should be sanitized here, no need to check invalid runs
    for r in data[0][3:]:
        count = r-32
        for x in range(count):
            if ix+x < pixels:
                nimg[ix+x] = color
        ix += count
        color = 0 if color == 1 else 1
        if ix == pixels:
            break
    nimg = nimg.reshape(shape)
    tmpI = Image.fromarray(nimg,mode='P')
    tmpI.putpalette(fsPal)
    return [tmpI,multi,data,gcolors,text]