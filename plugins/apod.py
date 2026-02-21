#Retrieves an APOD and converts it to c64 gfx format

import requests
import random
from datetime import datetime
from PIL import Image
from io import BytesIO

from common import turbo56k as TT
from common.style import RenderMenuTitle
from common import filetools as FT
from common.helpers import formatX, More, text_displayer
from common.bbsdebug import _LOG,bcolors
from common.connection import Connection
from common.imgcvt import gfxmodes

url = 'https://api.nasa.gov/planetary/apod'

###############
# Plugin setup
###############
def setup():
    fname = "APOD"
    parpairs= []
    return(fname,parpairs)

start_date = datetime.today().replace(day=16, month=6, year=1995).toordinal()
end_date = datetime.today().toordinal()

###################################
# Plugin function
###################################
def plugFunction(conn:Connection):

    apod_lang = {'en':['Connecting with NASA',f"<CLR><BR><LTGREEN>Converting...<BR>press <INK c={conn.style.PbColor}>"	\
                    + f"[<INK c={conn.style.PtColor}>RETURN<INK c={conn.style.PbColor}>]"	\
                    + f"<LTGREEN> for a new<BR>random image<BR>Or "	\
                    + f"<INK c={conn.style.PbColor}>[<INK c={conn.style.PtColor}><BACK>"	\
                    + f"<INK c={conn.style.PbColor}>]<LTGREEN> to exit<YELLOW><SPINNER>",
                    f"<CLR><LTGREEN><FORMAT>A Turbo56K compatible terminal is required to view this image</FORMAT><BR>"\
                    + f"[<INK c={conn.style.PtColor}>RETURN<INK c={conn.style.PbColor}>]"	\
                    + f"<LTGREEN> for a new<BR>random image<BR>Or "	\
                    + f"<INK c={conn.style.PbColor}>[<INK c={conn.style.PtColor}><BACK>"	\
                    + f"<INK c={conn.style.PbColor}>]<LTGREEN> to exit<YELLOW><SPINNER>"],
                'es':['Conectando con la NASA',f"<CLR><BR><LTGREEN>Convirtiendo...<BR>presione <INK c={conn.style.PbColor}>"	\
                    + f"[<INK c={conn.style.PtColor}>RETURN<INK c={conn.style.PbColor}>]"	\
                    + f"<LTGREEN> para mostrar otra imagen al azar<BR>O "	\
                    + f"<INK c={conn.style.PbColor}>[<INK c={conn.style.PtColor}><BACK>"	\
                    + f"<INK c={conn.style.PbColor}>]<LTGREEN> para volver<YELLOW><SPINNER>",
                    f"<CLR><FORMAT><LTGREEN>Se requiere una terminal compatible con Turbo56K para ver ésta imagen</FORMAT><BR>"\
                    + f"[<INK c={conn.style.PtColor}>RETURN<INK c={conn.style.PbColor}>]"	\
                    + f"<LTGREEN> para una nueva imagen al azar<BR>O "	\
                    + f"<INK c={conn.style.PbColor}>[<INK c={conn.style.PtColor}><BACK>"	\
                    + f"<INK c={conn.style.PbColor}>]<LTGREEN> para volver<YELLOW><SPINNER>"]}
    loop = True
    rdate = datetime.today()
    while loop == True:
        # Text mode
        conn.SendTML(f'<NUL n=2><TEXT page=0 border={conn.style.BoColor} background={conn.style.BoColor}><CURSOR>')
        RenderMenuTitle(conn,'APOD')
        conn.SendTML(apod_lang.get(conn.bbs.lang,'en')[0]+'<YELLOW>...<SPINNER>')
        i = 0
        idata = None
        _LOG("Receiving APOD info",id=conn.id,v=4)
        while idata == None and i<5:
            idata = apod_info(rdate,conn.bbs.PlugOptions.get('nasakey','DEMO_KEY'))
            rdate = datetime.fromordinal(random.randint(start_date, end_date))
            if idata == None:
                _LOG(bcolors.OKBLUE+"APOD Retrying..."+bcolors.ENDC,id=conn.id,v=3)
            i += 1
            conn.Sendall(".")
        conn.SendTML(f'<BELL><DEL n={23+i}>')
        if idata != None:
            scwidth,scheight = conn.encoder.txt_geo
            if conn.QueryFeature(TT.SET_WIN) >= 0x80:
                barline = 3
            else:
                barline = scheight-1
            if conn.QueryFeature(TT.SCROLL) >= 0x80 and not conn.encoder.features['scrollback']:
                crsr = ''
            else:
                if set(('CRSRU','CRSRD')) <= conn.encoder.ctrlkeys.keys():
                    crsr = 'crsr'
                else:
                    crsr = 'a/z'
            if set(('F1','F3')) <= conn.encoder.ctrlkeys.keys():
                pages = 'F1/F3'
            else:
                pages = 'p/n'
            conn.SendTML(conn.templates.GetTemplate('main/navbar',**{'barline':barline,'crsr':crsr,'pages':pages,'keys':[('v','view')]}))
            # if 'MSX' in conn.mode:
            #     bcode = 0xDB
            #     rcrsr = ''
            # else:
            #     bcode = 0xA0
            #     rcrsr = '<CRSRR n=7><R-NARROW>'
            # if conn.QueryFeature(TT.LINE_FILL) < 0x80:
            #     conn.SendTML(f'<CYAN><LFILL row={barline} code={bcode}><AT x=0 y={barline}><RVSON>')
            # else:
            #     conn.SendTML(f'<CYAN><AT x=0 y={barline}><RVSON><SPC n={scwidth-1}><CRSRL><INS> <AT x=0 y={barline}>')
            # conn.SendTML(f'<R-NARROW><LTBLUE>{pages}{crsr}:move<GREEN><L-NARROW>v:view<R-NARROW><CYAN>{rcrsr}<YELLOW><BACK>:exit<CYAN><L-NARROW><RVSOFF>')
            if conn.QueryFeature(TT.SET_WIN) >= 0x80:
                conn.SendTML('<BR>')
            date = idata["date"]
            _LOG("Showing APOD info for "+date,id=conn.id,v=4)
            imurl = idata["url"]
            title = idata["title"]
            desc = idata["explanation"]
            if "copyright" in idata:
                autor = idata["copyright"]
            else:
                autor = ''
            texto = formatX(title,scwidth)
            #Date
            tdate = formatX('\n'+date+'\n\n',scwidth)
            tdate[0] = f'<INK c={conn.style.HlColor}>'+tdate[0]
            texto += tdate
            #Author
            if autor != '':
                at = formatX(autor,scwidth)
                at[0] = f'<INK c={conn.style.TevenColor}>'+at[0]
            else:
                at = ['<BR>']
            #Description
            tdesc = formatX(desc,scwidth)
            tdesc[0] = f'<INK c={conn.style.TxtColor}>'+tdesc[0]
            texto += at+tdesc
            conn.SendTML(f'<WINDOW top=3 bottom={scheight-2}>')
            tecla = text_displayer(conn,texto,scheight-4,ekeys='v')
            conn.SendTML('<WINDOW>')
            back = conn.encoder.back
            if conn.connected == False:
                return()
            if tecla == back or tecla == '':
                loop = False
            if loop == True:
                if conn.QueryFeature(TT.PRADDR) < 0x80 or (conn.T56KVer == 0 and len(conn.encoder.gfxmodes) > 0):
                    conn.SendTML(apod_lang.get(conn.bbs.lang,'en')[1])
                    _LOG("Downloading and converting image",id=conn.id,v=4)
                    try:
                        img = apod_img(conn, imurl)
                        FT.SendBitmap(conn, img)
                    except:
                        _LOG(bcolors.WARNING+"Error receiving APOD image"+bcolors.ENDC,id=conn.id,v=2)
                        conn.SendTML("<BR>ERROR, unable to receive image")
                else:
                    conn.SendTML(apod_lang.get(conn.bbs.lang,'en')[2])
                tecla = conn.ReceiveKey([conn.encoder.nl,back])
                conn.SendTML('<CURSOR>')
                if conn.connected == False:
                    _LOG(bcolors.WARNING+"ShowAPOD - Disconnect"+bcolors.ENDC,id=conn.id,v=1)
                    return()
                if tecla == back or tecla == '':
                    loop = False
        else:
            conn.SendTML("<BR>ERROR, unable to connect with NASA")
            _LOG(bcolors.WARNING+"Error while reaching NASA"+bcolors.ENDC,id=conn.id,v=2)
            loop = False

