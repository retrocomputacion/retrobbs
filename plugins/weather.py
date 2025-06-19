import asyncio
import requests
import string
import json
from zoneinfo import ZoneInfo
from datetime import datetime


import openmeteo_requests
import requests_cache
from retry_requests import retry

from geopy.geocoders import Photon, Nominatim

from PIL import Image
from PIL import ImageDraw

import numpy as NP
from math import sqrt

from common.connection import Connection
from common.imgcvt import gfxmodes, get_IndexedImg, PreProcess, colordelta, dithertype, get_ColorIndex, GFX_MODES
from common.bbsdebug import _LOG
from common import filetools as FT
from common import turbo56k as TT
from common.helpers import font_bold as font_title
from common.helpers import font_big as font_temp
from common.helpers import font_text, crop

wgfx24: list  # Weather gfx 24px 
wgfx8:  list  # Weather gfx 8px
#Weather types -> icons
wtypes =    {110:2,113:2,0:2,                                   #Clear
            116:7,1:7,                                          #Partly Cloudy
            119:1,2:1,                                          #Cloudy
            122:23,3:23,                                        #Overcast
            143:6,                                              #Mist
            176:13,263:13,353:13,80:13,                         #Light showers
            179:14,362:14,374:14,311:14,323:14,326:14,368:14,56:14,66:14,71:14,85:14,   #Light snow/sleet
            182:4,185:4,281:4,314:4,317:4,350:4,377:4,365:4,57:4,67:4,73:4,             #Moderate/heavy snow/sleet
            200:15,386:15,392:15,                               #Thundery showers
            227:17,230:17,320:17,                               #Blizzard
            248:5,260:5,45:5,48:5,                              #Fog
            266:13,293:13,296:13,51:13,53:13,55:13,61:13,       #Light rain
            299:3,302:3,356:3,63:3,                             #Moderate rain
            305:11,308:11,359:11,65:11,                         #Heavy rain
            335:24,371:24,395:0,338:24,86:24,                   #Heavy snow
            389:0,95:0                                          #Thunder
}
#Weather types -> text
twtypes = { 110:'Clear',113:'Clear',0:'Clear',
              1:'Mainly Clear',
            116:'Partly Cloudy',2:'Partly Cloudy',
            119:'Cloudy',
            122:'Overcast',3:'Overcast',
            143:'Mist',
             51:'Light Drizzle',
             53:'Drizzle',
             55:'Dense Drizzle',
             56:'Light Freezing Drizzle',
             57:'Dense Freezing Drizzle',
             66:'Light Freezing Rain',
             67:'Heavy Freezing Rain',
             77:'Snow Grains',
             81:'Showers',
             82:'Violent Showers',
             85:'Snow Showers',
             86:'Heavy Snow Showers',
             96:'Thunderstorm with hail',
             99:'Thunderstorm with heavy hail',
            176:'Light Showers',263:'Light Showers',353:'Light Showers',80:'Light Showers',
            179:'Light Snow',362:'Light Snow',374:'Light Snow',311:'Light Snow',323:'Light Snow',326:'Light Snow',368:'Light Snow',71:'Light Snow',
            182:'Snow',185:'Snow',281:'Snow',314:'Snow',317:'Snow',350:'Snow',377:'Snow',365:'Snow',74:'Snow',
            200:'Thunderstorm',386:'Thunderstorm',392:'Thunderstorm',95:'Thunderstorm',
            227:'Blizzard',230:'Blizzard',320:'Blizzard',
            248:'Fog',260:'Fog',45:'Fog',48:'Freezing Fog',
            266:'Light Rain',293:'Light Rain',296:'Light Rain',61:'Light Rain',
            299:'Rain',302:'Rain',356:'Rain',63:'Rain',
            305:'Heavy Rain',308:'Heavy Rain',359:'Heavy Rain',65:'Heavy Rain',
            335:'Heavy Snow',371:'Heavy Snow',395:'Heavy Snow',338:'Heavy Snow',75:'Heavy Snow',
            389:'Thunder'
}

