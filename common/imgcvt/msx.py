#########################################3
# MSX Routines
#
import numpy as np
import os
from PIL import Image

from common.imgcvt import common as CC
from common.imgcvt import palette as Palette


#Palette structure
Palette_MSX0 = [{'color':'Transparent','RGBA':[0x00,0x00,0x00,0x00],'enabled':False,'index':0},
    {'color':'Black','RGBA':[0x00,0x00,0x00,0xff],'enabled':True,'index':1},{'color':'Medium Green','RGBA':[0x3e,0xb8,0x49,0xff],'enabled':True,'index':2},
    {'color':'Light Green','RGBA':[0x74,0xd0,0x7d,0xff],'enabled':True,'index':3},{'color':'Dark Blue','RGBA':[0x59,0x55,0xe0,0xff],'enabled':True,'index':4},
    {'color':'Light Blue','RGBA':[0x80,0x76,0xf1,0xff],'enabled':True,'index':5},{'color':'Dark Red','RGBA':[0xb9,0x5e,0x51,0xff],'enabled':True,'index':6},
    {'color':'Cyan','RGBA':[0x65,0xdb,0xef,0xff],'enabled':True,'index':7},{'color':'Medium Red','RGBA':[0xdb,0x65,0x59,0xff],'enabled':True,'index':8},
    {'color':'Light Red','RGBA':[0xff,0x89,0x7d,0xff],'enabled':True,'index':9},{'color':'Dark Yellow','RGBA':[0xcc,0xc3,0x5e,0xff],'enabled':True,'index':10},
    {'color':'Light Yellow','RGBA':[0xde,0xd0,0x87,0xff],'enabled':True,'index':11},{'color':'Dark Green','RGBA':[0x3a,0xa2,0x41,0xff],'enabled':True,'index':12},
    {'color':'Magenta','RGBA':[0xb7,0x66,0xb5,0xff],'enabled':True,'index':13},{'color':'Gray','RGBA':[0xcc,0xcc,0xcc,0xff],'enabled':True,'index':14},
    {'color':'White','RGBA':[0xff,0xff,0xff,0xff],'enabled':True,'index':15}]

Palette_MSX1 = [{'color':'Transparent','RGBA':[0x00,0x00,0x00,0x00],'enabled':False,'index':0},
    {'color':'Black','RGBA':[0x00,0x00,0x00,0xff],'enabled':True,'index':1},{'color':'Medium Green','RGBA':[0x0a,0xad,0x1e,0xff],'enabled':True,'index':2},
    {'color':'Light Green','RGBA':[0x34,0xc8,0x4c,0xff],'enabled':True,'index':3},{'color':'Dark Blue','RGBA':[0x2b,0x2d,0xe3,0xff],'enabled':True,'index':4},
    {'color':'Light Blue','RGBA':[0x51,0x4b,0xfb,0xff],'enabled':True,'index':5},{'color':'Dark Red','RGBA':[0xbd,0x29,0x25,0xff],'enabled':True,'index':6},
    {'color':'Cyan','RGBA':[0x1e,0xe2,0xef,0xff],'enabled':True,'index':7},{'color':'Medium Red','RGBA':[0xfb,0x2c,0x2b,0xff],'enabled':True,'index':8},
    {'color':'Light Red','RGBA':[0xff,0x5f,0x4c,0xff],'enabled':True,'index':9},{'color':'Dark Yellow','RGBA':[0xbd,0xa2,0x2b,0xff],'enabled':True,'index':10},
    {'color':'Light Yellow','RGBA':[0xd7,0xb4,0x54,0xff],'enabled':True,'index':11},{'color':'Dark Green','RGBA':[0x0a,0x8c,0x18,0xff],'enabled':True,'index':12},
    {'color':'Magenta','RGBA':[0xaf,0x32,0x9a,0xff],'enabled':True,'index':13},{'color':'Gray','RGBA':[0xb2,0xb2,0xb2,0xff],'enabled':True,'index':14},
    {'color':'White','RGBA':[0xff,0xff,0xff,0xff],'enabled':True,'index':15}]

MSXPalettes = [['Gamma Corrected',Palette_MSX1],['Wratt',Palette_MSX0]]

Native_Ext = ['.SC2']


