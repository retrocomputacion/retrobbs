##############################################################################
# Radio Plugin 20240411 written by Emanuele Laface                           #
#                                                                            #
# This plugin requires pyradios to work and it is a Python implementaiton of #
# https://api.radio-browser.info/ free API (It uses GPL 3).                  #
##############################################################################

from common import turbo56k as TT
from common.helpers import crop
from common.connection import Connection

import string
from pyradios import RadioBrowser

rb = RadioBrowser()

###############
# Plugin setup
###############
def setup():
    fname = "RADIO"
    parpairs = []
    return(fname,parpairs)

###################################
# Plugin callable function
###################################
def plugFunction(conn:Connection):

    columns,lines = conn.encoder.txt_geo
    _dec = conn.encoder.decode

    def RadioTitle(conn:Connection):
        conn.SendTML(f'<WINDOW top=0 bottom={lines-1}><CLR><YELLOW>Search internet radios<BR>')
        if conn.QueryFeature(TT.LINE_FILL) < 0x80:
            if 'MSX' in conn.mode:
                conn.SendTML('<GREEN><LFILL row=1 code=23>')
            else:
                conn.SendTML('<GREEN><LFILL row=1 code=64>')
        else:
            conn.SendTML(f'<GREEN><HLINE n={conn.encoder.txt_geo[0]}>')
        conn.SendTML(f'<WINDOW top=2 bottom={lines-1}>')	#Set Text Window
    ecolors = conn.encoder.colors
    conn.SendTML(f'<TEXT page=0 border={ecolors["BLACK"]} background={ecolors["BLACK"]}>')
    loop = True
    while loop == True:
        RadioTitle(conn)
        conn.SendTML('<BR>Search: <BR>(<BACK> to exit)<CRSRU><CRSRL n=3>')
        keys = string.ascii_letters + string.digits + ' +-_,.$%&'
        back = conn.encoder.decode(conn.encoder.back)
        if back not in keys:
            keys += back
        termino = ''
        #Receive search term
        while termino == '':
            termino = _dec(conn.ReceiveStr(keys, columns-10, False))
            if conn.connected == False :
                return()
            if termino == back:
                conn.SendTML(f'<WINDOW top=0 bottom={lines}>')
                return()
        conn.SendTML('<BR><BR>Searching...<SPINNER>')
        searchRes = searchRadio(termino)
        if searchRes == False:
            conn.SendTML('<ORANGE>Service unavailable...<PAUSE n=2>')
            continue
        elif len(searchRes) == 0:
            conn.SendTML('<YELLOW>No results...<PAUSE n=2>')
            continue
        page = 0
        nradios = len(searchRes)
        pcount = lines-10
        if 'MSX' in conn.mode:
            grey = '<GREY>'
        else:
            grey = '<GREY1>'
        while True:
            #RadioTitle(conn)
            conn.SendTML('<CLR><BR>Results:<BR><BR>')
            for i in range(pcount*page, min(pcount*(page+1),nradios)):
                if i > 9:
                    pos = str(i)
                else:
                    pos = " "+str(i)
                radioName = crop(searchRes[i]['name'],columns-10,conn.encoder.ellipsis).ljust(columns-10)
                countryCode = searchRes[i]['countrycode']
                conn.SendTML(f' <BLUE>{pos} {grey}{radioName} [{countryCode}]<BR>')
            if nradios < pcount:
                conn.SendTML(f'<BR><RED><BACK>{grey}Exit<BR>')
                conn.SendTML(f'<RED><KPROMPT t=RETURN>{grey}Search Again<BR>')
            else:
                conn.SendTML(f'<BR><RED>P{grey}rev Page,')
                conn.SendTML(f'<RED>N{grey}ext Page,')
                conn.SendTML(f'<RED><BACK>{grey}Exit<BR>')
                conn.SendTML(f'<KPROMPT t=RETURN>{grey}Search Again<BR>')
            conn.SendTML('<BR>Select:')
            sel = _dec(conn.ReceiveStr(keys, 10, False))
            if sel.upper() == 'P':
                page = max(0,page-1)
            if sel.upper() == 'N':
                page = min(nradios//pcount, page+1)
            if sel == '':
                conn.SendTML(f'<WINDOW top=0 bottom={lines}>')
                break
            if sel == back:
                conn.SendTML(f'<WINDOW top=0 bottom={lines}>')
                return()
            if sel.isdigit() and int(sel) < nradios:
                url = searchRes[int(sel)]['url']
                image = searchRes[int(sel)]['favicon'] if len(searchRes[int(sel)]['favicon']) > 0 else None
                conn.SendTML(f'<WEBAUDIO url={url} image="{image}">')
                conn.SendTML(f'<NUL><CURSOR><TEXT border={ecolors["BLACK"]} background={ecolors["BLACK"]}>')
                RadioTitle(conn)

    conn.SendTML(f'<WINDOW top=0 bottom={lines}>')	#Set Text Window

def searchRadio(termino):
    urls = []
    res = []
    try:
        query = rb.search(name=termino, name_exact=False)
        for i in query:
            if i['url'] not in urls:
                res.append(i)
                urls.append(i['url'])
    except:
        return False
    return res
