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
        conn.SendTML(f'<WINDOW top=0 bottom={scheight-1}><CLR><INK c={wcolors.HlColor}>{crop("Wikipedia, the free Encyclopedia",scwidth,conn.encoder.ellipsis)}')
        if conn.QueryFeature(TT.LINE_FILL) < 0x80:
            conn.SendTML(f'{TxTtag}<AT x=0 y=2><LFILL row=1 code={hcode}>')
        else:
            if conn.encoder.txt_geo[0] > 32:
                conn.SendTML('<BR>')
            if 'PET' in conn.mode:
                conn.SendTML(f'{TxTtag}<HLINE n={scwidth-1}><CRSRL><INS><HLINE>')
            else:
                conn.SendTML(f'{TxTtag}<HLINE n={scwidth}>')
        conn.SendTML(f'<WINDOW top=2 bottom={scheight-1}>')	#Set Text Window

    scwidth,scheight = conn.encoder.txt_geo

    hdrs = {'User-Agent':'Mozilla/5.0 (X11; Linux x86_64; rv:87.0) Gecko/20100101 Firefox/87.0'}
    wcolors = conn.templates.GetStyle('wiki/default')   #bbsstyle(ecolors)
    TxTtag = f'<INK c={wcolors.TxtColor}>'   #'<GREY1>' if '64' in conn.mode else '<GREY2>' if 'PET128' in conn.mode else '<BLUE>'
    if 'MSX' in conn.mode:
        hcode = 0x17
    else:
        hcode = 0x40


    wikipedia.set_lang(conn.bbs.lang)
    if wikipediaapi.__version__[1]<6:
        wiki = wikipediaapi.Wikipedia(conn.bbs.lang, extract_format=wikipediaapi.ExtractFormat.HTML)
    else:
        wiki = wikipediaapi.Wikipedia(user_agent='RetroBBS/0.60',language=conn.bbs.lang, extract_format=wikipediaapi.ExtractFormat.HTML)

    conn.SendTML(f'<TEXT page=0 border={wcolors.BoColor} background={wcolors.BgColor}>')
    loop = True
    while loop == True:
        WikiTitle(conn)
        if conn.encoder.features['cursor'] == True:
            conn.SendTML('<BR>Search: <BR>(<BACK> to exit)<CRSRU><CRSRL n=3>')
        else:
            conn.SendTML('<BR>Search (<BACK> to exit):')
        keys = string.ascii_letters + string.digits + ' +-_,.$%&'
        back = conn.encoder.decode(conn.encoder.back)
        if back not in keys:
            keys += back
        termino = ''
        #Receive search term
        while termino == '':
            termino = conn.encoder.decode(conn.ReceiveStr(keys, 30, False))
            if conn.connected == False :
                return()
            if termino == back:
                conn.SendTML(f'<WINDOW top=0 bottom={scheight}>')
                return()
        termino = conn.encoder.decode(termino)
        conn.SendTML('<SPINNER>')
        try:
            results = wikipedia.search(termino, results = scheight-10)
            conn.SendTML(' <BR><BR>Results:<BR><BR>')		#<-Note the white space at the start to erase the SPINNER wait character
            i = 0
            options = ''
            for r in results:
                res = crop(r,scwidth-4,conn.encoder.ellipsis)
                conn.SendTML(f'<INK c={wcolors.PbColor}>[<INK c={wcolors.PtColor}>{string.ascii_lowercase[i]}<INK c={wcolors.PbColor}>]{TxTtag}{res}<BR>')
                options += string.ascii_lowercase[i]
                i += 1
        except:
            conn.SendTML('<FORMAT><ORANGE> Could not perform seach...</FORMAT>')
        conn.SendTML(f'<INK c={wcolors.PbColor}>[<INK c={wcolors.PtColor}><BACK><INK c={wcolors.PbColor}>]{TxTtag}Previous menu<BR><BR>Please select:')
        options += back+conn.encoder.nl
        sel = conn.ReceiveKey(options)
        if sel == back:
            loop = False
        elif sel != conn.encoder.nl:
            conn.Sendall(sel)
            conn.SendTML('<SPINNER>')
            i = options.index(sel)
            page = wiki.page(results[i])#wikipedia.page(results[i])
            try:
                resp = requests.get(page.fullurl,  allow_redirects=True, headers = hdrs)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.content, "html.parser")
                    if conn.QueryFeature(TT.PRADDR) < 0x80 or (conn.T56KVer == 0 and len(conn.encoder.gfxmodes) > 0):
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
                                conn.SendTML(f'<NUL><CURSOR><TEXT border={wcolors.BoColor} background={wcolors.BgColor}>')
                        except Exception as e:
                            exc_type, exc_obj, exc_tb = sys.exc_info()
                            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                            _LOG(e,id=conn.id,v=1)
                            _LOG(fname+'|'+str(exc_tb.tb_lineno),id=conn.id,v=1)
                    WikiTitle(conn)
                tt = formatX(normalize('NFKC',page.title),scwidth)
                tt[0] = f'<CLR><INK c={wcolors.HlColor}>{tt[0]}'
                if 'PET' in conn.mode:
                    tt.append(f'{TxTtag}<HLINE n={scwidth-1}><BR>')
                else:
                    tt.append(f'{TxTtag}<HLINE n={scwidth}>')
                tt += WikiParseParas(page.summary,scwidth,0,wcolors)	#<+
                tt.append('<BR>')
                tt += WikiSection(conn, page.sections, 0, style=wcolors)

                conn.SendTML(f'<WINDOW top=0 bottom={scheight}>')
                if conn.QueryFeature(TT.SET_WIN) >= 0x80:
                    barline = 2
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

                conn.SendTML(conn.templates.GetTemplate('main/navbar',**{'pages':pages,'crsr':crsr,'barline':barline,'st':wcolors}))
                conn.SendTML(f'<WINDOW top=2 bottom={scheight-2}>')

                if conn.QueryFeature(TT.SET_WIN) >= 0x80:
                    conn.SendTML('<BR>')
                text_displayer(conn,tt,scheight-3,wcolors)
            except Exception as e:
                conn.SendTML('<RED><BR>ERROR!<PAUSE n=2>')
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                _LOG(e,id=conn.id,v=1)
                _LOG(fname+'|'+str(exc_tb.tb_lineno),id=conn.id,v=1)
    conn.SendTML(f'<WINDOW top=0 bottom={scheight-1}>')	#Set Text Window

