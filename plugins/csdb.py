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

### Release types
release_types64 = ['C64 Demo','C64 One-File Demo','C64 Intro','C64 4K Intro','C64 Crack Intro','REU Release','C64 Music','C64 Music Collection','C64 Graphics',
                 'C64 Graphics Collection','C64 Game','C64 32K Game','C64 Diskmag','C64 Charts','C64 Tool','C64 Invitation','C64 Misc.','C64 1K Intro',
                 'C64 Game Preview','C64 Crack','C64 Basic Demo','C64 Hardware','C64 Fake Demo','C64 Tool Collection','C64 Papermag',
                 'SuperCPU Release','C64 1K Game','C64 2K Game','C64 512b Game','C64 4K Game','C64 256b Intro',
                 'IDE64 Release','C64 Fake Game','BBS Software','BBS Graphics','C64 Intro Collection','Related Release']
release_types128 = ['C128 Release']
release_typesother = ['C64 Disk Cover','C64 Votesheet','C64 DTV','EasyFlash Release','Other Platform C64 Tool']

###############
# Plugin setup
###############
def setup():
    fname = "CSDB" #UPPERCASE function name for config.ini
    parpairs = [] #config.ini Parameter pairs (name,defaultvalue)
    return(fname,parpairs)
#############################

#######################################
# Plugin callable function
#######################################
def plugFunction(conn:Connection):

    url = "https://csdb.dk/rss/latestreleases.php"
    search_url = "https://csdb.dk/search/?seinsel=releases&all=1&search="

    scwidth,scheight = conn.encoder.txt_geo
    # Text mode
    refresh = True
    render = True
    entries = []
    # try:
    r_types = release_types64
    if 'PET128' in conn.mode:
        r_types.extend(release_types128)
    elif 'PET' not in conn.mode:
        r_types.extend(release_types128)
        r_types.extend(release_typesother)

    while conn.connected:
        if render:
            conn.SendTML(f'<TEXT border={conn.style.BoColor} background={conn.style.BgColor}><CLR>{conn.templates.GetTemplate("csdb/menutitle",**{})}')
        if refresh:
            conn.SendTML(f'<WINDOW top=3 bottom={scheight-3}>')
            if conn.encoder.features['windows'] > 0:
                conn.SendTML('<CLR>')
            if entries == []:
                conn.SendTML('<SPINNER>')
                nfeed = feedparser.parse(url)
                title = H.formatX(nfeed.feed.get('title','No title'),scwidth)
                lines = scheight-(8+len(title))
                for ix, e in enumerate(nfeed.entries):
                    soup = BeautifulSoup(e.summary,'html.parser')
                    links = soup.find_all(lambda tag: tag.name == 'a' and tag.text in release_types64)
                    if len(links) == 0: #Skip if entry release type doesnt match
                        continue
                    purl = urlparse(e.link)
                    entries.append({'title':e.get('title','No title'),'id':parse_qs(purl.query)["id"][0]})
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
                text = H.crop(entries[ix+(c_page*lines)]['title'],scwidth-4,conn.encoder.ellipsis)
                S.KeyLabel(conn,H.valid_keys[ix],text,ix%2==0)
                conn.SendTML('<BR>')
                keys.append(H.valid_keys[ix])
            conn.SendTML(f'<WINDOW top=0 bottom={scheight}><AT x=0 y={scheight-1}><WHITE>[{c_page+1}/{pages}]')
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
            conn.SendTML('<BR><YELLOW>Search CSDb: <WHITE>')
            term = conn.ReceiveStr(string.ascii_letters + string.digits + ' +-_,.$%&')
            conn.SendTML('<SPINNER>')
            resp = requests.get(search_url+quote(term,safe=''), allow_redirects = True, headers = hdrs)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content,'html.parser')
                stitle = soup.find('head').find('title').string
                if '- Search for ' in stitle:
                    entries = []
                    olist = soup.find('body').find_all('li')
                    for i in olist:
                        v_item = i.find('img')
                        if v_item != None:
                            if v_item['src'] == '/gfx/icon-dllink.gif':
                                links = i.find_all('a')[1]
                                r_type = (links.next_sibling.string)
                                r_type = r_type[r_type.find("(")+1:r_type.find(")")]
                                if r_type not in r_types:
                                    continue
                                purl = urlparse(links['href'])
                                entries.append({'title':links.string,'id':parse_qs(purl.query)["id"][0]})
                    title = ['Search results:','']
                    lines = scheight-(8+len(title))
                    pages = ceil(len(entries)/lines)
                    c_page = 0
                else:   # Single match
                    purl = urlparse(resp.url)
                    conn.SendTML(f'<WINDOW top=0 bottom={scheight}>')
                    if showrelease(conn,parse_qs(purl.query)["id"][0]) == False:
                        conn.SendTML('<ORANGE>Error retreiving CSDb data<BR><PAUSE n=3>')
                    else:
                        render = True
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
            id = entries[H.valid_keys.index(key)+(c_page*lines)]['id']
            if showrelease(conn, id) == False:
                conn.SendTML('<ORANGE>Error retreiving CSDb data<BR><PAUSE n=3>')
            refresh = True
            render = True
        else:
            break
    # except:
    #     _LOG('CSDb - '+bcolors.FAIL+'failed'+bcolors.ENDC, id=conn.id,v=1)


