##################
# C64 Routines
##################
import numpy as np
import os
from PIL import Image

from common.imgcvt import common as CC
from common.imgcvt import palette as Palette
from common.imgcvt.types import gfxmodes

# Palette structure
Palette_Colodore = [{'color':'Black','RGBA':[0x00,0x00,0x00,0xff],'enabled':True,'index':0},
    {'color':'White','RGBA':[0xff,0xff,0xff,0xff],'enabled':True,'index':1},{'color':'Red','RGBA':[0x96,0x28,0x2e,0xff],'enabled':True,'index':2},
    {'color':'Cyan','RGBA':[0x5b,0xd6,0xce,0xff],'enabled':True,'index':3},{'color':'Purple','RGBA':[0x9f,0x2d,0xad,0xff],'enabled':True,'index':4},
    {'color':'Green','RGBA':[0x41,0xb9,0x36,0xff],'enabled':True,'index':5},{'color':'Blue','RGBA':[0x27,0x24,0xc4,0xff],'enabled':True,'index':6},
    {'color':'Yellow','RGBA':[0xef,0xf3,0x47,0xff],'enabled':True,'index':7},{'color':'Orange','RGBA':[0x9f,0x48,0x15,0xff],'enabled':True,'index':8},
    {'color':'Brown','RGBA':[0x5e,0x35,0x00,0xff],'enabled':True,'index':9},{'color':'Pink','RGBA':[0xda,0x5f,0x66,0xff],'enabled':True,'index':10},
    {'color':'Dark Grey','RGBA':[0x47,0x47,0x47,0xff],'enabled':True,'index':11},{'color':'Medium Grey','RGBA':[0x78,0x78,0x78,0xff],'enabled':True,'index':12},
    {'color':'Light Green','RGBA':[0x91,0xff,0x84,0xff],'enabled':True,'index':13},{'color':'Light Blue','RGBA':[0x68,0x64,0xff,0xff],'enabled':True,'index':14},
    {'color':'Light Grey','RGBA':[0xae,0xae,0xae,0xff],'enabled':True,'index':15}]

Palette_PeptoNTSC = [{'color':'Black','RGBA':[0x00,0x00,0x00,0xff],'enabled':True,'index':0},
    {'color':'White','RGBA':[0xff,0xff,0xff,0xff],'enabled':True,'index':1},{'color':'Red','RGBA':[0x7C,0x35,0x2B,0xff],'enabled':True,'index':2},
    {'color':'Cyan','RGBA':[0x5A,0xA6,0xB1,0xff],'enabled':True,'index':3},{'color':'Purple','RGBA':[0x69,0x41,0x85,0xff],'enabled':True,'index':4},
    {'color':'Green','RGBA':[0x5D,0x86,0x43,0xff],'enabled':True,'index':5},{'color':'Blue','RGBA':[0x21,0x2E,0x78,0xff],'enabled':True,'index':6},
    {'color':'Yellow','RGBA':[0xCF,0xBE,0x6F,0xff],'enabled':True,'index':7},{'color':'Orange','RGBA':[0x89,0x4A,0x26,0xff],'enabled':True,'index':8},
    {'color':'Brown','RGBA':[0x5B,0x33,0x00,0xff],'enabled':True,'index':9},{'color':'Pink','RGBA':[0xAF,0x64,0x59,0xff],'enabled':True,'index':10},
    {'color':'Dark Grey','RGBA':[0x43,0x43,0x43,0xff],'enabled':True,'index':11},{'color':'Medium Grey','RGBA':[0x6b,0x6b,0x6b,0xff],'enabled':True,'index':12},
    {'color':'Light Green','RGBA':[0xA0,0xCB,0x84,0xff],'enabled':True,'index':13},{'color':'Light Blue','RGBA':[0x56,0x65,0xB3,0xff],'enabled':True,'index':14},
    {'color':'Light Grey','RGBA':[0x95,0x95,0x95,0xff],'enabled':True,'index':15}]

C64Palettes = [['Colodore',Palette_Colodore],['Pepto (NTSC,Sony)',Palette_PeptoNTSC]]

Native_Ext = ['.KOA','.KLA','.ART','.OCP','.DD','.DDL','.GG']

