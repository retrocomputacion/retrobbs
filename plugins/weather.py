import python_weather
import asyncio
import requests
import string
import json

from geopy.geocoders import Photon, Nominatim

from PIL import Image
from PIL import ImageDraw

import numpy as NP

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
wtypes =    {110:2,113:2,                                       #Clear
            116:7,                                              #Partly Cloudy
            119:1,                                              #Cloudy
            122:23,                                             #Overcast
            143:6,                                              #Mist
            176:13,263:13,353:13,                               #Light showers
            179:14,362:14,374:14,311:14,323:14,326:14,368:14,   #Light snow/sleet
            182:4,185:4,281:4,314:4,317:4,350:4,377:4,365:4,    #Moderate/heavy snow/sleet
            200:15,386:15,392:15,                               #Thundery showers
            227:17,230:17,320:17,                               #Blizzard
            248:5,260:5,                                        #Fog
            266:13,293:13,296:13,                               #Light rain
            299:3,302:3,356:3,                                  #Moderate rain
            305:11,308:11,359:11,                               #Heavy rain
            335:24,371:24,395:0,338:24,                         #Heavy snow
            389:0                                               #Thunder
}
#Weather types -> text
twtypes = {110:'Clear',113:'Clear',
            116:'Partly Cloudy',
            119:'Cloudy',
            122:'Overcast',
            143:'Mist',
            176:'Light Showers',263:'Light Showers',353:'Light Showers',
            179:'Light Snow',362:'Light Snow',374:'Light Snow',311:'Light Snow',323:'Light Snow',326:'Light Snow',368:'Light Snow',
            182:'Snow',185:'Snow',281:'Snow',314:'Snow',317:'Snow',350:'Snow',377:'Snow',365:'Snow',
            200:'Thunderstorm',386:'Thunderstorm',392:'Thunderstorm',
            227:'Blizzard',230:'Blizzard',320:'Blizzard',
            248:'Fog',260:'Fog',
            266:'Light Rain',293:'Light Rain',296:'Light Rain',
            299:'Rain',302:'Rain',356:'Rain',
            305:'Heavy Rain',308:'Heavy Rain',359:'Heavy Rain',
            335:'Heavy Snow',371:'Heavy Snow',395:'Heavy Snow',338:'Heavy Snow',
            389:'Thunder'
}

wwind =     {'N':0,'NNE':7,'NE':7,'ENE':7,'E':2,'ESE':6,'SE':6,'SSE':6,'S':1,'SSW':5,'SW':5,'WSW':5,'W':3,'WNW':8,'NW':8,'NNW':8}

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

    keys = string.ascii_letters + string.digits + ' +-_,.$%&'
    #First get location from the connection IP
    response = requests.get('https://ipinfo.io/'+conn.addr[0])   #('https://geolocation-db.com/jsonp/200.59.72.128')
    result = response.content.decode()
    # Convert this data into a dictionary
    result  = json.loads(result)
    _LOG(f'User IP: {conn.addr[0]} - {result.get("city","Not a public IP")}',v=4,id=conn.id)
    locqry = result.get('city', conn.bbs.PlugOptions.get('wxdefault','Meyrin'))
    geoserver = conn.bbs.PlugOptions.get('geoserver','Nominatim')
    done = False
    loop = asyncio.new_event_loop()
    if geoserver == 'Photon':
        geoLoc = Photon(user_agent="RetroBBS-Weather")
    else:
        geoLoc = Nominatim(user_agent="RetroBBS-Weather")
    back = conn.encoder.decode(conn.encoder.back)
    while conn.connected and not done:
        conn.SendTML('<SPINNER>')
        img = loop.run_until_complete(getweather(conn,locqry,geoLoc))
        if img != None:
            if conn.QueryFeature(TT.PRADDR) < 0x80:
                gmod = gfxmodes.P4HI if conn.mode == 'PET264' else gfxmodes.C64HI
                FT.SendBitmap(conn,img,gfxmode=gmod,preproc=PreProcess(),lines=conn.encoder.txt_geo[1]-2,display=False,dither=dithertype.NONE)
                conn.SendTML(f'<SPLIT row={conn.encoder.txt_geo[1]-2} multi=False bgtop={conn.encoder.colors["BLACK"]} bgbottom={conn.encoder.colors["BLUE"]} mode={conn.mode}><CURSOR><CLR>')
            else:
                conn.SendTML(img)
        else:
            conn.SendTML('<CLR><WHITE>LOCATION NOT FOUND!<PAUSE n=2><BR>')
        conn.SendTML('<FORMAT><YELLOW>[N]ew location or <BACK> to exit</FORMAT>')
        if conn.ReceiveKey('n' + back) == back:
            done = True
        else:
            conn.SendTML('Location:')
            locqry = conn.encoder.decode(conn.ReceiveStr(keys,30))
            try:
                tloc = do_geocode(locqry) #geoLoc.geocode(locqry,language=conn.bbs.lang)
            except:
                _LOG("Weather: ERROR - Can't access geocoder",id=conn.id,v=1)
                conn.SendTML('<CLR><RED>ERROR,<YELLOW> service might be unavailable<BR>If this persist, contact the sysop.<PAUSE n=2>')
                continue
            if tloc == None:
                #Default to config setting, or Meyrin otherwise
                locqry = conn.bbs.PlugOptions.get('wxdefault','Meyrin')
    loop.close()
    conn.SendTML(f'<NUL n=2><SPLIT bgbottom={conn.encoder.colors.get("BLACK",0)} mode="_C.mode">')
    return