#############################################################
# Show release info
#############################################################
def showrelease(conn:Connection,id):
    conn.SendTML('<SPINNER>')
    st = conn.style
    top_url = f'https://csdb.dk/webservice/?type=release&id={id}&depth=2'
    # top_url = f'https://csdb.dk/webservice/?type=release&id=251393&depth=2'    #251393
    resp = requests.get(top_url, allow_redirects = False, headers = hdrs)
    if resp.status_code == 200:
        scwidth,scheight = conn.encoder.txt_geo
        try:
            xmldata = xmltodict.parse(resp.content)
        except:
            return False
        release = xmldata['CSDbData']['Release']
        r_type = release['Type'] 
        gfx_type = release.get('GfxType','')
        r_day = int(release.get('ReleaseDay',1))
        r_month = int(release.get('ReleaseMonth',1))
        r_year = int(release.get('ReleaseYear',1970))
        dfmt = conn.user_prefs['datef']
        if dfmt == 0:
            dstr = f'{r_day:02d}/{r_month:02d}/{r_year}'
        elif dfmt == 1:
            dstr = f'{r_month:02d}/{r_day:02d}/{r_year}'
        else:
            dstr = f'{r_year}/{r_month:02d}/{r_day:02d}'
        if 'ReleasedBy' in release:
            rlist = []
            if 'Handle' in release['ReleasedBy']:
                handles = release['ReleasedBy']['Handle']
                if type(handles) != list:
                    handles = [handles]
                for h in handles:
                    rlist.append(h.get('Handle','???'))
            elif 'Group' in release['ReleasedBy']:
                groups = release['ReleasedBy']['Group']
                if type(groups) != list:
                    groups = [groups]
                for g in groups:
                    rlist.append(g.get('Name','???'))
            if len(rlist) > 0:
                r_by = ', '.join(rlist)
            else:
                r_by = ''
        else:
            r_by = ''
        dlinks = []
        # Get valid download links
        if 'DownloadLinks' in release:
            downloads = release['DownloadLinks']['DownloadLink']
            if type(downloads) != list:
                downloads = [downloads]
            for dl in downloads:
                if dl['Status'] == 'Ok':
                    if 'PET' in conn.mode:
                        if dl['Link'].split('.')[-1].upper() in ['D64','D71','D81','ZIP','LHA','PRG','SEQ','SID']:
                            dlinks.append([dl['CounterLink'],unquote(dl['Link'].split('/')[-1])])
                    else:
                        dlinks.append([dl['CounterLink'],unquote(dl['Link'].split('/')[-1])])

        if 'PET' in conn.mode:
            # Try to select the best graphics mode
            if r_type == 'BBS Graphics':
                gfxmode = gfxmodes.C64HI
            elif r_type == 'C64 Graphics' and gfx_type in ['PETSCII','HiRes']:
                gfxmode = gfxmodes.C64HI
            else:
                gfxmode = gfxmodes.C64MULTI
        else:
            gfxmode = None

        #####   Release image   #####
        if conn.QueryFeature(TT.PRADDR) < 0x80 or (conn.T56KVer == 0 and len(conn.encoder.gfxmodes) > 0):
            try:
                imgurl = release['ScreenShot']
            except:
                imgurl = None
            if imgurl != None:
                conn.SendTML('<CURSOR enable=False>')
                FT.SendBitmap(conn,getImg(imgurl),gfxmode=gfxmode,cropmode=FT.cropmodes.CENTER,preproc=PreProcess())
                conn.ReceiveKey()
                conn.SendTML(f'<TEXT border={conn.style.BoColor} background={conn.style.BgColor}><CLR><CURSOR>')
        conn.SendTML(conn.templates.GetTemplate('csdb/menutitle',**{}))
        conn.SendTML(f'<BR><INK c={st.HlColor}>{release["Name"]}<BR>')
        conn.SendTML(f'<BR><WHITE>Type: <YELLOW>{r_type}{"("+gfx_type+")" if gfx_type != "" else ""}<BR>')
        if r_by != '':
            conn.SendTML(f'<WHITE>Released by: <YELLOW>{r_by}<BR><WHITE>O')
        else:
            conn.SendTML('<WHITE>Released o')
        conn.SendTML(f'n: <YELLOW>{dstr}<BR><BR>')
        keys = [conn.encoder.back]
        if len(dlinks) > 0:
            conn.SendTML('<GREEN>Downloads:<BR><BR>')
            for ix, dl in enumerate(dlinks):
                # ATTENTION: We assume there's less than 9 download links
                S.KeyLabel(conn,str(ix+1),H.crop(dl[1],scwidth-4,conn.encoder.ellipsis),ix%2==0)
                conn.SendTML('<BR>')
                keys.append(str(ix+1))
        conn.SendTML(f'<AT x=0 y={scheight-1}>')
        S.KeyLabel(conn, conn.encoder.back, 'Back',ix%2==0)
        conn.SendTML(' ')
        while conn.connected:
            key = conn.ReceiveKey(keys)
            if key.isnumeric():
                conn.SendTML('<BLUE><SPINNER>')
                d_resp = requests.get(dlinks[int(key)-1][0], allow_redirects = True, headers = hdrs)
                if d_resp.status_code == 200:
                    # Save tmp file
                    filename = f'{conn.bbs.Paths["temp"]}{dlinks[int(key)-1][1]}'
                    with open(filename,'wb') as tf:
                        tf.write(d_resp.content)
                    FT.SendFile(conn,filename,True,True)
                    os.remove(filename)
                    break
                    ...
                else:
                    conn.SendTML('<RED>ERROR!<PAUSE n=2><DEL n=6><BLUE>')
            else:
                break
    else:
        conn.SendTML(f'{resp.status_code}<PAUSE n=1>')
        _LOG('CSDb - '+bcolors.WARNING+'webservice failed'+bcolors.ENDC, id=conn.id,v=2)
        return(False)
    return(True)

#######################
# Get entry image
#######################
def getImg(src):
    scrap_im = requests.get(src, allow_redirects=True, headers=hdrs, timeout=10)
    try:
        img = Image.open(BytesIO(scrap_im.content))
    except:
        img = Image.new("RGB",(320,200),"red")
    return(img)

