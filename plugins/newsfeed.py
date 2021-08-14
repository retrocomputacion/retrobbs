import requests
import textwrap
from bs4 import BeautifulSoup
import feedparser
from PIL import Image
from io import BytesIO
import time
from urllib.parse import urlparse,urljoin

from common.bbsdebug import _LOG,bcolors
import common.helpers as H
import common.style as S
from common.connection import Connection
import common.petscii as P
import common.turbo56k as TT
import common.filetools as FT

### User Agent string used for some stingy content sources
hdrs = {'User-Agent':'Mozilla/5.0 (X11; Linux x86_64; rv:87.0) Gecko/20100101 Firefox/87.0'}




#############################
#Plugin setup
def setup():
    fname = "NEWSFEED" #UPPERCASE function name for config.ini
    parpairs = [('url','')] #config.ini Parameter pairs (name,defaultvalue)
    return(fname,parpairs)
#############################

 

##########################################
#Plugin callable function
def plugFunction(conn,url):
    
    if conn.menu != -1:
        conn.MenuStack.append([conn.MenuDefs,conn.menu])
        conn.menu = -1

    MenuDic = {
			    b'_': (H.MenuBack,(conn,),"pREVIOUS mENU",True,False),
				b'\r': (plugFunction,(conn,url),"",False,False)
			  }


    #conn.Sendall(chr(0))
    # # Text mode
    conn.Sendall(TT.to_Text(0,0,0))
    S.RenderMenuTitle(conn,"nEWSFEED")
    conn.Sendall(chr(P.COMM_B)+chr(P.CRSR_LEFT))

    nfeed = feedparser.parse(url)
    try:
        lines = 5
        _LOG('NewsFeeds - Feed: '+nfeed.feed.get('title','-no title-'),id=conn.id)

        conn.Sendall("rECENT FROM:\r")
        title = H.formatX(nfeed.feed.get('title','No title'))
        for t in title:
            conn.Sendall(t)
            if len(t)<40:
                conn.Sendall('\r')
        conn.Sendall('\r')
        lines +=len(title)

        i = 1
        for e in nfeed.entries:
            text = textwrap.shorten(e.get('title','No title'),width=72,placeholder='...')
            text = H.formatX(text,columns=36)
            lines+=len(text)
            if lines>22:
                continue
            conn.Sendall(chr(P.RVS_ON)+chr(H.menu_colors[i%2][0])+chr(181)+H.valid_keys[i-1]+chr(182)+chr(P.RVS_OFF)+chr(H.menu_colors[i%2][1]))
            x = 0
            for t in text:
                conn.Sendall(' '*(3*x)+t+'\r')
                x=1
            MenuDic[H.valid_keys[i-1].encode('ascii','ignore')] = (feedentry,(conn,e,P.toPETSCII(nfeed.feed.get('title','No title'))),H.valid_keys[i-1],True,False)
            i+=1
            #print(entries[-1]['href'])
        conn.Sendall(chr(P.RVS_ON)+chr(H.menu_colors[i%2][0])+chr(181)+'_'+chr(182)+chr(P.RVS_OFF)+chr(H.menu_colors[i%2][1])+'bACK\r')
        conn.Sendall(chr(P.WHITE)+'\ryOUR CHOICE: ')
        #print(MenuDic)
        return MenuDic

    except:
        _LOG('Newsfeed - '+bcolors.FAIL+'failed'+bcolors.ENDC, id=conn.id)

##############################################

def feedentry(conn,entry,feedname):
    _LOG('NewsFeeds - Entry: '+entry.get('title','-no title-'),id=conn.id)

    mtitle = textwrap.shorten(feedname,width=38-(len(conn.bbs.name)+7),placeholder='...')


    if webarticle(conn,entry.link,mtitle) == False:
        e_title = entry.get('title','')
        S.RenderMenuTitle(conn,mtitle)
        conn.Sendall(TT.set_Window(3,24))
        #conn.Sendall(chr(P.COMM_B)+chr(P.CRSR_LEFT))
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

        body = H.formatX(e_text)

        #body = H.formatX(a_body)
        title = H.formatX(e_title)
        title[0] = chr(P.WHITE)+title[0]
        title.append(chr(P.YELLOW)+chr(P.HLINE)*40+chr(P.PALETTE[S.default_style.TxtColor]))
        title.append('\r')
        text = title + body
        H.More(conn,text,22)
    conn.Sendall(TT.set_Window(0,24))