##########################
# Get 2 closest colors
##########################
def c64_get2closest(colors,p_in,p_out,fixed):
    cd = [[197000 for j in range(len(p_in))] for i in range(len(colors))]
    closest = []
    _indexes = [1,1]
    xmin = -1
    for x in range(0,len(colors)):
        for y in range(0,len(p_in)):
            if y != xmin:
                cd[x][y] = CC.Redmean(colors[x][1],p_in[y][0])
        xmin=cd[x].index(min(cd[x]))
        cc = p_in[xmin][1]
        m = p_in[xmin][0]
        closest.append(CC.RGB24(m).tolist())
        _indexes[x] = cc
    if len(closest) == 1:
        closest.append(CC.RGB24(p_in[0][0]).tolist())
        _indexes[1]= 0
    tix = sorted(_indexes)  # Sort by color index
    if tix != _indexes:
        closest.reverse()
        _indexes = tix
    return(_indexes,Palette.Palette(closest))

##########################
# Get 4 closest colors
##########################
def c64_get4closest(colors, p_in, p_out, bgcolor):
    cd = [[0 for j in range(len(p_in))] for i in range(len(colors))]
    brgb = CC.RGB24(next(x[0].tolist() for x in p_in if x[1]==bgcolor[0]))
    closest = [brgb,brgb,brgb,brgb]
    _indexes = [bgcolor[0],bgcolor[0],bgcolor[0],bgcolor[0]]
    # Find least used color
    if len(colors) >= 4:
        bi = colors.index(min(colors))
    else:
        bi = 5
    xx = 1
    for x in range(0,len(colors)):
        if x == bi:
            continue
        for y in range(0,len(p_in)):
            cd[x][y] = CC.Redmean(colors[x][1],p_in[y][0])
        xmin=cd[x].index(min(cd[x]))
        cc = p_in[xmin][1]
        m = p_in[xmin][0]
        closest[xx] = CC.RGB24(m).tolist()
        _indexes[xx] = cc
        xx += 1
    return(_indexes,Palette.Palette(closest))