wind_vane = ['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW']
wwind =     {'N':0,'NNE':7,'NE':7,'ENE':7,'E':2,'ESE':6,'SE':6,'SSE':6,'S':1,'SSW':5,'SW':5,'WSW':5,'W':3,'WNW':8,'NW':8,'NNW':8}

cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)


###############
# Plugin setup
###############
def setup():
    global wgfx8
    global wgfx24
    gfx = NP.array(Image.open('plugins/weather_icons.png'))
    wgfx24 = [gfx[x:x+24,y:y+24] for x in range(0,48,24) for y in range(0,312,24)]
    wgfx8 = [gfx[x:x+8,y:y+8] for x in range(56,72,8) for y in range(0,40,8)]
    fname = "WEATHER" #UPPERCASE function name for config.ini
    parpairs = [] #config.ini Parameter pairs (name,defaultvalue)
    return(fname,parpairs)

#########################################
# Register/Get/Set Plugin preferences
#-------------------------------------
# Pass no parameters to get a list of
# preference parameters.
#
# Pass connection & param but no value
# to get the parameter value for this
# user
#
# Pass all connection, param & value to
# set the parameter for this client
#########################################
def plugPrefs(conn:Connection = None, param = None, value = None):
    if conn == None: # Get parameter list
        return [{'name':'wxunits','title':'Weather units','prompt':'Set weather units:','values':{'F':'Imperial','C':'Metric'}}]
    elif param != None:
        if value == None: # Get parameter value
            if param == 'wxunits':
                return conn.bbs.database.getUserPrefs(conn.userid, {'wxunits':conn.bbs.PlugOptions.get('wxunits','C')})['wxunits']
        elif param == 'wxunits': # Set parameter
            conn.bbs.database.updateUserPrefs(conn.userid, {'wxunits':value})


