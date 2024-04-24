import requests
import textwrap
from bs4 import BeautifulSoup
import feedparser
from PIL import Image
from io import BytesIO
from urllib.parse import urlparse,urljoin

from common.bbsdebug import _LOG,bcolors
from common.imgcvt import gfxmodes
from common import helpers as H
from common import style as S
from common.connection import Connection
from common import turbo56k as TT
from common import filetools as FT

### User Agent string used for some stingy content sources
hdrs = {'User-Agent':'Mozilla/5.0 (X11; Linux x86_64; rv:87.0) Gecko/20100101 Firefox/87.0'}

###############
# Plugin setup
###############
def setup():
    fname = "NEWSFEED" #UPPERCASE function name for config.ini
    parpairs = [('url','')] #config.ini Parameter pairs (name,defaultvalue)
    return(fname,parpairs)
#############################

#######################################
# Plugin callable function
#######################################
def plugFunction(conn:Connection,url):
    if conn.menu != -1:
        conn.MenuStack.append([conn.MenuDefs,conn.menu])
        conn.menu = -1
    colors = conn.encoder.colors
    scwidth,scheight = conn.encoder.txt_geo
    menucolors = [[colors['LIGHT_BLUE'],colors['LIGHT_GREY']],[colors['CYAN'],colors['YELLOW']]]
    MenuDic = {
                conn.encoder.back: (H.MenuBack,(conn,),"Previous menu",0,False),
                conn.encoder.nl: (plugFunction,(conn,url),"",0,False)
              }
    # Text mode
    conn.SendTML(f'<TEXT border={conn.style.BoColor} background={conn.style.BgColor}><CLR><MTITLE t=Newsfeed><SPINNER><CRSRL>')
    nfeed = feedparser.parse(url)
    try:
        lines = 5
        _LOG('NewsFeeds - Feed: '+nfeed.feed.get('title','-no title-'),id=conn.id,v=2)
        conn.SendTML("Recent from:<BR>")
        title = H.formatX(nfeed.feed.get('title','No title'),scwidth)
        for t in title:
            conn.SendTML(t)
        conn.SendTML('<BR>')
        lines +=len(title)
        i = 1
        for e in nfeed.entries:
            text = textwrap.shorten(e.get('title','No title'),width=72,placeholder='...')
            text = H.formatX(text,columns=scwidth-3)
            lines+=len(text)
            if lines>scheight-2:
                continue
            conn.SendTML(f'<RVSON><INK c={menucolors[i%2][0]}><L-NARROW>{H.valid_keys[i-1]}<R-NARROW><RVSOFF><INK c={menucolors[i%2][1]}>')
            x = 0
            for t in text:
                conn.SendTML(f'<SPC n={3*x}>{t}')
                x=1
            MenuDic[H.valid_keys[i-1]] = (feedentry,(conn,e,nfeed.feed.get('title','No title')),H.valid_keys[i-1],0,False)
            i+=1
        conn.SendTML(f'<RVSON><INK c={menucolors[i%2][0]}><L-NARROW><BACK><R-NARROW><RVSOFF><INK c={menucolors[i%2][1]}>Back<BR>'
                     f'<WHITE><BR>Your choice: ')
        return MenuDic
    except:
        _LOG('Newsfeed - '+bcolors.FAIL+'failed'+bcolors.ENDC, id=conn.id,v=1)

