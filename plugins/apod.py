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


url = 'https://api.nasa.gov/planetary/apod'

#############################
#Plugin setup
def setup():
    fname = "APOD"
    parpairs= []
    return(fname,parpairs)
#############################

start_date = datetime.today().replace(day=16, month=6, year=1995).toordinal()
end_date = datetime.today().toordinal()

##########################################
#Plugin callable function
def plugFunction(conn:Connection):



    apod_lang = {'en':['Connecting with NASA',f"<BR><GREEN>Press <INK c={conn.style.PbColor}>"	\
                    + f"[<INK c={conn.style.PtColor}>RETURN<INK c={conn.style.PbColor}>]"	\
                    + f"<LTGREEN> to display image<BR>Press <INK c={conn.style.PbColor}>[<INK c={conn.style.PtColor}>"	\
                    + f"RETURN<INK c={conn.style.PbColor}>]<LTGREEN> again for a new<BR>random image<BR>Or "	\
                    + f"<INK c={conn.style.PbColor}>[<INK c={conn.style.PtColor}><LARROW>"	\
                    + f"<INK c={conn.style.PbColor}>]<LTGREEN> to go back"],
                'es':['Connectando con la NASA',f"<BR><GREEN>Presione <INK c={conn.style.PbColor}>"	\
                    + f"[<INK c={conn.style.PtColor}>RETURN<INK c={conn.style.PbColor}>]"	\
                    + f"<LTGREEN> para mostrar imagen<BR>Presione <INK c={conn.style.PbColor}>[<INK c={conn.style.PtColor}>"	\
                    + f"RETURN<INK c={conn.style.PbColor}>]<LTGREEN> de nuevo<BR>para otra imagen al azar<BR>O "	\
                    + f"<INK c={conn.style.PbColor}>[<INK c={conn.style.PtColor}><LARROW>"	\
                    + f"<INK c={conn.style.PbColor}>]<LTGREEN> para volver"]}

    loop = True
    rdate = datetime.today()
    while loop == True:
        # # Text mode
        conn.Sendall((chr(0)*2)+TT.to_Text(0,conn.style.BoColor,conn.style.BgColor)+TT.enable_CRSR())
        RenderMenuTitle(conn,'APOD')
        conn.SendTML(apod_lang.get(conn.bbs.lang,'en')[0]+'<YELLOW>...<CBM-B><CRSRL>')
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
            conn.SendTML('<CYAN><LFILL row=24 code=160><AT x=1 y=24><RVSON><CBM-L><LTBLUE>F1/F3/crsr:move<CYAN><CBM-J><CBM-L><GREEN>v:view<CYAN><CBM-J><CRSRR n=5><CBM-L><YELLOW><LARROW>:exit<CYAN><CBM-J><RVSOFF>')
            date = idata["date"]
            _LOG("Showing APOD info for "+date,id=conn.id,v=4)
            imurl = idata["url"]
            title = idata["title"]
            desc = idata["explanation"]
            if "copyright" in idata:
                autor = idata["copyright"]
            else:
                autor = ''

            texto = formatX(title)
            #Prints date
            tdate = formatX('\n'+date+'\n\n')
            tdate[0] = '<LTBLUE>'+tdate[0]
            texto += tdate
            if autor != '':
                at = formatX(autor)
                at[0] = '<ORANGE>'+at[0]
            else:
                at = ['<BR>']
            tdesc = formatX(desc)
            tdesc[0] = f'<INK c={conn.style.TxtColor}>'+tdesc[0]
            texto += at+tdesc
            conn.SendTML('<WINDOW top=3 bottom=23>')
            tecla = text_displayer(conn,texto,21,ekeys='V')
            conn.SendTML('<WINDOW>')
            if conn.connected == False:
                return()
            if tecla == b'_' or tecla == b'':
                loop = False
            if loop == True:
                conn.SendTML("<CLR><BR>Converting image<YELLOW><CBM-B><CRSRL>")
                _LOG("Downloading and converting image",id=conn.id,v=4)
                try:
                    img = apod_img(conn, imurl)
                    FT.SendBitmap(conn, img)
                except:
                    _LOG(bcolors.WARNING+"Error receiving APOD image"+bcolors.ENDC,id=conn.id,v=2)
                    conn.SendTML("<BR>ERROR, unable to receive image")

                tecla = conn.ReceiveKey(b'\r_')
                conn.Sendall(TT.enable_CRSR())
                if conn.connected == False:
                    _LOG(bcolors.WARNING+"ShowAPOD - Disconnect"+bcolors.ENDC,id=conn.id,v=1)
                    return()
                if tecla == b'_' or tecla == b'':
                    loop = False
        else:
            conn.SendTML("<BR>ERROR, unable to connect with NASA")
            _LOG(bcolors.WARNING+"Error while reaching NASA"+bcolors.ENDC,id=conn.id,v=2)
            loop = False
##########################################


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