###################################
# Plugin function
###################################
def plugFunction(conn:Connection):

    # Avoid Geocode timeout/Unavailable errors
    # https://gis.stackexchange.com/questions/173569/avoid-time-out-error-nominatim-geopy-openstreetmap
    def do_geocode(location, attempt=1, max_attempts=5):
        try:
            return geoLoc.geocode(location,language=conn.bbs.lang)
        except:
            if attempt <= max_attempts:
                return do_geocode(location, attempt=attempt+1)
            return None

    locqry = {}
    keys = string.ascii_letters + string.digits + ' +-_,.$%&'
    back = conn.encoder.decode(conn.encoder.back)
    geoserver = conn.bbs.PlugOptions.get('geoserver','Nominatim')
    if geoserver == 'Photon':
        geoLoc = Photon(user_agent="RetroBBS-Weather")
    else:
        geoLoc = Nominatim(user_agent="RetroBBS-Weather")

    conn.SendTML('<SPINNER>')
    #First get location from the connection IP
    response = requests.get('https://ipinfo.io/'+conn.addr[0]+'/json')
    result = response.content.decode()
    # Convert this data into a dictionary
    result  = json.loads(result)
    _LOG(f'User IP: {conn.addr[0]} - {result.get("city","Not a public IP")}',v=4,id=conn.id)
    if 'city' in result:
        locqry['city'] = result['city']
        coords = result['loc'].split(',')
        locqry['latitude'] = float(coords[0])
        locqry['longitude'] = float(coords[1])
    else:
        locqry['city'] = conn.bbs.PlugOptions.get('wxdefault','Meyrin')
        try:
            tloc = do_geocode(locqry['city'])
        except:
            _LOG("Weather: ERROR - Can't access geocoder",id=conn.id,v=1)
            conn.SendTML('<CLR><RED>ERROR,<YELLOW> service might be unavailable<BR>If this persist, contact the sysop.<PAUSE n=3>')
            return
        if tloc == None:
            _LOG("Weather: ERROR - Can't access geocoder",id=conn.id,v=1)
            conn.SendTML('<CLR><RED>ERROR,<YELLOW> service might be unavailable<BR>If this persist, contact the sysop.<PAUSE n=3>')
            return
        locqry['latitude'] = tloc.latitude
        locqry['longitude'] = tloc.longitude

    # locqry = result.get('city', conn.bbs.PlugOptions.get('wxdefault','Meyrin'))
    done = False
    loop = asyncio.new_event_loop()
    while conn.connected and not done:
        conn.SendTML('<SPINNER>')
        img, img2, series = loop.run_until_complete(getweather(conn,locqry,geoLoc))
        if img != None:
            if conn.QueryFeature(TT.PRADDR) < 0x80:
                gmod = gfxmodes.P4HI if conn.mode == 'PET264' else gfxmodes.C64HI
                FT.SendBitmap(conn,img,gfxmode=gmod,preproc=PreProcess(),lines=conn.encoder.txt_geo[1]-2,display=False,dither=dithertype.NONE)
                conn.SendTML(f'<SPLIT row={conn.encoder.txt_geo[1]-2} multi=False bgtop={conn.encoder.colors["BLACK"]} bgbottom={conn.encoder.colors["BLUE"]} mode={conn.mode}><CURSOR><CLR>')
                conn.SendTML(f'<FORMAT><YELLOW>Next page? (Y/N)</FORMAT>')
                if conn.ReceiveKey('ynYN').upper() == 'Y':
                    FT.SendBitmap(conn,img2,gfxmode=gmod,preproc=PreProcess(),lines=conn.encoder.txt_geo[1]-2,display=False,dither=dithertype.NONE)
                    conn.SendTML(f'<SPLIT row={conn.encoder.txt_geo[1]-2} multi=False bgtop={conn.encoder.colors["BLACK"]} bgbottom={conn.encoder.colors["BLUE"]} mode={conn.mode}><CURSOR><CLR>')
                    if conn.QueryFeature(TT.LINE) < 0x80:
                        conn.Sendallbin(series)
            else:
                # Text only version
                conn.SendTML(img)
        else:
            conn.SendTML('<CLR><WHITE>LOCATION NOT FOUND!<PAUSE n=2><BR>')
        conn.SendTML('<FORMAT><YELLOW>[N]ew location or <BACK> to exit</FORMAT>')
        if conn.ReceiveKey('n' + back) == back:
            done = True
        else:
            _locqry = {}
            conn.SendTML('Location:')
            _locqry['city'] = conn.encoder.decode(conn.ReceiveStr(keys,30))
            try:
                tloc = do_geocode(_locqry['city']) #geoLoc.geocode(locqry,language=conn.bbs.lang)
            except:
                _LOG("Weather: ERROR - Can't access geocoder",id=conn.id,v=1)
                conn.SendTML('<CLR><RED>ERROR,<YELLOW> service might be unavailable<BR>If this persist, contact the sysop.<PAUSE n=2>')
                continue
            if tloc != None:
                _locqry['latitude'] = tloc.latitude
                _locqry['longitude'] = tloc.longitude
                locqry = _locqry
    loop.close()
    conn.SendTML(f'<NUL n=2><SPLIT bgbottom={conn.encoder.colors.get("BLACK",0)} mode="_C.mode">')
    return