###############################################
# Parse an RSS/Atom feed entry
###############################################
def feedentry(conn:Connection,entry,feedname):
    _LOG('NewsFeeds - Entry: '+entry.get('title','-no title-'),id=conn.id,v=4)
    mtitle = textwrap.shorten(feedname,width=38-(len(conn.bbs.name)+7),placeholder='...')
    scwidth,scheight = conn.encoder.txt_geo
    if webarticle(conn,entry.link,mtitle) == False:
        if 'MSX' in conn.mode:
            bcode = 0xDB
        else:
            bcode = 0xA0
        e_title = entry.get('title','')
        S.RenderMenuTitle(conn,mtitle)
        conn.SendTML(f'<CYAN><LFILL row={scheight-1} code={bcode}><AT x=1 y={scheight-1}><RVSON><R-NARROW><LTBLUE>F1/F3/crsr:move<CYAN><L-NARROW><CRSRR n={scwidth-2-25}><R-NARROW><YELLOW><BACK>:exit<CYAN><L-NARROW><RVSOFF>')
        conn.Sendall(TT.set_Window(3,scheight-2))
        e_text = ''
        content = entry.get('content',[]) #Atom
        for c in content:
            if 'html' in c['type']: #Get first (x)html content entry
                e_text = c['value']
                continue
        if len(e_text) == 0:
            e_text = entry.get('description','') #RSS
        soup= BeautifulSoup(e_text, "html.parser")
        texts = soup.find_all(text=True)
        e_text = " ".join(t.strip() for t in texts)
        body = H.formatX(e_text,scwidth)
        title = H.formatX(e_title,scwidth)
        title[0] = '<WHITE>'+title[0]
        title.append(f'<YELLOW><HLINE n={scwidth}><INK c={conn.style.TxtColor}>')
        title.append('<BR>')
        text = title + body
        H.text_displayer(conn,text,scheight-4)
        #H.More(conn,text,22)
    conn.Sendall(TT.set_Window(0,scheight-1))