#####################################################
# Retrieve APOD data
#####################################################
def apod_info(idate, key='DEMO_KEY', retry = False):
    global url

    date = idate.strftime("%Y-%m-%d")
    resp = None
    while resp == None:
        try :
            param = {'api_key': key, 'date': date}
            resp = requests.get(url, params=param, timeout=8).json()
            #apod_url = resp["hdurl"]
            if "media_type" in resp:
                m_type = resp["media_type"]
            else:
                m_type = ''
            if m_type != 'image' and retry == True:
                _LOG('APOD - Not an image, retrying...')
                resp = None
                date = datetime.fromordinal(random.randint(start_date, end_date)).strftime("%Y-%m-%d")
        except :
            if retry == True:
                _LOG('APOD - Error, retrying...')
            else:
                m_type = ''
                resp = -1
    if m_type != 'image':
        resp = None
    return(resp)

###################################
# Retrieve APOD image
###################################
def apod_img(conn:Connection,url):
    cv_img = None
    bitmap = None
    screen = None
    colorRAM = None
    background = 0
    try:
        apod_im = requests.get(url, allow_redirects=True)
        _LOG('APOD - Image retrieved', id=conn.id, v=4)
    except:
        _LOG('APOD - Error retreiving image', id=conn.id, v=2)
        return(cv_img, bitmap, screen, colorRAM, background)
    try:
        img = Image.open(BytesIO(apod_im.content))
        img = img.convert("RGB")
    except:
        _LOG('APOD - Error converting image', id=conn.id, v=1)
    return (img)