# Get closest cell x-coord
cellx = lambda width,percent:int((width*percent)//8)*8


#######################################################
# Get weather data and render image
#######################################################
async def getweather(conn:Connection,locquery,geoLoc):
    global retry_session

    # Avoid Geocode timeout/Unavailable errors
    # https://gis.stackexchange.com/questions/173569/avoid-time-out-error-nominatim-geopy-openstreetmap
    def do_reverse(location, attempt=1, max_attempts=5):
        try:
            return geoLoc.reverse(location,language=conn.bbs.lang)
        except:
            if attempt <= max_attempts:
                return do_reverse(location, attempt=attempt+1)
            return None

    # declare the client. format defaults to the metric system (celsius, km/h, etc.)
    units = conn.bbs.database.getUserPrefs(conn.userid, {'wxunits':conn.bbs.PlugOptions.get('wxunits','C')})['wxunits']
    om_units = ['celsius','kmh'] if conn.bbs.database.getUserPrefs(conn.userid, {'wxunits':conn.bbs.PlugOptions.get('wxunits','C')})['wxunits']=='C' else ['fahrenheit','mph']

    # get timezone
    response = requests.get(f"https://timezonefinder.michelfe.it/api/0_{locquery['longitude']}_{locquery['latitude']}")
    result = response.content.decode()
    # Convert this data into a dictionary
    result  = json.loads(result)
    tz = result['tz_name']
    if tz == None:
        tz = 'GMT'
    if 'Etc' in tz:
        timezone = tz.split('/')[1]
        if '-' in timezone:
            timezone = timezone.replace('-','+')
        elif '+' in timezone:
            timezone = timezone.replace('+','-')
    else:
        timezone = tz

    # open-meteo parameters
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": locquery['latitude'],
        "longitude": locquery['longitude'],
        "hourly": ["temperature_2m","weather_code"],
        "current": ["temperature_2m", "weather_code", "surface_pressure", "wind_speed_10m", "wind_direction_10m"],
        "timezone": timezone,
        "forecast_days": 7,
        "temperature_unit": om_units[0],
        "wind_speed_unit": om_units[1]
    }

    openmeteo = openmeteo_requests.Client(session = retry_session)

    c_black = (0,0,0)
    c_red = (0x99,0x33,0x33)
    c_white = (0xff,0xff,0xff)
    c_purple = (0xaa,0x33,0xaa)
    c_lblue = (0x66,0x66,0xff)
    c_cyan = (0x55,0xdd,0xcc)
    c_yellow = (0xff,0xff,0x55)
    c_orange = (0xaa,0x55,0x11)
    c_dgrey = (0x43,0x43,0x43)
    c_blue = (0x33,0x33,0xcc)
    c_lgrey = (0xaa,0xaa,0xaa)
    if conn.QueryFeature(TT.PRADDR) < 0x80:
        if conn.mode == "PET64":
            gm = gfxmodes.C64HI
        else:
            gm = conn.encoder.def_gfxmode

        xdim = GFX_MODES[gm]['out_size']
        # First screen
        img, inPal = get_IndexedImg(gm,get_ColorIndex(gm,c_black)) #Image.new('1', (320,200), color = 'black')
        inPal.colordelta = colordelta.EUCLIDEAN
        draw = ImageDraw.Draw(img)
        gfx = True
        # Second screen
        img2, inPal2 = get_IndexedImg(gm,get_ColorIndex(gm,c_black)) #Image.new('1', (320,200), color = 'black')
        inPal2.colordelta = colordelta.EUCLIDEAN
        draw2 = ImageDraw.Draw(img2)
        gfx = True
        series = b''
    else:
        gfx = False
        img = ''
        img2 = None
        series = b''

    # fetch a weather forecast
    responses = openmeteo.weather_api(url, params=params)
    if len(responses) == 0:
        return None
    
    weather = responses[0]

    # Get full location from returned coordinates
    try:
        floc = do_reverse(str(weather.Latitude())+','+str(weather.Longitude())) #geoLoc.reverse(str(weather.location[0])+','+str(weather.location[1]),language=conn.bbs.lang)
        address = floc.raw.get('address',floc.raw.get('properties',{})) #'address' in nominatim, 'properties in photon
        #City
        city = address.get('village',address.get('town',address.get('city',address.get('municipality','Unknown'))))
        #Region
        region = address.get('state',address.get('region',address.get('county','')))
        #Country
        country = address.get('country',address.get('country_code',address.get('continent','')))
    except Exception as e:
        _LOG('Error getting location data, using user query instead',id=conn.id, v=1)
        city = locquery['city']
        region = ''
        country = ''
    locdisplay = city+('-'+region if region != '' else '')+('-'+country if country != '' else '')
    #Current temperature
    ctemp = int(weather.Current().Variables(0).Value())
    if units == 'F':
        if ctemp < 32:
            tco = c_purple  #4
            ttco = '<PURPLE>'
        elif ctemp < 41:
            tco = c_lblue   #14
            ttco = '<LTBLUE>'
        elif ctemp < 59:
            tco = c_cyan    #3
            ttco = '<CYAN>'
        elif ctemp < 77:
            tco = c_yellow  #7
            ttco = '<YELLOW>'
        elif ctemp < 86:
            tco = c_orange  #8
            ttco = '<ORANGE>'
        else:
            tco = c_red     #2
            ttco = '<RED>'
    else:
        if ctemp < 0:
            tco = c_purple  #4
            ttco = '<PURPLE>'
        elif ctemp < 5:
            tco = c_lblue   #14
            ttco = '<LTBLUE>'
        elif ctemp < 15:
            tco = c_cyan    #3
            ttco = '<CYAN>'
        elif ctemp < 25:
            tco = c_yellow  #7
            ttco = '<YELLOW>'
        elif ctemp < 30:
            tco = c_orange  #8
            ttco = '<ORANGE>'
        else:
            tco = c_red     #2
            ttco = '<RED>'
    #Current weather type
    wt = weather.Current().Variables(1).Value()
    #Current wind conditions
    wd = wind_vane[int((weather.Current().Variables(4).Value()%360)//22.5)]
    ws = round(weather.Current().Variables(3).Value())
    #Pressure
    sp = round(weather.Current().Variables(2).Value())

    time_s = weather.Hourly().Time()
    # Hourly Temperatures
    d_temp = weather.Hourly().Variables(0).ValuesAsNumpy()
    # Hourly Weather codes
    d_wc = weather.Hourly().Variables(1).ValuesAsNumpy()

    # Render 1st screen
    if gfx:
        draw.rectangle([0,0,xdim[0]-1,15],c_lgrey)
        j = 3
        for i in range(0,7):
            draw.line(((2+(int(j*i)),0),(-13+(int(j*i)),15)),fill=c_dgrey)
        l,t,r,b = draw.textbbox((xdim[0]//2,2),locdisplay,font=font_title,anchor='mt')
        draw.rectangle([l-1,t-1,r+1,b+1],c_lgrey)
        draw.text((xdim[0]//2,2),locdisplay.replace('|','-'),c_dgrey,font=font_title,anchor='mt')
        draw.line(((0,16),(xdim[0]-1,16)),fill=c_dgrey)
        for i in range(0,xdim[0],2):
            draw.point((i,17),fill=c_dgrey)
            draw.point((i+1,18),fill=c_dgrey)
            draw.point((i,54),fill=c_blue)
            draw.point((i+1,53),fill=c_blue)
        draw.text((40, 24),str(ctemp)+'°'+units,tco,font=font_temp)
        tmp = inPal.create_PIL_png_from_rgb_array(Image.fromarray(wgfx24[wtypes.get(wt,8)]))
        img.paste(tmp,(8,24))
        tmp = inPal.create_PIL_png_from_rgb_array(Image.fromarray(wgfx24[16]))
        img.paste(tmp,(cellx(xdim[0],.325),24)) #32.5%
        draw.text((cellx(xdim[0],.425),28),str(ws)+('km/h' if units == 'C' else 'mph'),c_white,font=font_title)   #42.5%
        tmp = inPal.create_PIL_png_from_rgb_array(Image.fromarray(wgfx8[wwind[wd]]))
        img.paste(tmp,(cellx(xdim[0],.575),32)) #57.5%
        tmp = inPal.create_PIL_png_from_rgb_array(Image.fromarray(wgfx24[10]))
        img.paste(tmp,(cellx(xdim[0],.7),24)) #70%
        draw.text((cellx(xdim[0],.8),28),str(sp)+'hPa',c_white,font=font_title)   #80%
    else:
        img = '<CLR>'
        locdisplay = crop(locdisplay, conn.encoder.txt_geo[0]-2, conn.encoder.ellipsis)
        lpad = (conn.encoder.txt_geo[0]-len(locdisplay))//2
        rpad = conn.encoder.txt_geo[0]-(lpad+len(locdisplay))
        img += f'<GREY><RVSON><SPC n={lpad}>{locdisplay}<SPC n={rpad}><RVSOFF>'
        img += f'<BR><FORMAT><YELLOW>Current weather: <GREY3>'
        img += f'{twtypes.get(wt,"Clear")}<BR><WHITE>Temp:{ttco}{ctemp}{"°C" if units == "C" else "°F"}</FORMAT>'
        img += f'<WHITE>Wind:<GREY> {wd} {ws}{"km/h" if units == "C" else "mph"}<BR>'
        img += f'<WHITE>Pressure:<GREY> {sp}hPa<BR><BLUE><HLINE n={conn.encoder.txt_geo[0]}>'
        img += f'<RED>&gt;<GREEN>&gt;<BLUE>&gt;<WHITE>Forecast:<BR><BR>'

    if gfx:
        draw.line(((0,55),(xdim[0]-1,55)),fill=c_blue)
        # get the weather forecast for a few days
        draw.text((cellx(xdim[0],.17),58),'Morning',c_white,font=font_text,anchor='mt')     #17%
        draw.text((cellx(xdim[0],.394),58),'Noon',c_white,font=font_text,anchor='mt')       #39.37%
        draw.text((cellx(xdim[0],.62),58),'Evening',c_white,font=font_text,anchor='mt')     #62%
        draw.text((cellx(xdim[0],.837),58),'Night',c_white,font=font_text,anchor='mt')      #83.75%
        ix = 0
        for day in range(0,3):
            date = datetime.fromtimestamp(time_s+(86400*day),ZoneInfo(tz))
            draw.text((0,76+(ix)),date.strftime('%a'),c_white,font=font_text)
            for hour in range(6,25,6):
                wt = d_wc[hour+(day*24)]
                if hour == 6: # Morning
                    xx = cellx(xdim[0],.10)
                elif hour == 12: #Noon
                    xx = cellx(xdim[0],.325)
                elif hour == 18: #Evening
                    xx = cellx(xdim[0],.55)
                elif hour == 24: #Night
                    xx = cellx(xdim[0],.775)
                try:
                    icon = Image.fromarray(wgfx24[wtypes.get(wt,8)])
                except:
                    icon = Image.fromarray(wgfx24[8])
                tmp = inPal.create_PIL_png_from_rgb_array(icon)
                img.paste(tmp,(xx,72+(ix)))
                draw.text((xx+24,76+(ix)),str(round(d_temp[hour+(day*24)]))+'°',c_white,font=font_text)
            ix += 32
    else:
        tod = ['Morning','Noon','Evening','Night']
        for day in range(0,3):
            date = datetime.fromtimestamp(time_s+(86400*day),ZoneInfo(tz))
            img += f'<KPROMPT><INKEYS><DEL n=8><FORMAT><YELLOW>{date.strftime("%A")}<BR>'
            for hour in range(6,25,6):
                wt = d_wc[hour+(day*24)]
                img += f'<WHITE>{tod[int(hour//6)-1]}: <GREY>{round(d_temp[hour+(day*24)])}° {twtypes.get(wt,"CLEAR")}<BR>'
            img +=f'</FORMAT><GREEN><HLINE n={conn.encoder.txt_geo[0]}>'

    if gfx:
        #Render 2nd screen
        draw2.rectangle([0,0,xdim[0]-1,15],c_lgrey)
        j = 3
        for i in range(0,7):
            draw2.line(((2+(int(j*i)),0),(-13+(int(j*i)),15)),fill=c_dgrey)
        l,t,r,b = draw2.textbbox((xdim[0]//2,2),locdisplay.replace('|','-'),font=font_title,anchor='mt')
        draw2.rectangle([l-1,t-1,r+1,b+1],c_lgrey)
        draw2.text((xdim[0]//2,2),locdisplay.replace('|','-'),c_dgrey,font=font_title,anchor='mt')
        draw2.text((xdim[0]//2,20),'7 days temperature',c_white,font=font_text,anchor='mt')

        ch_h = (xdim[1]-32)-32  # chart height
        ch_w = (xdim[0]-16)-24  # chart width
        t_min = round(NP.min(d_temp)/5)*5
        t_max = round(NP.max(d_temp)/5)*5
        if t_min >= NP.min(d_temp):
            t_min -= 5
        if t_max <= NP.max(d_temp):
            t_max += 5
        # t_min and t_max: minimum and maximum temperatures to the nearest 5 (lower and higher) degrees multiple
        y_scale = ch_h/(t_max - t_min)

        # draw axis
        draw2.line(((24,xdim[1]-32),(xdim[0]-16,xdim[1]-32)),fill=c_white)
        x_step = NP.linspace(0,ch_w,len(d_temp), endpoint=False)
        # Dotted lines every 5 degrees
        for i,y in enumerate(range(32,32+ch_h,round(y_scale*5))):
            draw2.text((23,y),str(t_max-(5*i)),c_white,font=font_text,anchor='rm')
            for x in range(0,ch_w,4):
                draw2.point((x+24,y),fill=c_white)
        draw2.text((23,xdim[1]-34),str(t_min),c_white,font=font_text,anchor='rm')
        draw2.text((xdim[0]-16,(ch_h//2)+32),"°C" if units == "C" else "°F",c_white,font=font_text,anchor='lm')

        if conn.QueryFeature(TT.LINE) < 0x80:
            p_black = conn.encoder.colors.get('BLACK',0)
            p_white = conn.encoder.colors.get('WHITE',1)
            series = bytes([TT.CMDON,TT.PENCOLOR,0,p_black,TT.PENCOLOR,1,p_white])

        for i,x in enumerate(x_step):
            x2 = 24+round(x)
            y2 = (32+ch_h)-round((d_temp[i]-t_min)*y_scale)
            if i == 0:
                x1 = x2
                y1 = y2
            if conn.QueryFeature(TT.LINE) < 0x80:
                _x1 = x1.to_bytes(2,'little',signed=True)
                _x2 = x2.to_bytes(2,'little',signed=True)
                _y1 = y1.to_bytes(2,'little',signed=True)
                _y2 = y2.to_bytes(2,'little',signed=True)
                if NP.linalg.norm(NP.array([x1,y1])-NP.array([x2,y2])) <= sqrt(2):
                    series += bytes([TT.PLOT,1,_x1[0],_x1[1],_y1[0],_y1[1]])
                else:
                    series += bytes([TT.LINE,1,_x1[0],_x1[1],_y1[0],_y1[1],_x2[0],_x2[1],_y2[0],_y2[1]])
            else:
                draw2.line(((x1,y1),(x2,y2)),fill=c_white)
            x1 = x2
            y1 = y2
            if i % 12 == 0:
                draw2.line(((x1,ch_h+32),(x1,ch_h+36)),fill=c_white)
            if i % 24 == 0:
                date = datetime.fromtimestamp(time_s+(i*3600),ZoneInfo(tz))
                draw2.text((x1,ch_h+36),date.strftime('%a'),c_white,font=font_text,anchor='mt')
        if conn.QueryFeature(TT.LINE) < 0x80:
            series += bytes([TT.CMDOFF])
    return(img,img2,series)
