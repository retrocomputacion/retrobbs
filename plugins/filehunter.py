import requests
import os
from bs4 import BeautifulSoup
import string
import feedparser
import xmltodict
from PIL import Image
from io import BytesIO
from math import ceil
from urllib.parse import urlparse,parse_qs, unquote, quote

from common.bbsdebug import _LOG,bcolors
from common.imgcvt import gfxmodes, PreProcess
from common import helpers as H
from common import style as S
from common.connection import Connection
from common import turbo56k as TT
from common import filetools as FT
from common.imgcvt import gfxmodes

### User Agent string used for some stingy content sources
hdrs = {'User-Agent':'Mozilla/5.0 (X11; Linux x86_64; rv:87.0) Gecko/20100101 Firefox/87.0'}

latest_releases = []
latest_timestamp = ''
allfiles = []

##################
# Plugin setup
##################
def setup():
    fname = "FILEHUNTER"  # UPPERCASE function name for config.ini
    parpairs = []   # config.ini Parameter pairs (name,defaultvalue)
    get_updatelog() # Get latest files, and allfiles lists
    return(fname,parpairs)

##############################
# Plugin callable function
##############################
def plugFunction(conn:Connection):

    scwidth,scheight = conn.encoder.txt_geo
    # Text mode
    refresh = True
    render = True
    entries = []
    ptext = ''
    # try:
    # Check if the file-hunter log has been updated
    conn.SendTML('<SPINNER>')
    log = requests.get('https://download.file-hunter.com/Update-Log.txt',allow_redirects=False,headers=hdrs)
    if log.status_code == 200:
        if log.headers['last-modified'] != latest_timestamp:
            _LOG('FILEHUNTER - updating file list'+bcolors.ENDC, id=conn.id,v=1)
            get_updatelog() # update local copy

    while conn.connected:
        if render:
            # conn.SendTML(f'<TEXT border={conn.style.BoColor} background={conn.style.BgColor}><CLR>{conn.templates.GetTemplate("csdb/menutitle",**{})}')
            conn.SendTML(f'<TEXT border={conn.style.BoColor} background={conn.style.BgColor}><CLR><MTITLE t=File-hunter>')
        if refresh:
            conn.SendTML(f'<WINDOW top=3 bottom={scheight-3}>')
            if conn.encoder.features['windows'] > 0:
                conn.SendTML('<CLR>')
            if entries == []:
                conn.SendTML('<SPINNER>')
                title = H.formatX('Latest on file-hunter.com',scwidth)
                lines = scheight-(8+len(title))
                for ix, e in enumerate(latest_releases):
                    purl = e[2]
                    entries.append({'title':unquote(os.path.basename(purl)),'url':purl})
                pages = ceil(len(entries)/lines)
                c_page = 0

            conn.SendTML(' <BR>')
            for t in title:
                conn.SendTML(t)
                if len(t)<scwidth:
                    conn.SendTML('<BR>')
            keys = [conn.encoder.back,'*']
            if pages > 1:
                keys.extend(['+','-'])
            for ix in range(min(lines,len(entries))):
                if ix+(c_page*lines) >= len(entries):
                    break
                text = H.crop(entries[ix+(c_page*lines)]['title'],scwidth-4,conn.encoder.ellipsis)
                S.KeyLabel(conn,H.valid_keys[ix],text,ix%2==0)
                conn.SendTML('<BR>')
                keys.append(H.valid_keys[ix])
            conn.SendTML(f'<WINDOW top=0 bottom={scheight}><AT x={len(ptext)} y={scheight-1}><DEL n={len(ptext)}><WHITE>')
            ptext = f'[{c_page+1}/{pages}]'
            conn.SendTML(ptext)
            refresh = False
        if render:
            conn.SendTML(conn.templates.GetTemplate('main/navbar',**{'barline':scheight-2,'crsr':'','pages':'+/-','keys':[('*','search')]}))
            render = False
        key = conn.ReceiveKey(keys)
        if key == '*':  # Search
            if conn.encoder.features['windows']== 0:
                conn.SendTML(f'<CLR>{conn.templates.GetTemplate("csdb/menutitle",**{})}')
            else:
                conn.SendTML(f'<WINDOW top=3 bottom={scheight-3}><CLR>')
            conn.SendTML('<BR><YELLOW>Search file-hunter: <WHITE>')
            term = conn.ReceiveStr(string.ascii_letters + string.digits + ' +-_,.$%&')
            conn.SendTML('<SPINNER>')
            result = [s for s in allfiles if term.lower() in os.path.basename(s).lower()]
            if len(result) > 0:
                entries = []
                for i in result:
                    entries.append({'title':os.path.basename(i),'url':'https://download.file-hunter.com/'+quote(i,safe='')})
                title = ['Search results:','']
                lines = scheight-(8+len(title))
                pages = ceil(len(entries)/lines)
                c_page = 0
                refresh = True
                if conn.encoder.features['windows'] == 0:
                    render = True
            else:
                refresh = True
                if conn.encoder.features['windows'] == 0:
                    render = True
        elif key == '-':
            if c_page > 0:
                c_page -= 1
                refresh = True
                if conn.encoder.features['windows'] == 0:
                    render = True
        elif key == '+':
            if c_page <= pages:
                c_page += 1
                refresh = True
                if conn.encoder.features['windows'] == 0:
                    render = True
        elif key != conn.encoder.back:
            url = entries[H.valid_keys.index(key)+(c_page*lines)]['url']
            conn.SendTML('<SPINNER>')
            d_resp = requests.get(url, allow_redirects = True, headers = hdrs)
            if d_resp.status_code == 200:
                # Save tmp file
                filename = f'{conn.bbs.Paths["temp"]}{entries[H.valid_keys.index(key)+(c_page*lines)]['title']}'
                with open(filename,'wb') as tf:
                    tf.write(d_resp.content)
                FT.SendFile(conn,filename,True,True)
                os.remove(filename)
                break
            else:
                conn.SendTML('<RED>ERROR!<PAUSE n=2><DEL n=6><BLUE>')                # if showrelease(conn, id) == False:
                conn.SendTML('<ORANGE>Error retreiving CSDb data<BR><PAUSE n=3>')
            refresh = True
            render = True
        else:
            break
    # except:
    #     _LOG('FILEHUNTER - '+bcolors.FAIL+'failed'+bcolors.ENDC, id=conn.id,v=1)
    conn.SendTML(f'<WINDOW top=0 bottom={scheight}><TEXT><CURSOR>')


def get_updatelog():
    global latest_releases, latest_timestamp, allfiles
    latest = requests.get('https://download.file-hunter.com/Update-Log.txt',allow_redirects=False,headers=hdrs) # Get file-hunter.com update log
    if latest.status_code == 200:
        latest_timestamp = latest.headers['last-modified']
        tmp = latest.content.decode('utf8').split('\r\n')   # Split in lines
        tmp = list(filter(lambda a: len(a) > 0 and '\t' in a and 'New' in a, tmp)) # Remove unwanted lines
        tmp = [l.replace(' ','\t').split('\t') for l in tmp]  # Split in fields
        for l in tmp:
            latest_releases.append(list(filter(lambda a: len(a) > 0, l)))
    all = requests.get('https://download.file-hunter.com/allfiles.txt',allow_redirects=False,headers=hdrs) # Get file-hunter.com complete file list
    if all.status_code == 200:
        allfiles = list(filter(lambda a: len(a) > 0, all.content.decode('utf8').replace('\\','/').split('\r\n')))
    