############################
# Pack Hires bitmap cell
############################
def bmpackhi(column,row,cell,buffers):
    if len(buffers)<4:
        offset = (column*8)+(row*320)
        buffers[0][offset:offset+8]=list(np.packbits(np.asarray(cell,dtype='bool')))
    else:
        offset = ((column+3)*8)+(row//8)*320+(row&7)
        buffers[0][offset]=list(np.packbits(np.asarray(cell,dtype='bool')))[0]

#################################
# Pack multicolor bitmap cell
#################################
def bmpackmulti(column,row,cell,buffers):
    cell_a = np.asarray(cell)
    offset = (column*8)+(row*320)
    for y in range(8):
        tbyte = 0
        for x in range(4):
            tbyte += int(cell_a[y,x])<<((3-x)*2)
        buffers[0][offset+y] = tbyte

#########################
# Pack attribute cell
#########################
def attrpack(column,row,attr,buffers):
    if len(buffers) < 4:
        offset = column+(row*40)    # Normal
    else:
        offset = column+3+((row//8)*40) # (A)FLI
    if len(attr) == 2:
        if len(buffers) == 2:
            buffers[1][offset]=attr[0]+(attr[1]*16) # HIRES
        else:
            buffers[1+(row % 8)][offset]=attr[0]+(attr[1]*16) # AFLI
    else:
        buffers[1][offset]=attr[2]+(attr[1]*16)
        buffers[2][offset]=attr[3]

###################################
# Get buffers to store raw data
# Returns a list of lists
###################################
def get_buffers(mode:int):
    if mode == 3:
        x = 8
    else:
        x = 1 
    buffers=[]
    buffers.append([0]*8000)    # Bitmap
    for i in range(x):
        buffers.append([0xf0]*1000)    # Screen RAM(s)
    if mode == 2:
        buffers.append([0]*1000)    # Color RAM
    return buffers

#################################################
# Build a native image file from the raw data
#################################################
def buildfile(buffers,gcols,baseMode,filename):
    if baseMode == 1:   # Save Koala
        t_data = b'\x00\x60' # Load address
        # Bitmap
        t_data += bytes(buffers[0])
        # Screen
        t_data += bytes(buffers[1])
        # ColorRAM
        t_data += bytes(buffers[2])
        # Background
        t_data += gcols[1].to_bytes(1,'big')
        filename = '\x81PIC A ' + filename[:9]
    elif baseMode == 0:   # Save ArtStudio
        t_data = b'\x00\x20' # Load address
        # Bitmap
        t_data += bytes(buffers[0])
        # Screen
        t_data += bytes(buffers[1])
        # Border
        t_data += gcols[0].to_bytes(1,'big')
        # Padding
        t_data += b"M 'STU"
        filename = (filename.ljust(13,' ') if len(filename)<13 else filename[:13])+'PIC'
    return(t_data, filename)

#######################################################################################################################
# Graphic modes structure
# name: Name displayed in the combobox
# bpp: bits per pixel
# attr: attribute size in pixels
# global_colors: a boolean tuple of 2^bpp elements, True if the color for that index is global for the whole screen
# palettes: a list of name/palette pairs
#
# This field is for the planned rewrite of the conversion routine(s), unused right now.
# attributes: list of attributes:
#               dim: area this/these attributes cover
#               get_attr: function call to get closest color(s) for an attribute cell
#               bm_pack:  function call to pack the bitmap from 8bpp into the native format order (optional)
#               attr_pack: function call to pack the individual cell color(s) into attribute byte(s) (optional)
#               Need more fields to set GUI options -> name and get best color    
#
# in_size: input image dimensions, converted image will also be displayed with these dimensions
# out_size: native image dimensions
# get_attr: function call to get closest colors for an attribute cell
# bm_pack:  function call to pack the bitmap from 8bpp into the native format order
# attr_pack: function call to pack the individual cell colors into attribute byte(s)
# get_buffers: function call returns the native bitmap and attribute buffers
# save_output: a list of lists in the format ['name','extension',save_function]
#######################################################################################################################

GFX_MODES=[{'name':'C64 HiRes','bpp':1,'attr':(8,8),'global_colors':(False,False),'palettes':C64Palettes,
            'global_names':[],
            'attributes':[{'dim':(8,8),'get_attr':c64_get2closest,'bm_pack':bmpackhi,'attr_pack':attrpack}],
            'in_size':(320,200),'out_size':(320,200),'get_attr':c64_get2closest,'bm_pack':bmpackhi,'attr_pack':attrpack,
            'get_buffers':lambda: get_buffers(1),'save_output':['Art Studio',lambda buf,c,fn: buildfile(buf,c,0,fn)]},
            {'name':'C64 Multicolor','bpp':2,'attr':(4,8),'global_colors':(True,False,False,False),'palettes':C64Palettes,
             'global_names':['Background color'],
            'attributes':[{'dim':(160,200),'get_attr':None,'bm_pack':None,'attr_pack':None},
                        {'dim':(4,8),'get_attr':c64_get4closest,'bm_pack':bmpackmulti,'attr_pack':attrpack}],
            'in_size':(320,200),'out_size':(160,200),'get_attr':c64_get4closest,'bm_pack':bmpackmulti,'attr_pack':attrpack,
            'get_buffers':lambda: get_buffers(2),'save_output':['Koala Paint',lambda buf,c,fn:buildfile(buf,c,1,fn)]}]


##############################
# Load native image format
##############################
def load_Image(filename:str):
    multi = gfxmodes.C64HI
    data = [None]*3
    gcolors = [0]*2  # Border, Background
    extension = os.path.splitext(filename)[1].upper()
    fsize = os.stat(filename).st_size
    # Read file
    if (extension == '.ART') and (fsize == 9009):  # Art Studio
        with open(filename,'rb') as ifile:
            if ifile.read(2) == b'\x00\x20':
                # Bitmap data
                data[0] = ifile.read(8000)
                # Screen data
                data[1] = ifile.read(1000)
                # Read border color
                gcolors[0] = ifile.read(1)[0]
                text = 'Art Studio'
            else:
                return None
    elif (extension in ['.DD','.DDL']) and (fsize == 9218): # Doodle
        with open(filename,'rb') as ifile:
            if ifile.read(2) == b'\x00\x5c':
                # Screen data
                data[1] = ifile.read(1000)
                # Skip
                ifile.read(24)
                # Bitmap data
                data[0] = ifile.read(8000)
                gcolors[0] = 0x0c    # Border color
                text = 'Doodle'
            else:
                return None
    elif (extension == '.OCP') and (fsize == 10018):
        with open(filename,'rb') as ifile:
            if ifile.read(2) == b'\x00\x20':
                # Bitmap data
                data[0] = ifile.read(8000)
                # Screen data
                data[1] = ifile.read(1000)
                # Read border color
                gcolors[0] = ifile.read(1)[0]
                # Read background color
                gcolors[1] = ifile.read(1)[0]
                # Skip the next 14 bytes
                ifile.read(14)
                # Color data
                data[2] = ifile.read(1000)
                multi = gfxmodes.C64MULTI
                text = 'Advanced Art Studio'
            else:
                return None
    elif (extension in ['.KOA','.KLA']) and (fsize == 10003):
        with open(filename,'rb') as ifile:
            if ifile.read(2) == b'\x00\x60':
                # Bitmap data
                data[0] = ifile.read(8000)
                # Screen data
                data[1] = ifile.read(1000)
                # Color data
                data[2] = ifile.read(1000)
                # Read background color
                gcolors[1] = ifile.read(1)[0]
                gcolors[0] = gcolors[1]
                multi = gfxmodes.C64MULTI
                text = 'Koala Paint'
            else:
                return None
    elif (extension == '.GG'):  # RLE encoded KoalaPainter
        with open(filename,'rb') as ifile:
            if ifile.read(2) == b'\x00\x60':
                c_buffer = ifile.read()
                d_buffer = b''
                run = 0
                d_index = 0
                repeat = 0
                for v in c_buffer:
                    if run == 0:  # Literal or escape
                        if v == 254:    # escape
                            run = 1
                            continue
                        d_buffer = d_buffer + v.to_bytes(1,'big')   # literal
                    elif run == 1:  # repeat byte
                        run = 2
                        repeat = v
                    else:
                        for i in range(v):  #repeat count
                            d_buffer = d_buffer + repeat.to_bytes(1,'big')
                        run = 0
                data[0] = d_buffer[:8000]
                data[1] = d_buffer[8000:9000]
                data[2] = d_buffer[9000:10000]
                gcolors[1] = d_buffer[10000]
                gcolors[0] = gcolors[1]
                multi = gfxmodes.C64MULTI
                text = 'Koala Paint (RLE)'
            else:
                return None
    else:
        return None
    # Render image
    # Generate palette(s)
    rgb_in = []
    for c in Palette_Colodore: # iterate colors
        rgb_in.append(np.array(c['RGBA'][:3]))   # ignore alpha for now
    fsPal = [element for sublist in rgb_in for element in sublist]
    plen = len(fsPal)//3
    fsPal.extend(fsPal[:3]*(256-plen))
    if multi == gfxmodes.C64HI:
        nimg = np.empty((200,320),dtype=np.uint8)
        for c in range(1000):
            cell = np.unpackbits(np.array(list(data[0][c*8:(c+1)*8]),dtype=np.uint8), axis=0)
            fgbg = {0:data[1][c]&15,1:data[1][c]>>4}
            ncell = np.copy(cell)
            for k,v in fgbg.items():
                ncell[cell==k] = v
            sr = int(c/40)*8
            er = sr+8
            sc = (c*8)%320
            ec = sc+8
            nimg[sr:er,sc:ec] = ncell.reshape(8,8)
        tmpI = Image.fromarray(nimg,mode='P')
        tmpI.putpalette(fsPal)
    else:
        nimg = np.empty((200,160),dtype=np.uint8)
        for c in range(1000):
            cell = np.array([[(data[0][(c*8)+x]>>6)&3,(data[0][(c*8)+x]>>4)&3,(data[0][(c*8)+x]>>2)&3,data[0][(c*8)+x]&3] for x in range(8)],dtype=np.uint8).reshape((32))
            fgbg = {0:gcolors[1],2:data[1][c]&15,1:data[1][c]>>4,3:data[2][c]}
            ncell = np.copy(cell)
            for k,v in fgbg.items():
                ncell[cell==k] = v
            sr = int(c/40)*8
            er = sr+8
            sc = (c*4)%160
            ec = sc+4
            nimg[sr:er,sc:ec] = ncell.reshape(8,4)
        tmpI = Image.fromarray(nimg,mode='P').resize((320,200),Image.NEAREST)
        tmpI.putpalette(fsPal)
    return [tmpI,multi,data,gcolors,text]