from common import turbo56k as TT
from common.style import bbsstyle
from common import filetools as FT
from common.helpers import formatX, crop, text_displayer
from common.connection import Connection
from common.bbsdebug import _LOG
from common.imgcvt import cropmodes, PreProcess

import wikipedia
import wikipediaapi
import string
from io import BytesIO
from PIL import Image
from bs4 import BeautifulSoup
from unicodedata import normalize
import requests
import sys, os

###############
# Plugin setup
###############
def setup():
    fname = "WIKI"
    parpairs = []
    return(fname,parpairs)

###################################
# Plugin callable function
###################################
def plugFunction(conn:Connection):

    def WikiTitle(conn:Connection):
        conn.SendTML(f'<WINDOW top=0 bottom={scheight-1}><CLR><BLACK>Wikipedia, the free Enciclopedia<BR>')
        if conn.QueryFeature(TT.LINE_FILL) < 0x80:
            conn.SendTML(f'{TxTtag}<LFILL row=1 code={hcode}>')
        else:
            conn.SendTML(f'{TxTtag}<HLINE n={scwidth}>')
        conn.Sendall(TT.set_Window(2,scheight-1))	#Set Text Window

    scwidth,scheight = conn.encoder.txt_geo
    if 'MSX' in conn.mode:
        hcode = 0x17
        bcode = 0x20
    else:
        hcode = 0x40
        bcode = 0xA0
    hdrs = {'User-Agent':'Mozilla/5.0 (X11; Linux x86_64; rv:87.0) Gecko/20100101 Firefox/87.0'}
    ecolors = conn.encoder.colors
    wcolors = bbsstyle(ecolors)
    wcolors.TxtColor = ecolors['DARK_GREY'] if 'PET' in conn.mode else ecolors['BLUE']
    TxTtag = '<GREY1>' if 'PET' in conn.mode else '<BLUE>'
    wcolors.PbColor = ecolors['BLACK']
    wcolors.PtColor = ecolors['BLUE']
    wikipedia.set_lang(conn.bbs.lang)
    wiki = wikipediaapi.Wikipedia(conn.bbs.lang, extract_format=wikipediaapi.ExtractFormat.HTML)
    sccolors = 'WHITE' if 'MSX' in conn.mode else 'LIGHT_GREY'
    conn.Sendall(TT.to_Text(0,ecolors[sccolors],ecolors[sccolors]))
    loop = True
    while loop == True:
        WikiTitle(conn)
        conn.SendTML('<BR>Search: <BR>(<BACK> to exit)<CRSRU><CRSRL n=3>')
        keys = string.ascii_letters + string.digits + ' +-_,.$%&'
        if conn.encoder.back not in keys:
            keys += conn.encoder.back
        termino = ''
        #Receive search term
        while termino == '':
            termino = conn.ReceiveStr(bytes(keys,'ascii'), 30, False)
            if conn.connected == False :
                return()
            if termino == conn.encoder.back:
                conn.Sendall(TT.set_Window(0,scheight))
                return()
        conn.SendTML('<SPINNER><CRSRL>')
        results = wikipedia.search(termino, results = scheight-10)
        conn.SendTML(' <BR><BR>Results:<BR><BR>')		#<-Note the white space at the start to erase the SPINNER wait character
        i = 0
        options = ''
        for r in results:
            res = crop(r,scwidth-4,conn.encoder.ellipsis)
            conn.SendTML(f'<BLACK>[<BLUE>{string.ascii_lowercase[i]}<BLACK>]{TxTtag}{res}<BR>')
            options += string.ascii_lowercase[i]
            i += 1
        conn.SendTML(f'<BLACK>[<BLUE><BACK><BLACK>]{TxTtag}Previous menu<BR><BR>Please select:')
        options += conn.encoder.back+conn.encoder.nl
        sel = conn.ReceiveKey(options)
        if sel == conn.encoder.back:
            loop = False
        elif sel != conn.encoder.nl:
            conn.Sendall(sel)
            conn.SendTML('<SPINNER><CRSRL>')
            i = options.index(sel)
            page = wiki.page(results[i])#wikipedia.page(results[i])
            try:
                resp = requests.get(page.fullurl)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.content, "html.parser")
                    if conn.QueryFeature(TT.PRADDR) < 0x80:
                        try:
                            im_p = soup.find(['table','td','div'],{'class':['infobox','infobox-image', 'infobox-full-data','sidebar-image','thumbinner']}).find('img')
                            if im_p != None:
                                src = im_p['src']
                                if src.startswith('//'):
                                    src = 'https:'+src
                                _LOG(f'Wikipedia: attempting to load image: {src}',id=conn.id, v=4)
                                scrap_im = requests.get(src, allow_redirects=True, headers = hdrs)
                                w_image = Image.open(BytesIO(scrap_im.content))
                                if w_image.mode == 'P':	#Check if indexed mode with transparency
                                    if w_image.info.get("transparency",-1) != -1:
                                        w_image = w_image.convert('RGBA')
                                if w_image.mode == 'LA': #Grayscale + alpha
                                    w_image = w_image.convert('RGBA')
                                if w_image.mode == 'RGBA':	#Possible SVG/logo, fill white
                                    if (w_image.size[0]/w_image.size[1]) > (4/3):
                                        timg = Image.new("RGBA", (w_image.size[0],w_image.size[0]*3//4),"WHITE")
                                    elif (w_image.size[0]/w_image.size[1]) < (4/3):
                                        timg = Image.new("RGBA", (w_image.size[1]*4//3,w_image.size[1]),"WHITE")
                                    else:
                                        timg = Image.new("RGBA", w_image.size, "WHITE")
                                    timg.paste(w_image,((timg.size[0]-w_image.size[0])//2,(timg.size[1]-w_image.size[1])//2),w_image)
                                    w_image = timg
                                FT.SendBitmap(conn,w_image, cropmode=cropmodes.FIT, preproc=PreProcess(1,1.3,1.3))
                                conn.ReceiveKey()
                                conn.SendTML(f'<NUL><CURSOR><TEXT border={ecolors[sccolors]} background={ecolors[sccolors]}>')
                        except Exception as e:
                            exc_type, exc_obj, exc_tb = sys.exc_info()
                            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                            _LOG(e,id=conn.id,v=1)
                            _LOG(fname+'|'+str(exc_tb.tb_lineno),id=conn.id,v=1)
                    WikiTitle(conn)
                tt = formatX(normalize('NFKC',page.title),scwidth)
                tt[0] = '<CLR><BLACK>'+tt[0]
                tt.append(f'{TxTtag}<HLINE n={scwidth}>')
                tt += WikiParseParas(page.summary,scwidth,0,TxTtag)	#<+
                tt.append('<BR>')
                tt += WikiSection(conn, page.sections,0)
                if conn.QueryFeature(TT.SCROLL) < 0x80:
                    conn.SendTML(f'<WINDOW top={scheight-1} bottom={scheight}><RVSON><BLUE><LFILL row={scheight-1} code={bcode}> [crsr/F1/F3] scroll  [<BACK>] exit<RVSOFF><WINDOW top=2 bottom={scheight-2}>')
                else:
                    conn.SendTML(f'<WINDOW top={scheight-1} bottom={scheight}><RVSON><BLUE><LFILL row={scheight-1} code={bcode}> [F1/F3] to scroll  [<BACK>] to exit<RVSOFF><WINDOW top=2 bottom={scheight-2}>')
                text_displayer(conn,tt,scheight-3,wcolors)
            except Exception as e:
                conn.SendTML('<RED><BR>ERROR!<PAUSE n=2>')
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                _LOG(e,id=conn.id,v=1)
                _LOG(fname+'|'+str(exc_tb.tb_lineno),id=conn.id,v=1)
    conn.Sendall(TT.set_Window(0,scheight-1))	#Set Text Window

##################################################################
# Parse a wiki article sections
##################################################################
def WikiSection(conn:Connection, sections, level = 0, lines = 0):
    tt = []
    scwidth = conn.encoder.txt_geo[0]
    TxTtag = '<GREY1>' if 'PET' in conn.mode else '<BLUE>'
    for s in sections:
        title = ('-'*level)+WikiParseTitles(s.title)
        ts = formatX(normalize('NFKC',title),scwidth)
        ts[0] = '<BLACK>'+ts[0]
        tt += ts
        tt.append(f'<HLINE n={scwidth}>{TxTtag}')
        tt += WikiParseParas(s.text,scwidth,0,TxTtag)	#<+
        tt.append('<BR>')
        tt += WikiSection(conn, s.sections, level + 1, lines)
    return(tt) #lines

##################################################################################################
# Get plain text,
# replace <p> and <br>with new lines
# based on: https://stackoverflow.com/questions/10491223/how-can-i-turn-br-and-p-into-line-breaks
##################################################################################################
def WikiParseParas(text, width = 40, level = 0,TxTtag='<GREY1>'):
    def replace_with_newlines(element):
        text = ''
        for elem in element.recursiveChildGenerator():
            if isinstance(elem, str):
                text += elem
            elif elem.name == 'br':
                text += '\n'
            elif elem.name == 'li':
                text += '\u2022'+elem.get_text()+'\n'
        return formatX(normalize('NFKC',text),width)
    
    if isinstance(text,str):
        soup = BeautifulSoup(text, "html.parser")
    else:
        soup = text
    plain_text = []
    for elem in soup.children:	#soup.findAll('p'):
        if elem.name == 'p':
            elem = replace_with_newlines(elem)
            plain_text+= elem
        elif elem.name == 'ul':
            for item in elem.find_all('li',recursive=False):
                key = next(item.stripped_strings,'')
                k = formatX(normalize('NFKC',key),width-2-level)
                k[0] =f'<SPC n={level}><BLACK>\u2022 {TxTtag}'+k[0]
                for i in range(1,len(k)):
                    k[i] = f'<SPC n={level+2}>'+k[i]
                plain_text += k
                nitem = item.find(['p','ul','ol'])
                if nitem:
                    plain_text += WikiParseParas(item,width,level+1,TxTtag)+['<BR>']
        elif elem.name == 'ol':
            for i,item in enumerate(elem.find_all('li',recursive=False)):
                key = next(item.stripped_strings,'')
                k = formatX(normalize('NFKC',key),width-2-level-len(str(i)))
                k[0] = f'<SPC n=level><BLACK>{i}. {TxTtag}{k[0]}'
                for i in range(1,len(k)):
                    k[i] = f'<SPC n={level+2}>'+k[i]
                plain_text += k
                nitem = item.find(['p','ul','ol'])
                if nitem:
                    plain_text += WikiParseParas(item,width,level+1,TxTtag)+'\r'		
        elif elem.name == 'dl':
            for item in elem.find_all('dd',recursive=False):
                key = next(item.stripped_strings,'')
                k = formatX(normalize('NFKC',key),width-level-1)
                k[0] =f'<SPC n={level+1}>{TxTtag}'+k[0]
                for i in range(1,len(k)):
                    k[i] = f'<SPC n={level+1}>'+k[i]
                plain_text += k
                nitem = item.find(['p','ul','ol'])
                if nitem:
                    plain_text += WikiParseParas(item,width,level+1,TxTtag)+['<BR>']
        elif elem.name == 'blockquote':
            nitem = elem.find(['p','ul','ol'])
            if nitem:
                plain_text += ['<BR>']+WikiParseParas(elem,width,level+1,TxTtag)+['<BR>']
    if plain_text == []:
        plain_text == formatX(normalize('NFKC',soup.get_text()),width)
    return(plain_text)

############################
# Parse wiki article titles
############################
def WikiParseTitles(text):
    soup = BeautifulSoup(text, "html.parser")
    return(soup.get_text())