#############################################################
# Try to scrap data from wordpress and some other CMS sites,
# returns False if entry title or body cannot be found
#############################################################
def webarticle(conn:Connection,url, feedname):
    conn.SendTML('<SPINNER><CRSRL>')
    resp = requests.get(url, allow_redirects = False, headers = hdrs)
    r = 0   # Redirect loop disconnector
    while resp.status_code == 301 or resp.status_code == 302 and r < 10:
        url = resp.headers['Location']
        resp = requests.get(url, allow_redirects = False, headers = hdrs)
        r += 1
    purl = urlparse(url)
    top_url = purl.scheme + '://' + purl.netloc
    if resp.status_code == 200:
        scwidth,scheight = conn.encoder.txt_geo
        if 'MSX' in conn.mode:
            bcode = 0xDB
        else:
            bcode = 0xA0        
        soup= BeautifulSoup(resp.content, "html.parser")
        # Remove unwanted sections
        for div in soup.find_all(['div','nav','aside','header'],
        {'class':['author-bio','post-thumbnail','mg-featured-slider','random',
        'wp-post-nav','upprev_thumbnail','primary-sidebar','related-posts-list',
        'footer-widget-area','sidebar','sticky','titlewrapper','widget-title',
        'PopularPosts']}):
            div.decompose()
        # Replace </br> tags
        for br in soup.find_all("br"):
            br.replace_with('\n')
        #####   Title   #####
        try:
            a_title = soup.find(['h1','h2','h3'],{'class':['entry-title','post-title','title']}).get_text()
        except:
            a_title = None
        if a_title == None:
            t_soup = soup.find('div',{'class':['view-item','artikel_titel']})
            if t_soup != None:
                a_title = t_soup.find('a').get_text()
                if a_title == None:
                    _LOG('Newsfeed - '+bcolors.WARNING+'webscrapping failed - no title - defaulting to rss data'+bcolors.ENDC, id=conn.id,v=2)
                    return(False)
            else:
                _LOG('Newsfeed - '+bcolors.WARNING+'webscrapping failed - no title - defaulting to rss data'+bcolors.ENDC, id=conn.id,v=2)
                return(False)
        #####   Author   #####
        a_author = None
        a_soup = soup.find('a',{'rel':'author'})
        if a_soup != None:
            a_author = a_soup.get_text()
        else:
            a_soup = soup.find('a',{'class':'author-name'})
            if a_soup == None:
                a_soup = soup.find(['div','span','p'],[{'class':'author'},{'class':'lead'}])
                if a_soup != None:
                    a_author = a_soup.find('a').get_text()
            else:
                a_author = a_soup.get_text()
        #####   Body   #####
        a_body = soup.find('div',{'class':['entry','entry-content','the-content','entry-inner','post-content','node-content','article-body','artikel_tekst']})
        if a_body == None:
            a_body = soup.find('article')
            if a_body == None:
                _LOG('Newsfeed - '+bcolors.WARNING+'webscrapping failed - no body - defaulting to rss data'+bcolors.ENDC, id=conn.id,v=2)
                return(False)
        a_headers = a_body.find_all(['h2','h4'])
        body = []
        if len(a_headers) != 0:
            for h in a_headers:
                h2 = H.formatX(h.get_text(),scwidth)
                h2[0] = f'<INK c={conn.style.HlColor}>'+h2[0]
                body += h2
                for el in h.next_siblings:
                    if el.name and el.name.startswith('h'):
                        break
                    if el.name == 'p':
                        p = H.formatX(el.get_text(),scwidth)
                        if len(p)>0:
                            p[0] = f'<INK c={conn.style.TxtColor}>'+p[0]
                            body += p
                    body.append('<BR>')
        else:
            a_paras = a_body.find_all(['p'])
            for p in a_paras:
                body +=  H.formatX(p.get_text(),scwidth)+['<BR>']
            if body == []:
                body = H.formatX(a_body.get_text(),scwidth)
        #####   Entry image   #####
        if conn.QueryFeature(TT.PRADDR) < 0x80:
            d_img = soup.find('div',{'class':'entry-featured-image'})
            if d_img != None:
                a_img = d_img.find('img')
            else:
                a_img = None
            if a_img == None:
                a_img = soup.find('img',{'class':['wp-post-image','header','news_image']})
                if a_img == None:
                    a_img = a_body.find('img')
            if a_img != None:
                conn.Sendall(TT.disable_CRSR())
                FT.SendBitmap(conn,getImg(top_url,a_img))
                conn.ReceiveKey()
                conn.SendTML('<TEXT border={conn.style.BoColor} background={conn.style.BgColor}><CLR><CURSOR>')
        S.RenderMenuTitle(conn,feedname)
        conn.SendTML(f'<CYAN><LFILL row={scheight-1} code={bcode}><AT x=1 y={scheight-1}><RVSON><R-NARROW><LTBLUE>F1/F3/crsr:move<CYAN><L-NARROW><CRSRR n={scwidth-27}><R-NARROW><YELLOW><BACK>:exit<CYAN><L-NARROW><RVSOFF>')
        conn.Sendall(TT.set_Window(3,scheight-2))
        title = H.formatX(a_title,scwidth)
        title[0] = '<WHITE>'+title[0]
        title.append(f'<YELLOW><HLINE n={scwidth}>')
        if a_author != None:
            title.append(f'<INK c={conn.style.TxtColor}>by: <YELLOW>{H.crop(a_author,scwidth-3,conn.encoder.ellipsis)}<BR>')
            title.append('<BR>')
        body[0] = '<GREY2>'+body[0]
        text = title + body
        H.text_displayer(conn,text,scheight-4)
        conn.Sendall(TT.set_Window(0,scheight))
    else:
        conn.SendTML(f'<DEL>{resp.status_code}<PAUSE n=1>')
        _LOG('Newsfeed - '+bcolors.WARNING+'webscrapping failed - defaulting to rss description'+bcolors.ENDC, id=conn.id,v=2)
        return(False)
    return(True)

#######################
# Get entry image
#######################
def getImg(url,img_t):
    src = img_t['src']
    src = urljoin(url, src)
    scrap_im = requests.get(src, allow_redirects=True, headers=hdrs, timeout=10)
    try:
        img = Image.open(BytesIO(scrap_im.content))
    except:
        img = Image.new("RGB",(320,200),"red")
    return(img)