def msx_get2closest(colors,p_in,p_out,fixed):
    cd = [[197000 for j in range(len(p_in))] for i in range(len(colors))]
    closest = []
    _indexes = [1,1]
    xmin = -1
    for x in range(0,len(colors)):
        for y in range(0,len(p_in)):
            if y != xmin:
                cd[x][y] = CC.Redmean(colors[x][1],p_in[y][0])  #(rd * rd + gd * gd + bd * bd)
        xmin=cd[x].index(min(cd[x]))
        cc = p_in[xmin][1]
        m = p_in[xmin][0] #p_out[cc]
        closest.append(CC.RGB24(m).tolist())
        _indexes[x] = cc
    if len(closest) == 1:
        closest.append(CC.RGB24(p_in[1][0]).tolist())
        _indexes[1]= 1
    tix = sorted(_indexes)  #Sort by color index
    if tix != _indexes:
        closest.reverse()
        _indexes = tix
    return(_indexes,Palette.Palette(closest))


def bmpacksc2(column,row,cell,buffers):
    offset = (column*8)+(row//8)*256+(row&7)
    buffers[0][offset]=list(np.packbits(np.asarray(cell,dtype='bool')))[0]

def attrpack(column,row,attr,buffers):
    offset = (column*8)+(row//8)*256+(row&7)
    buffers[2][offset]=attr[0]+(attr[1]*16) #HIRES


# Returns a list of lists
def get_buffers():
    buffers=[]
    buffers.append([0]*6144)    # [0] Bitmap
    buffers.append([i for i in range(256)]*3) # [1] Name Table
    buffers.append([0]*6144)    # [2] Colors
    return buffers

def buildfile(buffers):
    t_data = b'\xFE\x00\x00\xFF\x37\x00\x00' #Header
    #Bitmap
    t_data += bytes(buffers[0])
    #Names
    t_data += bytes([i for i in range(256)])*3
    #Sprites+unused space
    t_data+=bytes(1280)
    #Colors
    t_data += bytes(buffers[2])
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

GFX_MODES=[{'name':'MSX1 Screen 2','bpp':1,'attr':(8,1),'global_colors':(False,False),'palettes':MSXPalettes,
            'global_names':[], 'match':Palette.colordelta.CCIR,
            'in_size':(256,192),'out_size':(256,192),'get_attr':msx_get2closest,'bm_pack': bmpacksc2,'attr_pack':attrpack,
            'get_buffers':get_buffers,'save_output':[['Screen 2','.sc2',lambda buf,c: buildfile(buf)]]}]

##############################
# Load native image format
##############################
def load_Image(filename:str):
    multi = 0
    data = [None]*3
    gcolors = [0]*2  # Border, Background
    extension = os.path.splitext(filename)[1].upper()
    fsize = os.stat(filename).st_size
    #Read file
    if (extension == '.SC2') and (fsize == 14343):  # Screen 2
        with open(filename,'rb') as ifile:
            if ifile.read(7) == b'\xFE\x00\x00\xFF\x37\x00\x00':
                # Bitmap data
                data[0] = ifile.read(6144)
                # Nametable data
                data[1] = ifile.read(768)
                # Sprites/Unused data
                tmp = ifile.read(1280)
                # Color data
                data[2] = ifile.read(6144)
                text = 'MSX Screen 2'
            else:
                return None
    else:
        return None
    #Render image
    # Generate palette(s)
    rgb_in = []
    for c in Palette_MSX1: # iterate colors
        rgb_in.append(np.array(c['RGBA'][:3]))   # ignore alpha for now
    fsPal = [element for sublist in rgb_in for element in sublist]
    plen = len(fsPal)//3
    fsPal.extend(fsPal[:3]*(256-plen))

    nimg = np.empty((192,256),dtype=np.uint8)
    for c in range(768):
        nt = data[1][c]+(256*(c//256))  # Get pattern nr. from nametable
        for y in range(8):
            cell = np.unpackbits(np.array(list(data[0][(nt*8)+y:(nt*8)+y+1]),dtype=np.uint8), axis=0)
            fgbg = {0:data[2][(nt*8)+y]&15,1:data[2][(nt*8)+y]>>4}
            ncell = np.copy(cell)
            for k,v in fgbg.items():
                ncell[cell==k] = v
            sr = (int(c/32)*8)+y
            er = sr+1
            sc = (c*8)%256
            ec = sc+8
            nimg[sr:er,sc:ec] = ncell.reshape(1,8)
    tmpI = Image.fromarray(nimg,mode='P')
    tmpI.putpalette(fsPal)

    return [tmpI,multi,data,gcolors,text]