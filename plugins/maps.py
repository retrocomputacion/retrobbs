
import math
import requests
import json
import string
from io import BytesIO
from PIL import Image
from common.connection import Connection
from common.bbsdebug import _LOG
from common.imgcvt import gfxmodes, ColorProcess, dithertype
from common import filetools as FT
from common import turbo56k as TT
from common import petscii as P
from geopy.geocoders import Photon, Nominatim

#############################
#Plugin setup
def setup():
    fname = "MAPS" #UPPERCASE function name for config.ini
    parpairs = [] #config.ini Parameter pairs (name,defaultvalue)
    return(fname,parpairs)


def deg2num(lat_deg, lon_deg, zoom):
  lat_rad = math.radians(lat_deg)
  n = 2.0 ** zoom
  xtile = int((lon_deg + 180.0) / 360.0 * n)
  ytile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
  return (xtile, ytile)
  
def num2deg(xtile, ytile, zoom):
  n = 2.0 ** zoom
  lon_deg = xtile / n * 360.0 - 180.0
  lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
  lat_deg = math.degrees(lat_rad)
  return (lat_deg, lon_deg)
  
def lat2res(lat_deg, zoom):
    dptx = 360/(2**zoom)    #degrees per tile, x
    dpty = dptx*math.cos(math.radians(lat_deg)) #y (latitude)
    dppx = dptx/256 #degrees per pixel, x
    dppy = dpty/256 #degrees per pixel, y
    return dptx, dpty, dppx, dppy