# Get closest cell x-coord
cellx = lambda width,percent:int((width*percent)//8)*8


#######################################################
# Get weather data and render image
#######################################################
async def getweather(conn:Connection,locquery,geoLoc):

    # Avoid Geocode timeout/Unavailable errors
    # https://gis.stackexchange.com/questions/173569/avoid-time-out-error-nominatim-geopy-openstreetmap
    def do_reverse(location, attempt=1, max_attempts=5):
        try:
            return geoLoc.reverse(location,language=conn.bbs.lang)
        except:
            if attempt <= max_attempts:
                return do_reverse(location, attempt=attempt+1)
            return None

    # declare the client. format defaults to the metric system (celcius, km/h, etc.)
    units = python_weather.METRIC if conn.bbs.database.getUserPrefs(conn.userid, {'wxunits':conn.bbs.PlugOptions.get('wxunits','C')})['wxunits']=='C' else python_weather.IMPERIAL
    if python_weather.__version__[0]=='0':
        client = python_weather.Client(format=units)
    else:
        client = python_weather.Client(unit=units)

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
        img, inPal = get_IndexedImg(gm,get_ColorIndex(gm,c_black)) #Image.new('1', (320,200), color = 'black')
        inPal.colordelta = colordelta.EUCLIDEAN
        draw = ImageDraw.Draw(img)
        gfx = True
    else:
        gfx = False
        img = ''
    # fetch a weather forecast from a city
    try:
        weather = await asyncio.wait_for(client.get(locquery),15) # Wait for up to 15seconds.
        if weather.coordinates == None:    #Invalid location
            await client.close()
            return None
    except Exception as e:
        _LOG('Weather: TIMEOUT',id=conn.id,v=1)
        await client.close()
        return None
    # if gfx:
    # else:
    # Get full location from returned coordinates
    try:
        floc = do_reverse(str(weather.coordinates[0])+','+str(weather.coordinates[1])) #geoLoc.reverse(str(weather.location[0])+','+str(weather.location[1]),language=conn.bbs.lang)
        address = floc.raw.get('address',floc.raw.get('properties',{})) #'address' in nominatim, 'properties in photon
        #City
        city = address.get('village',address.get('town',address.get('city',address.get('municipality','Unknown'))))
        #Region
        region = address.get('state',address.get('region',address.get('county','')))
        #Country
        country = address.get('country',address.get('country_code',address.get('continent','')))
    except Exception as e:
        _LOG('Error getting location data, using user query instead',id=conn.id, v=1)
        city = locquery
        region = ''
        country = ''
    # Generate image
    locdisplay = city+('-'+region if region != '' else '')+('-'+country if country != '' else '')
    # if gfx:
    # else:
    #Current temperature
    ctemp = weather.temperature
    if units == python_weather.IMPERIAL:
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
    # if gfx:
    # else:
    #Current weather type
    wt = weather.kind.value
    # if  gfx:
    # else:
    #Current wind conditions
    wd = weather.wind_direction.value
    # if gfx:
    # else:
    #Pressure
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
        draw.text((40, 24),str(ctemp)+'°'+('C' if units==python_weather.METRIC else 'F'),tco,font=font_temp)
        tmp = inPal.create_PIL_png_from_rgb_array(Image.fromarray(wgfx24[wtypes.get(wt,8)]))
        img.paste(tmp,(8,24))
        tmp = inPal.create_PIL_png_from_rgb_array(Image.fromarray(wgfx24[16]))
        img.paste(tmp,(cellx(xdim[0],.325),24)) #32.5%
        draw.text((cellx(xdim[0],.425),28),str(weather.wind_speed)+('km/h' if units == python_weather.METRIC else 'mph'),c_white,font=font_title)   #42.5%
        tmp = inPal.create_PIL_png_from_rgb_array(Image.fromarray(wgfx8[wwind[wd]]))
        img.paste(tmp,(cellx(xdim[0],.575),32)) #57.5%
        tmp = inPal.create_PIL_png_from_rgb_array(Image.fromarray(wgfx24[10]))
        img.paste(tmp,(cellx(xdim[0],.7),24)) #70%
        draw.text((cellx(xdim[0],.8),28),str(weather.pressure)+('hPa' if units == python_weather.METRIC else 'Hg'),c_white,font=font_title)   #80%
    else:
        img = '<CLR>'
        locdisplay = crop(locdisplay, conn.encoder.txt_geo[0]-2, conn.encoder.ellipsis)
        lpad = (conn.encoder.txt_geo[0]-len(locdisplay))//2
        rpad = conn.encoder.txt_geo[0]-(lpad+len(locdisplay))
        img += f'<GREY><RVSON><SPC n={lpad}>{locdisplay}<SPC n={rpad}><RVSOFF>'
        img += f'<BR><FORMAT><YELLOW>Current weather: <GREY3>'
        img += f'{twtypes.get(wt,"Clear")}<BR><WHITE>Temp:{ttco}{ctemp}°{"C" if units==python_weather.METRIC else "F"}</FORMAT>'
        img += f'<WHITE>Wind:<GREY> {wd} {weather.wind_speed}{"km/h" if units == python_weather.METRIC else "mph"}<BR>'
        img += f'<WHITE>Pressure:<GREY> {weather.pressure}{"hPa" if units == python_weather.METRIC else "Hg"}<BR><BLUE><HLINE n={conn.encoder.txt_geo[0]}>'
        img += f'<RED>&gt;<GREEN>&gt;<BLUE>&gt;<WHITE>Forecast:<BR><BR>'

    if gfx:
        draw.line(((0,55),(xdim[0]-1,55)),fill=c_blue)
        # get the weather forecast for a few days
        draw.text((cellx(xdim[0],.17),58),'Morning',c_white,font=font_text,anchor='mt')     #17%
        draw.text((cellx(xdim[0],.394),58),'Noon',c_white,font=font_text,anchor='mt')       #39.37%
        draw.text((cellx(xdim[0],.62),58),'Evening',c_white,font=font_text,anchor='mt')    #62%
        draw.text((cellx(xdim[0],.837),58),'Night',c_white,font=font_text,anchor='mt')      #83.75%
        ix = 0
        for daily in weather:
            draw.text((0,76+(ix)),daily.date.strftime('%a'),c_white,font=font_text)
            ih = 0
            for hourly in daily:
                if python_weather.__version__[0] == 0:
                    wt = hourly.type.value
                else:
                    wt = hourly.kind.value
                if ih == 3: # Morning
                    try:
                        icon = Image.fromarray(wgfx24[wtypes.get(wt,8)])
                    except:
                        icon = Image.fromarray(wgfx24[8])
                    tmp = inPal.create_PIL_png_from_rgb_array(icon)
                    xx = cellx(xdim[0],.10)
                    img.paste(tmp,(xx,72+(ix)))
                    draw.text((xx+24,76+(ix)),str(hourly.temperature)+'°',c_white,font=font_text)
                elif ih == 4: #Noon
                    try:
                        icon = Image.fromarray(wgfx24[wtypes.get(wt,8)])
                    except:
                        icon = Image.fromarray(wgfx24[8])
                    tmp = inPal.create_PIL_png_from_rgb_array(icon)
                    xx = cellx(xdim[0],.325)
                    img.paste(tmp,(xx,72+(ix)))
                    draw.text((xx+24,76+(ix)),str(hourly.temperature)+'°',c_white,font=font_text)
                elif ih == 6: #Evening
                    try:
                        icon = Image.fromarray(wgfx24[wtypes.get(wt,8)])
                    except:
                        icon = Image.fromarray(wgfx24[8])
                    tmp = inPal.create_PIL_png_from_rgb_array(icon)
                    xx = cellx(xdim[0],.55)
                    img.paste(tmp,(xx,72+(ix)))
                    draw.text((xx+24,76+(ix)),str(hourly.temperature)+'°',c_white,font=font_text)
                elif ih == 7: #Night
                    try:
                        icon = Image.fromarray(wgfx24[wtypes.get(wt,8)])
                    except:
                        icon = Image.fromarray(wgfx24[8])
                    tmp = inPal.create_PIL_png_from_rgb_array(icon)
                    xx = cellx(xdim[0],.775)
                    img.paste(tmp,(xx,72+(ix)))
                    draw.text((xx+24,76+(ix)),str(hourly.temperature)+'°',c_white,font=font_text)
                ih += 1
            ix += 32
    else:
        for daily in weather:
            img += f'<KPROMPT><INKEYS><DEL n=8><FORMAT><YELLOW>{daily.date.strftime("%A")}<BR>'
            ih = 0
            for hourly in daily:
                if python_weather.__version__[0] == 0:
                    wt = hourly.type.value
                else:
                    wt = hourly.kind.value
                if ih == 3: # Morning
                    img += f'<WHITE>Morning: <GREY>{hourly.temperature}° {twtypes.get(wt,"CLEAR")}<BR>'
                elif ih == 4: #Noon
                    img += f'<WHITE>Noon:    <GREY>{hourly.temperature}° {twtypes.get(wt,"CLEAR")}<BR>'
                elif ih == 6: #Evening
                    img += f'<WHITE>Evening: <GREY>{hourly.temperature}° {twtypes.get(wt,"CLEAR")}<BR>'
                elif ih == 7: #Night
                    img += f'<WHITE>Night:   <GREY>{hourly.temperature}° {twtypes.get(wt,"CLEAR")}<BR>'
                ih += 1
            img +=f'</FORMAT><GREEN><HLINE n={conn.encoder.txt_geo[0]}>'
    # close the wrapper once done
    await client.close()
    return(img)