### Try to scrap data from wordpress and some other CMS sites,
### returns False if entry title or body cannot be found 
def webarticle(conn,url, feedname):
    conn.Sendall(chr(P.COMM_B)+chr(P.CRSR_LEFT))
    resp = requests.get(url, allow_redirects = False, headers = hdrs)
    r = 0   # Redirect loop disconnector
    while resp.status_code == 301 or resp.status_code == 302 and r < 10:
        url = resp.headers['Location']
        resp = requests.get(url, allow_redirects = False, headers = hdrs)
        r += 1
    #for r in resp.history:
    #    print(r.status_code,r.url)
    purl = urlparse(url)
    top_url = purl.scheme + '://' + purl.netloc
    if resp.status_code == 200:
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
                    _LOG('Newsfeed - '+bcolors.WARNING+'webscrapping failed - no title - defaulting to rss data'+bcolors.ENDC, id=conn.id)
                    return(False)
            else:
                _LOG('Newsfeed - '+bcolors.WARNING+'webscrapping failed - no title - defaulting to rss data'+bcolors.ENDC, id=conn.id)
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
                _LOG('Newsfeed - '+bcolors.WARNING+'webscrapping failed - no body - defaulting to rss data'+bcolors.ENDC, id=conn.id)
                return(False)
        a_headers = a_body.find_all(['h2','h4'])
        body = []
        if len(a_headers) != 0:
            for h in a_headers:
                h2 = H.formatX(h.get_text())
                h2[0] = chr(P.PALETTE[S.default_style.HlColor])+h2[0]
                body += h2
                for el in h.next_siblings:
                    if el.name and el.name.startswith('h'):
                        break
                    if el.name == 'p':
                        p = H.formatX(el.get_text())
                        if len(p)>0:
                            p[0] = chr(P.PALETTE[S.default_style.TxtColor])+p[0]
                            body += p
                    body.append('\r')
        else:
            a_paras = a_body.find_all(['p'])
            for p in a_paras:
                body +=  H.formatX(p.get_text())+['\r']
            if body == []:
                body = H.formatX(a_body.get_text())
        #print(soup.find('div',{'class':'entry-content'}))
        #####   Entry image   #####
        d_img = soup.find('div',{'class':'entry-featured-image'})
        if d_img != None:
            a_img = d_img.find('img')
        else:
            a_img = None #soup.find('img',{'itemprop':'image'})
        if a_img == None:
            a_img = soup.find('img',{'class':['wp-post-image','header','news_image']})
            if a_img == None:
                a_img = a_body.find('img')
        if a_img != None:
            conn.Sendall(TT.disable_CRSR())
            FT.SendBitmap(conn,getImg(top_url,a_img),multi=True)
            conn.ReceiveKey()
            conn.Sendall(chr(P.CLEAR)+TT.to_Text(0,0,0)+TT.enable_CRSR())
        S.RenderMenuTitle(conn,feedname)
        conn.Sendall(TT.set_Window(3,24))
        #body = H.formatX(a_body)
        title = H.formatX(a_title)
        title[0] = chr(P.WHITE)+title[0]
        #print(a_title)
        title.append(chr(P.YELLOW)+chr(P.HLINE)*40)
        if a_author != None:
            title.append(chr(P.PALETTE[S.default_style.TxtColor])+'BY: '+chr(P.YELLOW)+P.toPETSCII(a_author))
            title.append('\r')
        body[0] = chr(P.GREY2)+body[0]
        text = title + body
        H.More(conn,text,22)
        conn.Sendall(TT.set_Window(0,24))
    else:
        conn.Sendall(chr(P.DELETE)+str(resp.status_code))
        time.sleep(1)
        _LOG('Newsfeed - '+bcolors.WARNING+'webscrapping failed - defaulting to rss description'+bcolors.ENDC, id=conn.id)
        return(False)
    return(True)


def getImg(url,img_t):
    src = img_t['src']
    print(url)
    print(src)
    src = urljoin(url, src)
    #if src.startswith('//'):
    #    src = 'http:'+src
    scrap_im = requests.get(src, allow_redirects=True, headers=hdrs)
    try:
        img = Image.open(BytesIO(scrap_im.content))
    except:
        img = Image.new("RGB",(320,200),"red")

    return(img)