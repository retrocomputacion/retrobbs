###############################################################################
# Podcast Plugin 20240826 written by Emanuele Laface                          #
#                                                                             #
# This plugin requires feedpareser to work and it is a Python                 #
# implementation of https://performance-partners.apple.com/search-api         #
# #############################################################################

from common import turbo56k as TT
from common import filetools as FT
from common import audio as AA
from common.imgcvt import cropmodes, PreProcess, gfxmodes, dithertype
from common.helpers import crop
from common.connection import Connection

import string
import feedparser
import requests
import io
from PIL import Image
import numpy

###############
# Plugin setup
###############
def setup():
    fname = "PODCAST"
    parpairs = []
    return(fname,parpairs)

###################################
# Plugin callable function
###################################
def plugFunction(conn:Connection):

    columns,lines = conn.encoder.txt_geo
    tml = f'<NUL n=2><SPLIT bgbottom={conn.encoder.colors["BLACK"]} mode="_C.mode"><CLR>'

    def PodcastTitle(conn:Connection):
        conn.SendTML(f'<WINDOW top=0 bottom={lines-1}><CLR><YELLOW>Search internet podcasts<BR>')
        if conn.QueryFeature(TT.LINE_FILL) < 0x80:
            if 'MSX' in conn.mode:
                conn.SendTML('<GREEN><LFILL row=1 code=23>')
            else:
                conn.SendTML('<GREEN><LFILL row=1 code=64>')
        else:
            conn.SendTML('<GREEN><HLINE n=40>')
        conn.Sendall(TT.set_Window(2,lines-1))	#Set Text Window
    ecolors = conn.encoder.colors
    conn.Sendall(TT.to_Text(0,ecolors['BLACK'],ecolors['BLACK']))
    loop = True
    while loop == True:
        PodcastTitle(conn)
        conn.SendTML('<BR>Search: <BR>(<BACK> to exit)<CRSRU><CRSRL n=3>')
        keys = string.ascii_letters + string.digits + ' +-_,.$%&'
        termino = ''
        #Receive search term
        while termino == '':
            termino = conn.ReceiveStr(bytes(keys,'ascii'), columns-10, False)
            if conn.connected == False :
                return()
            if termino == '_':
                conn.Sendall(TT.set_Window(0,lines))
                return()
        conn.SendTML('<BR><BR>Searching...<SPINNER><CRSRL>')
        searchRes = searchPodcast(termino)
        if searchRes == False:
            conn.SendTML('<ORANGE>Service unavailable...<PAUSE n=2>')
            continue
        elif searchRes['resultCount'] == 0:
            conn.SendTML('<YELLOW>No results...<PAUSE n=2>')
            continue
        page = 0
        npodcasts = searchRes['resultCount']
        pcount = lines-10
        if 'MSX' in conn.mode:
            grey = '<GREY>'
        else:
            grey = '<GREY1>'
        while True:
            conn.SendTML('<CLR><BR>Results:<BR><BR>')
            for i in range(pcount*page, min(pcount*(page+1),npodcasts)):
                if i > 9:
                    pos = str(i)
                else:
                    pos = " "+str(i)
                podcastName = crop(searchRes['results'][i]['collectionName'],columns-10,conn.encoder.ellipsis).ljust(columns-10)
                conn.SendTML(f' <BLUE>{pos} {grey}{podcastName}<BR>')
            if npodcasts < pcount:
                conn.SendTML(f'<BR><RED><BACK>{grey}Exit<BR>')
                conn.SendTML(f'<RED><KPROMPT t=RETURN>{grey}Search Again<BR>')
            else:
                conn.SendTML(f'<BR><RED>P{grey}rev Page,')
                conn.SendTML(f'<RED>N{grey}ext Page,')
                conn.SendTML(f'<RED><BACK>{grey}Exit<BR>')
                conn.SendTML(f'<KPROMPT t=RETURN>{grey}Search Again<BR>')
            conn.SendTML('<BR>Select:')
            sel = conn.ReceiveStr(bytes(keys,'ascii'), 10, False)
            if sel.upper() == 'P':
                page = max(0,page-1)
            if sel.upper() == 'N':
                page = min(npodcasts//pcount, page+1)
            if sel == '':
                conn.Sendall(TT.set_Window(0,lines))
                break
            if sel == '_':
                conn.Sendall(TT.set_Window(0,lines))
                return()
            if sel.isdigit() and int(sel) < npodcasts:
                episodes = getEpisodes(searchRes['results'][int(sel)])
                if episodes == False:
                    conn.SendTML('<ORANGE>Service unavailable...<PAUSE n=2>')
                    continue
                elif len(episodes) == 0:
                    conn.SendTML('<YELLOW>No episodes...<PAUSE n=2>')
                    continue
                faviconURL = searchRes['results'][int(sel)]['artworkUrl100']
                r = requests.get(faviconURL)
                if r.reason == 'OK':
                    newimage = Image.open(io.BytesIO(r.content))
                    newimage.thumbnail((110,110))
                else:
                    newimage = numpy.zeros((200,320,3), dtype=numpy.uint8)
                if conn.mode == "PET64":
                    gm = gfxmodes.C64HI
                elif conn.mode == "PET264":
                    gm = gfxmodes.P4HI
                else:
                    gm = conn.encoder.def_gfxmode

                favicon = FT.SendBitmap(conn,newimage, lines=12, cropmode=cropmodes.TOP ,gfxmode=gm,preproc=PreProcess(contrast=1.5,saturation=1.5),dither=dithertype.BAYER2, display=False)
                conn.Sendall(TT.split_Screen(12,False,ord(favicon),conn.encoder.colors.get('BLACK',0),mode=conn.mode))

                eppage = 0
                nepisodes = len(episodes)
                eppcount = lines-19
                if 'MSX' in conn.mode:
                    grey = '<GREY>'
                else:
                    grey = '<GREY1>'
                while True:
                    conn.SendTML(f'<CLR><BR>{str(nepisodes)} Episodes:<BR><BR>')
                    for i in range(eppcount*eppage, min(eppcount*(eppage+1),nepisodes)):
                        if i > 9:
                            eppos = str(i)
                        else:
                            eppos = " "+str(i)
                        episodeName = crop(episodes[i]['title'],columns-10,conn.encoder.ellipsis).ljust(columns-10)
                        conn.SendTML(f' <BLUE>{eppos} {grey}{episodeName}<BR>')
                    if nepisodes < eppcount:
                        conn.SendTML(f'<BR><RED><BACK>{grey}Exit<BR>')
                        conn.SendTML(f'<RED><KPROMPT t=RETURN>{grey}Back to Podcasts<BR>')
                    else:
                        conn.SendTML(f'<BR><RED>P{grey}rev Page,')
                        conn.SendTML(f'<RED>N{grey}ext Page,')
                        conn.SendTML(f'<RED><BACK>{grey}Exit<BR>')
                        conn.SendTML(f'<KPROMPT t=RETURN>{grey}Back to Podcasts<BR>')
                    conn.SendTML('<BR>Select:')
                    epsel = conn.ReceiveStr(bytes(keys,'ascii'), 10, False)
                    if epsel.upper() == 'P':
                        eppage = max(0,eppage-1)
                    if epsel.upper() == 'N':
                        eppage = min(nepisodes//eppcount, eppage+1)
                    if epsel == '':
                        conn.SendTML(tml)
                        conn.Sendall(TT.set_Window(0,lines))
                        break
                    if epsel == '_':
                        conn.SendTML(tml)
                        conn.Sendall(TT.set_Window(0,lines))
                        return()
                    if epsel.isdigit() and int(epsel) < nepisodes:
                        url = None
                        for link in episodes[int(epsel)]['links']:
                            if 'mpeg' in link['type']:
                                url = link['href']
                        if url == None:
                            conn.SendTML('<YELLOW>Invalid Stream...<PAUSE n=2>')
                        else:
                            fullname = episodes[int(epsel)]['title']
                            conn.SendTML('<SPINNER><CRSRL>')
                            AA.PlayAudio(conn, url, None)
                            conn.SendTML(f'<NUL><CURSOR><TEXT border={ecolors["BLACK"]} background={ecolors["BLACK"]}>')
                PodcastTitle(conn)

def searchPodcast(termino):
    baseurl = 'https://itunes.apple.com/search?entity=podcast&term='
    try:
        query = requests.get(baseurl+termino.replace(' ','+'))
    except:
        return False
    if (query.reason == 'OK'):
        return query.json()
    else:
        return False
def getEpisodes(podcast):
    try:
        query = feedparser.parse(podcast['feedUrl'])['entries']
    except:
        return False
    return query
