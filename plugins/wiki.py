from common import turbo56k as TT
from common.style import bbsstyle
from common import filetools as FT
from common.helpers import formatX, More, crop, text_displayer
from common.connection import Connection
from common.bbsdebug import _LOG
from common.imgcvt import gfxmodes, cropmodes, PreProcess

import wikipedia
import wikipediaapi
import string
from io import BytesIO
from PIL import Image
from bs4 import BeautifulSoup
import requests
import sys, os


#############################
#Plugin setup
def setup():
    fname = "WIKI"
    parpairs = []
    return(fname,parpairs)
#############################

##########################################
#Plugin callable function
def plugFunction(conn:Connection):

	def WikiTitle(conn:Connection):
		conn.SendTML('<WINDOW top=0 bottom=24><CLR><BLACK>Wikipedia, the free Enciclopedia<BR>')
		if conn.QueryFeature(TT.LINE_FILL) < 0x80:
			conn.SendTML('<GREY1><LFILL row=1 code=64>')
		else:
			conn.SendTML('<GREY1><HLINE n=40>')
		conn.Sendall(TT.set_Window(2,24))	#Set Text Window

	hdrs = {'User-Agent':'Mozilla/5.0 (X11; Linux x86_64; rv:87.0) Gecko/20100101 Firefox/87.0'}
	ecolors = conn.encoder.colors
	wcolors = bbsstyle(ecolors)
	wcolors.TxtColor = ecolors['DARK_GREY']
	wcolors.PbColor = ecolors['BLACK']
	wcolors.PtColor = ecolors['BLUE']

	wikipedia.set_lang(conn.bbs.lang)
	wiki = wikipediaapi.Wikipedia(conn.bbs.lang, extract_format=wikipediaapi.ExtractFormat.HTML)

	conn.Sendall(TT.to_Text(0,ecolors['LIGHT_GREY'],ecolors['LIGHT_GREY']))
	loop = True
	while loop == True:
		WikiTitle(conn)
		conn.SendTML('<BR>Search: <BR>(<LARROW> to exit)<CRSRU><CRSRL n=3>')

		keys = string.ascii_letters + string.digits + ' +-_,.$%&'
		termino = ''
		#Receive search term
		while termino == '':
			termino = conn.ReceiveStr(bytes(keys,'ascii'), 30, False)
			if conn.connected == False :
				return()
			if termino == '_':
				conn.Sendall(TT.set_Window(0,25))
				return()
		conn.SendTML('<CBM-B><CRSRL>')
		results = wikipedia.search(termino, results = 15)

		conn.SendTML(' <BR><BR>Results:<BR><BR>')		#<-Note the white space at the start to erase the COMM_B wait character

		i = 0

		options = ''

		for r in results:
			res = crop(r,36)
			conn.SendTML(f'<BLACK>[<BLUE>{string.ascii_lowercase[i]}<BLACK>]<GREY1>{res}<BR>')
			options += string.ascii_uppercase[i]
			i += 1
		conn.SendTML('<BLACK>[<BLUE><LARROW><BLACK>]<GREY1>Previous menu<BR><BR>Please select:')
		options += '_\r'
		sel = conn.ReceiveKey(bytes(options, 'ascii'))
		if sel == b'_':
			loop = False
		elif sel != b'\r':
			conn.Sendallbin(sel)
			conn.SendTML('<CBM-B><CRSRL>')
			i = options.index(sel.decode())
			page = wiki.page(results[i])#wikipedia.page(results[i])
			try:
				resp = requests.get(page.fullurl)
				if resp.status_code == 200:
					soup = BeautifulSoup(resp.content, "html.parser")
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
							# if (w_image.size[0]/w_image.size[1])<1: #Try to avoid chopping off heads
							# 	w_image = w_image.crop((0,0,w_image.size[0],w_image.size[0]*3/4))
							FT.SendBitmap(conn,w_image, cropmode=cropmodes.FIT, preproc=PreProcess(1,1.3,1.3))
							conn.ReceiveKey()
							conn.SendTML(f'<NUL><CURSOR><TEXT border={ecolors["LIGHT_GREY"]} background={ecolors["LIGHT_GREY"]}>')
							# conn.Sendall(TT.enable_CRSR()+TT.to_Text(0,ecolors['LIGHT_GREY'],ecolors['LIGHT_GREY']))
					except Exception as e:
						exc_type, exc_obj, exc_tb = sys.exc_info()
						fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
						_LOG(e,id=conn.id,v=1)
						_LOG(fname+'|'+str(exc_tb.tb_lineno),id=conn.id,v=1)
					WikiTitle(conn)
				tt = formatX(page.title)
				tt[0] = '<CLR><BLACK>'+tt[0]
				tt.append('<GREY1><HLINE n=40>')

				tt += WikiParseParas(page.summary)	#<+

				tt.append('<BR>')

				tt += WikiSection(conn, page.sections,0)

				if conn.QueryFeature(TT.SCROLL) < 0x80:
					conn.SendTML('<WINDOW top=24 bottom=25><RVSON><BLUE><LFILL row=24 code=160> [crsr/F1/F7] to scroll  [<LARROW>] to exit<RVSOFF><WINDOW top=2 bottom=23>')
					text_displayer(conn,tt,22,wcolors)
				else:
					More(conn,tt,22,wcolors)
			except Exception as e:
				conn.SendTML('<RED><BR>ERROR!<PAUSE n=2>')
				exc_type, exc_obj, exc_tb = sys.exc_info()
				fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
				_LOG(e,id=conn.id,v=1)
				_LOG(fname+'|'+str(exc_tb.tb_lineno),id=conn.id,v=1)

	conn.Sendall(TT.set_Window(0,24))	#Set Text Window

	#MenuBack()

