import requests
import textwrap
from PIL import Image
from io import BytesIO
from bs4 import BeautifulSoup
from bs4.element import Comment

from common import c64cvt
from common.bbsdebug import _LOG,bcolors
import common.helpers as H
import common.style as S
from common.connection import Connection
import common.petscii as P
import common.turbo56k as TT
import common.filetools as FT

#############################
#Plugin setup
def setup():
    fname = "HACKADAY" #UPPERCASE function name for config.ini
    parpairs = [] #config.ini Parameter pairs (name,defaultvalue)
    return(fname,parpairs)
#############################

def getImg(img_t):
    src = img_t['src']
    # print(src)
    if src.startswith('//'):
        src = 'http:'+src
    scrap_im = requests.get(src, allow_redirects=True)
    img = Image.open(BytesIO(scrap_im.content))

    return(img)
    

##########################################
#Plugin callable function
def plugFunction(conn):
    
    if conn.menu != -1:
        conn.MenuStack.append([conn.MenuDefs,conn.menu])
        conn.menu = -1

    MenuDic = {
			    b'_': (H.MenuBack,(conn,),"pREVIOUS mENU",True,False),
				b'\r': (plugFunction,(conn,),"",False,False)
			  }

    _LOG('HACKADAY - webscrapping recent',id=conn.id)

    conn.Sendall(chr(0))
    # # Text mode
    conn.Sendall(TT.to_Text(0,0,0))

    S.RenderMenuTitle(conn,"hackaday")

    conn.Sendall(chr(P.COMM_B)+chr(P.CRSR_LEFT))    #Wait cursor

    url = "https://hackaday.com"
    resp = requests.get(url)
    if resp.status_code == 200:
        conn.Sendall(' '+chr(P.DELETE))
        soup = BeautifulSoup(resp.content, "html.parser")
        e_ul = soup.find('ul',{'class':'recent_entries-list'})
        i = 1
        conn.Sendall("rECENT FROM THE BLOG:\r\r")
        for e in e_ul.find_all('h2'):
            entry = (e.find('a'))
            #print('-'+valid_keys[i-1])+' '+entries[-1].get_text())
            text = textwrap.shorten(entry.get_text(),width=72,placeholder='...')
            text = H.formatX(text,columns=36)
            conn.Sendall(chr(P.RVS_ON)+chr(H.menu_colors[i%2][0])+chr(181)+H.valid_keys[i-1]+chr(182)+chr(P.RVS_OFF)+chr(H.menu_colors[i%2][1]))
            x = 0
            for t in text:
                conn.Sendall(' '*(3*x)+t+'\r')
                x=1
            MenuDic[H.valid_keys[i-1].encode('ascii','ignore')] = (hadarticle,(conn,entry['href']),H.valid_keys[i-1],True,False)
            i+=1
            #print(entries[-1]['href'])
        conn.Sendall(chr(P.RVS_ON)+chr(H.menu_colors[i%2][0])+chr(181)+'_'+chr(182)+chr(P.RVS_OFF)+chr(H.menu_colors[i%2][1])+'bACK\r')
        conn.Sendall(chr(P.WHITE)+'\ryOUR CHOICE: ')
        #print(MenuDic)
        return MenuDic

    else:
        _LOG('HACKADAY - '+bcolors.FAIL+'webscrapping failed'+bcolors.ENDC, id=conn.id)

##############################################

def hadarticle(conn,url):
    conn.Sendall(chr(P.COMM_B)+chr(P.CRSR_LEFT))
    resp = requests.get(url)
    if resp.status_code == 200:
        soup= BeautifulSoup(resp.content, "html.parser")
        a_title = soup.find('h1',{'itemprop':'name'}).get_text()
        a_author = soup.find('a',{'rel':'author'}).get_text()
        a_body = soup.find('div',{'class':'entry-content'})
        a_headers = a_body.find_all(['h2'])
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
                        p[0] = chr(P.PALETTE[S.default_style.TxtColor])+p[0]
                        body += p
                    body.append('\r')
        else:
            a_paras = a_body.find_all(['p'])
            for p in a_paras:
                body +=  H.formatX(p.get_text())
        #print(soup.find('div',{'class':'entry-content'}))
        a_img = soup.find('img',{'itemprop':'image'})
        conn.Sendall(TT.disable_CRSR())
        FT.SendBitmap(conn,getImg(a_img),multi=True)
        conn.ReceiveKey()
        conn.Sendall(chr(P.CLEAR)+TT.to_Text(0,0,0)+TT.enable_CRSR())
        S.RenderMenuTitle(conn,'HACKADAY')
        conn.Sendall(TT.set_Window(3,24))
        #body = H.formatX(a_body)
        title = H.formatX(a_title)
        title[0] = chr(P.WHITE)+title[0]
        title.append(chr(P.PALETTE[S.default_style.TxtColor])+'BY: '+chr(P.YELLOW)+P.toPETSCII(a_author)+chr(P.GREY3))
        title.append('\r')
        text = title + body
        H.More(conn,text,22)
        conn.Sendall(TT.set_Window(0,24))
    else:
        _LOG('HACKADAY - '+bcolors.FAIL+'webscrapping failed'+bcolors.ENDC, id=conn.id)