##################################################################
# Parse a wiki article sections
##################################################################
def WikiSection(conn:Connection, sections, level = 0, lines = 0, style:bbsstyle= None):
    tt = []
    scwidth = conn.encoder.txt_geo[0]
    for s in sections:
        title = ('-'*level)+WikiParseTitles(s.title)
        ts = formatX(normalize('NFKC',title),scwidth)
        ts[0] = f'<INK c={style.HlColor}>{ts[0]}' #hlcolor+ts[0]
        tt += ts
        if 'PET' in conn.mode:
            tt.append(f'<HLINE n={scwidth-1}><BR><INK c={style.TxtColor}>')
        else:
            tt.append(f'<HLINE n={scwidth}><INK c={style.TxtColor}>')
    
        tt += WikiParseParas(s.text,scwidth,0,style)	#<+
        tt.append('<BR>')
        tt += WikiSection(conn, s.sections, level + 1, lines, style)
    return(tt) #lines

##################################################################################################
# Get plain text,
# replace <p> and <br>with new lines
# based on: https://stackoverflow.com/questions/10491223/how-can-i-turn-br-and-p-into-line-breaks
##################################################################################################
def WikiParseParas(text, width = 40, level = 0,style:bbsstyle = None):
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
                k[0] =f'<SPC n={level}><INK c={style.HlColor}>\u2022 <INK c={style.TxtColor}>'+k[0]
                for i in range(1,len(k)):
                    k[i] = f'<SPC n={level+2}>'+k[i]
                plain_text += k
                nitem = item.find(['p','ul','ol'])
                if nitem:
                    plain_text += WikiParseParas(item,width,level+1,style)+['<BR>']
        elif elem.name == 'ol':
            for i,item in enumerate(elem.find_all('li',recursive=False)):
                key = next(item.stripped_strings,'')
                k = formatX(normalize('NFKC',key),width-2-level-len(str(i)))
                k[0] = f'<SPC n=level><INK c={style.HlColor}>{i}. <INK c={style.TxtColor}>{k[0]}'
                for i in range(1,len(k)):
                    k[i] = f'<SPC n={level+2}>'+k[i]
                plain_text += k
                nitem = item.find(['p','ul','ol'])
                if nitem:
                    plain_text += WikiParseParas(item,width,level+1,style)+'\r'		
        elif elem.name == 'dl':
            for item in elem.find_all('dd',recursive=False):
                key = next(item.stripped_strings,'')
                k = formatX(normalize('NFKC',key),width-level-1)
                k[0] =f'<SPC n={level+1}><INK c={style.TxtColor}>'+k[0]
                for i in range(1,len(k)):
                    k[i] = f'<SPC n={level+1}>'+k[i]
                plain_text += k
                nitem = item.find(['p','ul','ol'])
                if nitem:
                    plain_text += WikiParseParas(item,width,level+1,style)+['<BR>']
        elif elem.name == 'blockquote':
            nitem = elem.find(['p','ul','ol'])
            if nitem:
                plain_text += ['<BR>']+WikiParseParas(elem,width,level+1,style)+['<BR>']
    if plain_text == []:
        plain_text == formatX(normalize('NFKC',soup.get_text()),width)
    return(plain_text)

############################
# Parse wiki article titles
############################
def WikiParseTitles(text):
    soup = BeautifulSoup(text, "html.parser")
    return(soup.get_text())