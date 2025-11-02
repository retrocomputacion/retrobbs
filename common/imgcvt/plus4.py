#########################################3
# Plus4 Routines
#
import numpy as np
import os
from PIL import Image

from common.imgcvt import common as CC
from common.imgcvt import palette as Palette
from common.imgcvt.types import gfxmodes

# TED YCbCr Values, Derived from Yape/VICE
TED_luminances = [0.125, 0.1875, 0.25, 0.3125, 0.46875, 0.5625, 0.75, 1]	#VICE luminances

# Yape CbCr values derived from RGB table at luminance = 1
CbCr_TED = [[0,0],[0,0],[-0.0516623,0.1640681],[0.0509762,-0.1565439],[0.1222589,0.1209588],[-0.1215972,-0.1229196],[0.1692892,-0.0293838],[-0.1267406,0.0076390],
             [-0.1187715,0.1267993],[-0.1250720,0.0740819],[-0.1258353,-0.0499566],[0.0502255,0.1641772],[-0.0189016,-0.1581522],[0.1382575,-0.1021706],[0.1710308,0.0203686],[-0.1230180,-0.0967441]]

YCbCr_TED = [[TED_luminances[i] if j != 0 else 0,CbCr_TED[j][0],CbCr_TED[j][1]] for i in range(len(TED_luminances)) for j in range(len(CbCr_TED)) ]

TED_names = ['Black','White','Red','Cyan','Purple','Green','Blue','Yellow','Orange','Brown','Yellow-Green','Pink','Blue-Green','Light Blue','Dark Blue','Light Green']

Blacks = [i for i in range(0,128,16)]	# All black indexes

#Palette structure
Palette_TED = [{'color':TED_names[ix%16]+str(ix//16),'RGBA':[max(0,min(int((i[0] + (i[2]*1.402))*255),255)),
            max(0,min(int((i[0] + ((i[1]*-0.344136) + (i[2]*-0.714136)))*255),255)),
            max(0,min(int((i[0] + (i[1]*1.772))*255),255)),0xff], 'enabled':True, 'index':ix} for ix,i in enumerate(YCbCr_TED)]

Plus4Palettes = [['Plus/4',Palette_TED]]

Native_Ext = ['.BOTI']

################################################
# Get 2 closest colors
################################################
def plus4_get2closest(colors,p_in,p_out,fixed):
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
    tix = sorted(_indexes)  #Sort by color index
    if tix != _indexes:
        closest.reverse()
        _indexes = tix
    return(_indexes,Palette.Palette(closest))

#####################################################
# Get 4 closest colors
#####################################################
def plus4_get4closest(colors, p_in, p_out, bgcolor):
    cd = [[0 for j in range(len(p_in))] for i in range(len(colors))]
    brgb = CC.RGB24(next(x[0].tolist() for x in p_in if x[1]==bgcolor[0]))
    brgb2 = CC.RGB24(next(x[0].tolist() for x in p_in if x[1]==bgcolor[3]))
    closest = [brgb,brgb,brgb,brgb2]
    _indexes = [bgcolor[0],bgcolor[0],bgcolor[0],bgcolor[3]]
    #Find least used color
    bi = []
    tc = colors.copy()
    for i in range(2):
        if len(tc) >= 3:
            bi.append(tc.index(min(tc)))
            tc.pop(tc.index(min(tc)))
    xx = 1
    for x in range(0,len(colors)):
        if x in bi:
            continue
        for y in range(0,len(p_in)):
            cd[x][y] = CC.Redmean(colors[x][1],p_in[y][0])
        xmin=cd[x].index(min(cd[x]))
        cc = p_in[xmin][1]
        m = p_in[xmin][0]
        closest[xx] = CC.RGB24(m).tolist()
        _indexes[xx] = cc
        xx += 1
        if xx==3:
            break
    return(_indexes,Palette.Palette(closest))

