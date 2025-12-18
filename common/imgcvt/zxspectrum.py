#########################################3
# ZX Spectrum Routines
#
import numpy as np

import modules.common as CC
import modules.palette as Palette

#Palette structure
Palette_ZXSpectrum = [{'color':'Black','RGBA':[0x00,0x00,0x00,0xff],'enabled':True,'index':0},
    {'color':'Blue','RGBA':[0x00,0x00,0xd8,0xff],'enabled':True,'index':1},{'color':'Red','RGBA':[0xd8,0x00,0x00,0xff],'enabled':True,'index':2},
    {'color':'Magenta','RGBA':[0xd8,0x00,0xd8,0xff],'enabled':True,'index':3},{'color':'Green','RGBA':[0x00,0xd8,0x00,0xff],'enabled':True,'index':4},
    {'color':'Cyan','RGBA':[0x00,0xd8,0xd8,0xff],'enabled':True,'index':5},{'color':'Yellow','RGBA':[0xd8,0xd8,0x00,0xff],'enabled':True,'index':6},
    {'color':'White','RGBA':[0xd8,0xd8,0xd8,0xff],'enabled':True,'index':7},{'color':'Black (Bright)','RGBA':[0x00,0x00,0x00,0xff],'enabled':True,'index':8},
    {'color':'Blue (Bright)','RGBA':[0x00,0x00,0xff,0xff],'enabled':True,'index':9},{'color':'Red (Bright)','RGBA':[0xff,0x00,0x00,0xff],'enabled':True,'index':10},
    {'color':'Magenta (Bright)','RGBA':[0xff,0x00,0xff,0xff],'enabled':True,'index':11},{'color':'Green (Bright','RGBA':[0x00,0xff,0x00,0xff],'enabled':True,'index':12},
    {'color':'Cyan (Bright)','RGBA':[0x00,0xff,0xff,0xff],'enabled':True,'index':13},{'color':'Yellow (Bright)','RGBA':[0xff,0xff,0x00,0xff],'enabled':True,'index':14},
    {'color':'White (Bright)','RGBA':[0xff,0xff,0xff,0xff],'enabled':True,'index':15}]

ZXPalettes = [['ZX Spectrum',Palette_ZXSpectrum]]

#HiRes
def zx_get2closest(colors,p_in,p_out,fixed):
    cd = [[197000 for j in range(len(p_in))] for i in range(len(colors))]
    closest = []
    _indexes = [-1,-1]
    xmin = -1
    counts = [0,0]
    for x in range(0,len(colors)):
        #yr = [b for b in range(len(p_in)) if b not in _indexes] #avoid repeated indexes
        for y in range(0,len(p_in)):
            if y != xmin:
                # rd = colors[x][1][0] - p_in[y][0][0]
                # gd = colors[x][1][1] - p_in[y][0][1]
                # bd = colors[x][1][2] - p_in[y][0][2]
                cd[x][y] = CC.Redmean(colors[x][1],p_in[y][0])  #(rd * rd + gd * gd + bd * bd)
        xmin=cd[x].index(min(cd[x]))
        cc = p_in[xmin][1]
        m = p_in[xmin][0] #p_out[cc]
        closest.append(CC.RGB24(m).tolist())
        _indexes[x] = cc
        counts[x] = colors[x][0]
    if len(closest) == 1:
        closest.append(closest[0])
        _indexes[1]=_indexes[0]
    if (0 not in _indexes and 8  not in _indexes):
        if (_indexes[0]&8)^(_indexes[1]&8) == 8:
            #Selected colors have different brightness
            #Replace the one less used by toggling bit 3
            mi = counts.index(min(counts))
            tmp = _indexes[mi]^8
            m = [a[0] for a in p_in if a[1]==tmp]
            if len(m)!=0:
                _indexes[mi] = tmp
                closest[mi] = CC.RGB24(m[0]).tolist()
            else:
                #The color we tried to replace it with is not enabled in the palette
                #try replacing the other color
                mi = counts.index(max(counts))
                tmp = _indexes[mi]^8
                m = [a[0] for a in p_in if a[1]==tmp]
                if len(m)!=0:
                    _indexes[mi] = tmp
                    closest[mi] = CC.RGB24(m[0]).tolist()
                else:
                    #No color can be replaced with the opposite brightness
                    #Remove the least used color altogether
                    tmp = _indexes[mi]
                    _indexes = [tmp for x in _indexes]
                    tmp = closest[mi]
                    closest = [tmp for x in closest]
    return(_indexes,Palette.Palette(closest))

def bmpackhi(column,row,cell,buffers):
    offset = column+(((row%8)*32)+(2048*((row*256)//2048)))
    char=list(np.packbits(np.asarray(cell,dtype='bool')))
    for i in range(0,2048,256):
        #print(offset+i)
        buffers[0][offset+i]=char[i//256]


def attrpack(column,row,attr,buffers):
    offset = column+(32*row)
    bright = (attr[0]&8|attr[1]&8) << 3 #Bright attribute
    paper = (attr[0]&7) << 3 # Paper
    ink = attr[1]&7
    buffers[1][offset]=bright|paper|ink

# Returns a list of lists
def get_buffers():
    buffers=[]
    buffers.append([0]*6144)    # Bitmap
    buffers.append([0xf0]*768)    # Attributes
    return buffers

def buildfile(buffers):
    t_data = bytes(buffers[0])#bitmap
    t_data += bytes(buffers[1])#attributes
    return(t_data)
#############################

#####################################################################################################################
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

GFX_MODES=[{'name':'ZX Spectrum','bpp':1,'attr':(8,8),'global_colors':(False,False),'palettes':ZXPalettes,
            'global_names':[],
            'in_size':(256,192),'out_size':(256,192),'get_attr':zx_get2closest,'bm_pack': bmpackhi,'attr_pack':attrpack,
            'get_buffers': get_buffers,'save_output':[['ZX Spectrum .scr','.scr',lambda buf,c: buildfile(buf)]]},
            {'name':'ZX Spectrum unrestricted','bpp':4,'attr':(0,0),'global_colors':(False,False),'palettes':ZXPalettes,
             'global_names':[],
            'in_size':(256,192),'out_size':(256,192),'get_attr': None,'bm_pack': None,'attr_pack': None,
            'get_buffers': None,'save_output': None}]