def plugFunction(conn:Connection):

    _dec = conn.encoder.decode

    # Avoid Geocode timeout/Unavailable errors
    # https://gis.stackexchange.com/questions/173569/avoid-time-out-error-nominatim-geopy-openstreetmap
    def do_geocode(location, attempt=1, max_attempts=5):
        try:
            return geoLoc.geocode(location,language=conn.bbs.lang)
        except:
            if attempt <= max_attempts:
                return do_geocode(location, attempt=attempt+1)
            return None

    def getImageCluster(xmin, ymin, width, height, zoom):
        smurl = r"https://stamen-tiles.a.ssl.fastly.net/toner/{0}/{1}/{2}.png"
        tnum = 2**zoom #Number of tiles per row/column
        
        Cluster = Image.new('RGB',((width)*256,(height)*256))
        conn.SendTML('<GREY1><CLR>Loading .........<CRSRL n=9>')
        for xtile in range((xmin-int(width/2)), (xmin+1+int(width/2))):
            for ytile in range(ymin-int(height/2),  ymin+1+int(height/2)):
                try:
                    imgurl=smurl.format(zoom, xtile % tnum, ytile)
                    imgstr = requests.get(imgurl,allow_redirects=True)
                    tile = Image.open(BytesIO(imgstr.content))
                    Cluster.paste(tile, box=((xtile-(xmin-int(width/2)))*256 ,  (ytile-(ymin-int(height/2)))*256))
                    conn.SendTML('<GREEN><CHECKMARK>')
                except:
                    conn.SendTML('<RED>X')
                    _LOG("MAPS: Error, couldn't load tile",id=conn.id,v=1)
        return Cluster

    keys = string.ascii_letters + string.digits + ' +-_,.$%&'

    geoserver = conn.bbs.PlugOptions.get('geoserver','Nominatim')

    if geoserver == 'Photon':
        geoLoc = Photon(user_agent="RetroBBS-Maps")
    else:
        geoLoc = Nominatim(user_agent="RetroBBS-Maps")


    FT.SendBitmap(conn,'plugins/maps_intro.png', gfxmode = gfxmodes.C64HI, preproc=ColorProcess(), display=False, dither=dithertype.NONE)
    conn.SendTML('<SPLIT row=24><YELLOW><CLR>Location:')
    locqry = _dec(conn.ReceiveStr(bytes(keys,'ascii'),30))
    if locqry == '_':
        conn.SendTML('<SPLIT><CURSOR>')
        return
    conn.SendTML('<CBM-B><CRSRL>')
    tloc = do_geocode(locqry)   #geoLoc.geocode(locqry,language=conn.bbs.lang)
    if tloc == None:
        conn.SendTML('<CLR>ERROR!<PAUSE n=0.5>')
        #Default to Greenwich observatory
        response = requests.get('https://ipinfo.io/'+conn.addr[0])   #('https://geolocation-db.com/jsonp/200.59.72.128')
        result = response.content.decode()
        result  = json.loads(result)
        loc = tuple(map(float,result.get('loc',"51.47679219,-0.00073887").split(',')))
    else:
        loc = (tloc.latitude,tloc.longitude)

    zoom = 16
    sw = 320    #Screen width
    sh = 200    #Screen height
    #Minimum number of tiles centered at map coordinates needed to fill screen
    xtiles = math.ceil(sw/256)
    if (xtiles*256)-sw < 256:
        xtiles = math.ceil(xtiles/2)*2+1
    ytiles = math.ceil(sh/256)
    if (ytiles*256)-sh < 256:
        ytiles = math.ceil(ytiles/2)*2+1
    ctilex,ctiley = deg2num(loc[0],loc[1],zoom) #Center tile
    tilecoord = num2deg(ctilex,ctiley,zoom) #Coordinates for center tile top-left corner
    dptx,dpty,dppx,dppy = lat2res(tilecoord[0],zoom)
    cpos = [1,1]

    display = True
    retrieve = True
    while conn.connected:
        if display:
            delta = [abs(loc[i]-tilecoord[i]) for i in range(2)] #Distance from tile corner to desired coordinates
            delta[0] = (delta[0]*256)/dpty
            delta[1] = (delta[1]*256)/dptx
            #croping coordinates
            xmin = ((256*cpos[0])+delta[1])-(sw/2)    #((((xtiles*256)/2)-128) + delta[1])-(sw/2)
            xmax = xmin+sw
            ymin = ((256*cpos[1])+delta[0])-(sh/2)    #((((ytiles*256)/2)-128) + delta[0])-(sh/2)
            ymax = ymin+sh
            tnum = 2**zoom #Number of tiles per row/column
            ttotal = tnum**2 #Total number of tiles
            if retrieve:
                conn.Sendall(TT.split_Screen(24,False,0,1))
                tiles = getImageCluster(ctilex,ctiley,xtiles,ytiles,zoom)
                conn.Sendall(TT.split_Screen(0,False,0,0)+TT.to_Hires(0,1))
                retrieve = False
            mwindow = tiles.crop((xmin,ymin,xmax,ymax))
            mwindow = mwindow.point(lambda p: 255 if p>218 else 0)
            FT.SendBitmap(conn,mwindow.convert('1'),gfxmode=gfxmodes.C64HI,preproc=ColorProcess())
            display = False

        k = conn.ReceiveKey(b'_+-\r'+bytes([P.CRSR_DOWN,P.CRSR_UP,P.CRSR_LEFT,P.CRSR_RIGHT]))
        if (k == b'-') and (zoom > 3):
            zoom -= 1
            ctilex,ctiley = deg2num(loc[0],loc[1],zoom) #Tile containing "loc"
            tilecoord = num2deg(ctilex,ctiley,zoom) #Coordinates for center tile top-left corner
            dptx,dpty,dppx,dppy = lat2res(tilecoord[0],zoom)
            display = True
            retrieve = True
            cpos=[1,1]
        elif (k == b'+') and (zoom < 20):
            zoom += 1
            ctilex,ctiley = deg2num(loc[0],loc[1],zoom) #Tile containing "loc"
            tilecoord = num2deg(ctilex,ctiley,zoom) #Coordinates for center tile top-left corner
            dptx,dpty,dppx,dppy = lat2res(tilecoord[0],zoom)
            display = True
            retrieve = True
            cpos=[1,1]
        elif ord(k) == P.CRSR_DOWN:
            if ymax+sh >= 256*ytiles:
                ctiley += 1
                tilecoord = num2deg(ctilex,ctiley,zoom) #Coordinates for center tile top-left corner
                dptx,dpty,dppx,dppy = lat2res(tilecoord[0],zoom)
                loc = (loc[0]-(dppy*sh),loc[1])
                display = True
                retrieve = True
                cpos = [1,1]
            else:
                if delta[0]+sh >= 256:
                    ctiley +=1
                    cpos[1] += 1
                    tilecoord = num2deg(ctilex,ctiley,zoom) #Coordinates for center tile top-left corner
                    dptx,dpty,dppx,dppy = lat2res(tilecoord[0],zoom)
                loc = (loc[0]-(dppy*sh),loc[1])
                display = True
        elif ord(k) == P.CRSR_UP:
            if ymin-sh < 0:
                ctiley -= 1
                tilecoord = num2deg(ctilex,ctiley,zoom) #Coordinates for center tile top-left corner
                dptx,dpty,dppx,dppy = lat2res(tilecoord[0],zoom)
                loc = (loc[0]+(dppy*sh),loc[1])
                display = True
                retrieve = True
                cpos = [1,1]
            else:
                if delta[0]-sh < 0: # center point moved beyond cell
                    ctiley-= 1
                    cpos[1]-=1
                    tilecoord = num2deg(ctilex,ctiley,zoom) #Coordinates for center tile top-left corner
                    dptx,dpty,dppx,dppy = lat2res(tilecoord[0],zoom)
                loc = (loc[0]+(dppy*sh),loc[1])
                display = True
        elif ord(k) == P.CRSR_RIGHT:
            lon = loc[1]+(dppx*sw)
            if lon > 180:   #wrap around
                lon -= 360
            loc = (loc[0],lon)
            ctilex,ctiley = deg2num(loc[0],lon,zoom) #Tile containing "loc"
            tilecoord = num2deg(ctilex,ctiley,zoom) #Coordinates for center tile top-left corner
            display = True
            if xmax+sw >= 256*xtiles:
                cpos=[1,1]
                retrieve = True
            else:
                if delta[1]+sw >= 256:
                    cpos[0]+=1
        elif ord(k) == P.CRSR_LEFT:
            lon = loc[1]-(dppx*sw)
            if lon < -180:   #wrap around
                lon += 360
            loc = (loc[0],lon)
            ctilex,ctiley = deg2num(loc[0],lon,zoom) #Tile containing "loc"
            tilecoord = num2deg(ctilex,ctiley,zoom) #Coordinates for center tile top-left corner
            display = True
            if xmin-sw < 0:
                cpos=[1,1]
                retrieve = True
            else:
                if delta[1]-sw < 0:
                    cpos[0]-=1
        elif (k == b'_'):   #Exit
            conn.Sendall(TT.enable_CRSR())
            break
        elif (k == b'\r'):  #New Location
            conn.SendTML('<SPLIT row=24 bgbottom=0><CURSOR><CLR><YELLOW>Location:')
            locqry = _dec(conn.ReceiveStr(bytes(keys,'ascii'),30))
            if locqry == '_':
                conn.Sendall(TT.split_Screen(0,False,0,0)+TT.enable_CRSR())
                break
            conn.SendTML('<CBM-B><CRSRL>')
            tloc = do_geocode(locqry)   #geoLoc.geocode(locqry,language=conn.bbs.lang)
            if tloc == None:
                conn.SendTML('<CLR>ERROR!><PAUSE n=0.5>')
                #Default to user location or Greenwich observatory otherwise
                response = requests.get('https://ipinfo.io/'+conn.addr[0])   #('https://geolocation-db.com/jsonp/200.59.72.128')
                result = response.content.decode()
                result  = json.loads(result)
                loc = tuple(map(float,result.get('loc',"51.47679219,-0.00073887").split(',')))
            else:
                loc = (tloc.latitude,tloc.longitude)
            zoom = 16
            ctilex,ctiley = deg2num(loc[0],loc[1],zoom)
            tilecoord = num2deg(ctilex,ctiley,zoom) #Coordinates for center tile top-left corner
            dptx,dpty,dppx,dppy = lat2res(tilecoord[0],zoom)
            display = True
            retrieve = True
            cpos = [1,1]