def WikiSection(conn:Connection, sections, level = 0, lines = 0):

	tt = []
	for s in sections:
		title = ('-'*level)+WikiParseTitles(s.title)
		ts = formatX(title)
		ts[0] = '<BLACK>'+ts[0]
		tt += ts
		tt.append('<HLINE n=40><GREY1>')
		tt += WikiParseParas(s.text)	#<+
		tt.append('<BR>')
		tt += WikiSection(conn, s.sections, level + 1, lines)
	return(tt) #lines

# Get plain text,
# replace <p> and <br>with new lines
# based on: https://stackoverflow.com/questions/10491223/how-can-i-turn-br-and-p-into-line-breaks
def WikiParseParas(text, level = 0):
	def replace_with_newlines(element):
		text = ''
		for elem in element.recursiveChildGenerator():
			if isinstance(elem, str):
				text += elem
			elif elem.name == 'br':
				text += '\n'
			elif elem.name == 'li':
				text += '*'+elem.get_text()+'\n'
		return formatX(text)

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
				k = formatX(key,38-level)
				k[0] =f'<SPC n={level}><BLACK>* <GREY1>'+k[0]
				plain_text += k
				nitem = item.find(['p','ul','ol'])
				if nitem:
					plain_text += WikiParseParas(item,level=level+1)+['<BR>']
		elif elem.name == 'ol':
			for i,item in enumerate(elem.find_all('li',recursive=False)):
				key = next(item.stripped_strings,'')
				k = formatX(key,38-level-len(str(i)))
				k[0] = f'<SPC n=level><BLACK>{i}. <GREY1>{k[0]}'
				plain_text += k
				nitem = item.find(['p','ul','ol'])
				if nitem:
					plain_text += WikiParseParas(item,level=level+1)+'\r'				

	if plain_text == []:
		plain_text == formatX(soup.get_text())
	return(plain_text)

def WikiParseTitles(text):
	soup = BeautifulSoup(text, "html.parser")
	return(soup.get_text())