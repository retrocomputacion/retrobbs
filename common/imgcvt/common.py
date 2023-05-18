##############################
# Common routines/variables

import math

#R,G,B to 24bit
RGB24= lambda rgb: rgb[2]+rgb[1]*256+rgb[0]*65536

#R,G,B to luminance
Luma= lambda rgb: round(rgb[0]*0.2126+rgb[1]*0.7152+rgb[2]*0.0722)

bundle_dir = ''

EDist= lambda c1,c2: math.sqrt((c1[0]-c2[0])**2)+((c1[1]-c2[1])**2)+((c1[2]-c2[2])**2)   #Euclidean distance

def Redmean(c1,c2):
    rmean = (c1[0]+c2[0]) // 2
    r = c1[0]-c2[0]
    g = c1[1]-c2[1]
    b = c1[2]-c2[2]
    return math.sqrt((((512+rmean)*r*r)>>8) + 4*g*g + (((767-rmean)*b*b)>>8))

def DeltaE(c1,c2):
    L1 = Y1 = (13933 * c1[0] + 46871 * c1[1] + 4732 * c1[2]) // 65536
    A1 = 377 * (14503 * c1[0]-22218 * c1[1] + 7714 * c1[2]) // 16777216 + 128
    b1 = (12773 * c1[0] + 39695 * c1[1]-52468 * c1[2]) // 16777216 + 128
    L2 = Y2 = (13933 * c2[0] + 46871 * c2[1] + 4732 * c2[2]) // 65536
    A2 = 377 * (14503 * c2[0]-22218 * c2[1] + 7714 * c2[2]) // 16777216 + 128
    b2 = (12773 * c2[0] + 39695 * c2[1]-52468 * c2[2]) // 16777216 + 128
    return math.sqrt((L2-L1)**2+(A2-A1)**2+(b2-b1)**2)
    