#######################################
# Pack Hires bitmap cell
#######################################
def bmpackhi(column,row,cell,buffers):
    if len(buffers)<4:
        offset = (column*8)+(row*320)
        buffers[0][offset:offset+8]=list(np.packbits(np.asarray(cell,dtype='bool')))
    else:
        offset = ((column+3)*8)+(row//8)*320+(row&7)
        buffers[0][offset]=list(np.packbits(np.asarray(cell,dtype='bool')))[0]

##########################################
# Pack multicolor bitmap cell
##########################################
def bmpackmulti(column,row,cell,buffers):
    cell_a = np.asarray(cell)
    offset = (column*8)+(row*320)
    for y in range(8):
        tbyte = 0
        for x in range(4):
            tbyte += int(cell_a[y,x])<<((3-x)*2)
        buffers[0][offset+y] = tbyte

#######################################
# Pack Hires attribute cell
#######################################
def attrpack(column,row,attr,buffers):
    offset = column+(row*40)    #Normal
    buffers[1][offset]=(attr[0]&15)+((attr[1]&15)<<4)   #Color Table
    buffers[2][offset]=((attr[1]&112)>>4)+(attr[0]&112) #Luminance Table

############################################
# Pack multicolor attribute cell
############################################
def attrpackmulti(column,row,attr,buffers):
    offset = column+(row*40)    #Normal
    buffers[1][offset]=(attr[2]&15)+((attr[1]&15)<<4)   #Color Table
    buffers[2][offset]=((attr[1]&112)>>4)+(attr[2]&112) #Luminance Table

################################
# Get buffers to store raw data
# Returns a list of lists
################################
def get_buffers(mode:int):
    x = 1 
    buffers=[]
    buffers.append([0]*8000) # Bitmap
    buffers.append([0]*1000) # Color table
    buffers.append([0]*1000) # Luminance table
    return buffers

##############################################
# Build a native image file from the raw data
##############################################
def buildfile(buffers,bg,baseMode, filename):
    t_data = b'\x00\x78'    #Load Address
    t_data += bytes(buffers[2])#luminance table
    t_data += bytes(18)
    if baseMode == 0:
        t_data += bytes(6)
        filename = "G."+filename[:14]
    else:
        t_data += b'MULT'
        t_data += bytes([((bg[4]&112)>>4)+((bg[4]&15)<<4)])
        t_data += bytes([((bg[1]&112)>>4)+((bg[1]&15)<<4)])
        filename = 'M.'+filename[:14]
    #Color table
    t_data += bytes(buffers[1])#color table
    t_data += bytes(24)
    #Bitmap
    t_data += bytes(buffers[0])#bitmap
    return(t_data,filename)

#####################################################################################################################
# Graphic modes structure
# name: Name displayed in the combobox
# bpp: bits per pixel
# attr: attribute size in pixels
# global_colors: a boolean tuple of 2^bpp elements, True if the color for that index is global for the whole screen
# palettes: a list of name/palette pairs

# This field is for the planned rewrite of the conversion routine(s), unused right now.
# attributes: list of attributes:
#               dim: dimension this/these attributes cover
#               get_attr: function call to get closest color(s) for an attribute cell
#               bm_pack:  function call to pack the bitmap from 8bpp into the native format order (optional)
#               attr_pack: function call to pack the individual cell color(s) into attribute byte(s) (optional)
#               Need more fields to set GUI options -> name and get best color    

# in_size: input image dimensions, converted image will also be displayed with these dimensions
# out_size: native image dimensions
# get_attr: function call to get closest colors for an attribute cell
# bm_pack:  function call to pack the bitmap from 8bpp into the native format order
# attr_pack: function call to pack the individual cell colors into attribute byte(s)
# get_buffers: function call returns the native bitmap and attribute buffers
# save_output: a list of lists in the format ['name','extension',save_function]

GFX_MODES=[{'name':'Plus/4 HiRes','bpp':1,'attr':(8,8),'global_colors':(False,False),'palettes':Plus4Palettes,
            'global_names':[],
            'attributes':[{'dim':(8,8),'get_attr':plus4_get2closest,'bm_pack':bmpackhi,'attr_pack':attrpack}],
            'in_size':(320,200),'out_size':(320,200),'get_attr':plus4_get2closest,'bm_pack':bmpackhi,'attr_pack':attrpack,
            'get_buffers':lambda: get_buffers(1),'save_output':['Botticelli',lambda buf,c,fn: buildfile(buf,c,0,fn)]},
            {'name':'Plus/4 Multicolor','bpp':2,'attr':(4,8),'global_colors':(True,False,False,True),'palettes':Plus4Palettes,
             'global_names':['Background color',None,None,'Multicolor 1'],
            'attributes':[{'dim':(160,200),'get_attr':None,'bm_pack':None,'attr_pack':None},
                        {'dim':(4,8),'get_attr':plus4_get4closest,'bm_pack':bmpackmulti,'attr_pack':attrpackmulti}],
            'in_size':(320,200),'out_size':(160,200),'get_attr':plus4_get4closest,'bm_pack':bmpackmulti,'attr_pack':attrpackmulti,
            'get_buffers':lambda: get_buffers(2),'save_output':['Multi Botticelli',lambda buf,c,fn:buildfile(buf,c,2,fn)]}]

##############################
# Load native image format
##############################
def load_Image(filename:str):
    multi = gfxmodes.P4HI
    data = [None]*3
    gcolors = [0]*5 # Border, Background, MC1, MC2, MC3
    extension = os.path.splitext(filename)[1].upper()
    fsize = os.stat(filename).st_size
    #Read file
    if (extension == '.BOTI') and (fsize == 10050):  # Botticelli
        with open(filename,'rb') as ifile:
            if ifile.read(2) == b'\x00\x78':
                # Luminance data
                data[2] = ifile.read(1000)  # Offset $0002 : Luminance data
                # Skip
                ifile.read(17)              # Offset $03EA : Unused 17 bytes
                tmp = ifile.read(1)[0]      # Offset $03FB : Custom border color *** NOT STANDARD on Botticelli format!!! ***
                gcolors[0] = ((tmp&240)>>4)+((tmp&15)<<4)
                # Multicolor ID
                tmp = ifile.read(4)         # Offset $03FC : Multi-Botticelli ID string
                if tmp == b'MULT':
                    # Multicolor 3
                    tmp = ifile.read(1)[0]  # Offset $0400 : Multicolor 3
                    gcolors[4] = ((tmp&240)>>4)+((tmp&15)<<4)
                    # Background
                    tmp = ifile.read(1)[0]  # Offset $0401 : Background color
                    gcolors[1] = ((tmp&240)>>4)+((tmp&15)<<4)
                    multi = gfxmodes.P4MULTI
                    text = 'Multi-Botticelli'
                else:
                    # Skip
                    ifile.read(2)           # Offset $0400 : Unused 2 bytes
                    text = 'Botticelli'
                # Color data
                data[1] = ifile.read(1000)  # Offset $0402 : Color data
                # Skip
                ifile.read(24)              # Offset $07EA : Unused 24 bytes
                # Bitmap data
                data[0] = ifile.read(8000)  # Offset $0802 : Bitmap
    else:
        return None
    #Render image
    # Generate palette(s)
    rgb_in = []
    for c in Palette_TED: # iterate colors
        rgb_in.append(np.array(c['RGBA'][:3]))   # ignore alpha for now
    fsPal = [element for sublist in rgb_in for element in sublist]
    plen = len(fsPal)//3
    fsPal.extend(fsPal[:3]*(256-plen))
    if multi == gfxmodes.P4HI:
        nimg = np.empty((200,320),dtype=np.uint8)
        for c in range(1000):
            cell = np.unpackbits(np.array(list(data[0][c*8:(c+1)*8]),dtype=np.uint8), axis=0)
            fgbg = {0:(data[1][c]&15)|(data[2][c]&112),1:(data[1][c]>>4)|((data[2][c]&15)<<4)}
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
            fgbg = {0:gcolors[1],1:(data[1][c]>>4)|((data[2][c]&15)<<4),2:(data[1][c]&15)|(data[2][c]&112),3:gcolors[4]}
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
    if gcolors[0] == 0:
        # Select border color
        # Get color counts of the border-adyacent cells
        im_top = dict(tmpI.crop((0,0,319,7)).getcolors())
        im_top = dict(zip(im_top.values(),im_top.keys()))
        im_left = dict(tmpI.crop((0,0,7,199)).getcolors())
        im_left = dict(zip(im_left.values(),im_left.keys()))
        im_bottom = dict(tmpI.crop((0,192,319,199)).getcolors())
        im_bottom = dict(zip(im_bottom.values(),im_bottom.keys()))
        im_right = dict(tmpI.crop((312,0,319,199)).getcolors())
        im_right = dict(zip(im_right.values(),im_right.keys()))
        for i in im_right:
            if i not in im_top:
                im_top[i] = 0
        for i in im_bottom:
            if i not in im_top:
                im_top[i] = 0
        for i in im_left:
            if i not in im_top:
                im_top[i] = 0

        for i in im_top:
            # Add color counts
            if i in im_left:
                im_top[i] += im_left[i]
            if i in im_bottom:
                im_top[i] += im_bottom[i]
            if i in im_right:
                im_top[i] += im_right[i]
        ccount = list(im_top.values())
        gcolors[0] = list(im_top.keys())[ccount.index(max(ccount))]

    return [tmpI,multi,data,gcolors,text]