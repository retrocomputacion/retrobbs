#########################################3
# Plus4 Routines
#
import numpy as np
import os

from common.imgcvt import common as CC
from common.imgcvt import palette as Palette


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

Native_Ext = ['boti']

#HiRes
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
        m = p_in[xmin][0] #p_out[cc]
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

#Multicolor
def plus4_get4closest(colors, p_in, p_out, bgcolor):
    cd = [[0 for j in range(len(p_in))] for i in range(len(colors))]
    brgb = CC.RGB24(next(x[0].tolist() for x in p_in if x[1]==bgcolor[0]))
    brgb2 = CC.RGB24(next(x[0].tolist() for x in p_in if x[1]==bgcolor[3]))
    
    closest = [brgb,brgb,brgb,brgb]
    _indexes = [bgcolor[0],bgcolor[0],bgcolor[0],bgcolor[3]]
    #Attr
    indexes = 0#0x33
    cram = 2
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
        m = p_in[xmin][0] #p_out[cc]
        closest[xx] = CC.RGB24(m).tolist()
        _indexes[xx] = cc
        xx += 1
        if xx==3:
            break

    return(_indexes,Palette.Palette(closest))


def bmpackhi(column,row,cell,buffers):
    if len(buffers)<4:
        offset = (column*8)+(row*320)
        buffers[0][offset:offset+8]=list(np.packbits(np.asarray(cell,dtype='bool')))
    else:
        offset = ((column+3)*8)+(row//8)*320+(row&7)
        buffers[0][offset]=list(np.packbits(np.asarray(cell,dtype='bool')))[0]

def bmpackmulti(column,row,cell,buffers):
    cell_a = np.asarray(cell)
    offset = (column*8)+(row*320)
    for y in range(8):
        tbyte = 0
        for x in range(4):
            tbyte += int(cell_a[y,x])<<((3-x)*2)
        buffers[0][offset+y] = tbyte

def attrpack(column,row,attr,buffers):
    offset = column+(row*40)    #Normal
    buffers[1][offset]=(attr[0]&15)+((attr[1]&15)<<4)   #Color Table
    buffers[2][offset]=((attr[1]&112)>>4)+(attr[0]&112) #Luminance Table

def attrpackmulti(column,row,attr,buffers):
    offset = column+(row*40)    #Normal
    buffers[1][offset]=(attr[2]&15)+((attr[1]&15)<<4)   #Color Table
    buffers[2][offset]=((attr[1]&112)>>4)+(attr[2]&112) #Luminance Table

# Returns a list of lists
def get_buffers(mode:int):
    x = 1 
    buffers=[]
    buffers.append([0]*8000) # Bitmap
    buffers.append([0]*1000) # Color table
    buffers.append([0]*1000) # Luminance table
    return buffers

def buildfile(buffers,bg,baseMode):
    if baseMode == 0:   #Save bitmap memory dump
        #Luminance table
        t_data = bytes(buffers[2])#luminance table
        t_data += bytes(24)
        #Color table
        t_data += bytes(buffers[1])#color table
        t_data += bytes(24)
        #Bitmap
        t_data += bytes(buffers[0])#bitmap
        #Border
        #t_data += b'\x00'
    elif baseMode == 2: #Save Multi Botticelli
        t_data = b'\x00\x78'    #Load Address
        t_data += bytes(buffers[2])#luminance table
        t_data += bytes(22)
        t_data += bytes([((bg[3]&112)>>4)+((bg[3]&15)<<4)])
        t_data += bytes([((bg[0]&112)>>4)+((bg[0]&15)<<4)])
        #Color table
        t_data += bytes(buffers[1])#color table
        t_data += bytes(24)
        #Bitmap
        t_data += bytes(buffers[0])#bitmap
    return(t_data)
#############################

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
            'get_buffers':lambda: get_buffers(1),'save_output':[['Bitmap dump','.prg',lambda buf,c: buildfile(buf,c,0)]]},
            {'name':'Plus/4 Multicolor','bpp':2,'attr':(4,8),'global_colors':(True,False,False,True),'palettes':Plus4Palettes,
             'global_names':['Background color',None,None,'Multicolor 1'],
            'attributes':[{'dim':(160,200),'get_attr':None,'bm_pack':None,'attr_pack':None},
                        {'dim':(4,8),'get_attr':plus4_get4closest,'bm_pack':bmpackmulti,'attr_pack':attrpackmulti}],
            'in_size':(320,200),'out_size':(160,200),'get_attr':plus4_get4closest,'bm_pack':bmpackmulti,'attr_pack':attrpackmulti,
            'get_buffers':lambda: get_buffers(2),'save_output':[['Multi Botticelli','.boti',lambda buf,c:buildfile(buf,c,2)]]}]

