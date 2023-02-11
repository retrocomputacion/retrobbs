import common.petscii as P
import common.turbo56k as TT
from common.style import bbsstyle
import common.filetools as FT
from common.helpers import formatX, More, crop, text_displayer
from common.connection import Connection

import wikipedia
import wikipediaapi
import string
from io import BytesIO
from PIL import Image
from bs4 import BeautifulSoup
import requests


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
		conn.Sendall(TT.set_Window(0,24))	#Set Text Window
		conn.Sendall(chr(P.CLEAR)+chr(P.BLACK)+"wIKIPEDIA, THE fREE eNCICLOPEDIA\r")
		if conn.QueryFeature(TT.LINE_FILL) < 0x80:
			conn.Sendall(chr(P.GREY1)+TT.Fill_Line(1,64))#(chr(P.HLINE)*40))
		else:
			conn.Sendall(chr(P.GREY1)+(chr(P.HLINE)*40))
		conn.Sendall(TT.set_Window(2,24))	#Set Text Window

	wcolors = bbsstyle()
	wcolors.TxtColor = 11
	wcolors.PbColor = 0
	wcolors.PtColor = 6

	wikipedia.set_lang(conn.bbs.lang)
	wiki = wikipediaapi.Wikipedia(conn.bbs.lang)

	#conn.Sendall('bUSCAR wIKIPEDIA')
	#time.sleep(1)
	conn.Sendall(TT.to_Text(0,15,15))
	loop = True
	while loop == True:
		WikiTitle(conn)
		conn.Sendall("\rsEARCH: \r(_ TO EXIT)"+chr(P.CRSR_UP)+chr(P.CRSR_LEFT)*3)

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
		conn.Sendall(chr(P.COMM_B)+chr(P.CRSR_LEFT))
		results = wikipedia.search(termino, results = 15)

		conn.Sendall(' \r\rrESULTS:\r\r')		#<-Note the white space at the start to erase the COMM_B wait character

		i = 0

		options = ''

		for r in results:
			res = P.toPETSCII(r)	#''.join(c.lower() if c.isupper() else c.upper() for c in r)
			#res = unicodedata.normalize('NFKD',r).encode('ascii','ignore')
			res = crop(res,36)
			# if len(res) > 36:
			# 	res = res[0:33] + '...'
			conn.Sendall(chr(P.BLACK)+'[' + chr(P.BLUE) + string.ascii_uppercase[i] + chr(P.BLACK) + ']' + chr(P.GREY1))
			conn.Sendall(res + '\r')
			options += string.ascii_uppercase[i]
			i += 1

		conn.Sendall(chr(P.BLACK)+'[' + chr(P.BLUE) + '_' + chr(P.BLACK) + ']' + chr(P.GREY1) + 'pREVIOUS MENU\r')
		options += '_\r'
		conn.Sendall('\rpLEASE SELECT:')

		sel = conn.ReceiveKey(bytes(options, 'ascii'))
		
		if sel == b'_':
			loop = False
		elif sel != b'\r':
			conn.Sendallbin(sel)
			conn.Sendall(chr(P.COMM_B)+chr(P.CRSR_LEFT))
			i = options.index(sel.decode())
			page = wiki.page(results[i])#wikipedia.page(results[i])
			resp = requests.get(page.fullurl)
			if resp.status_code == 200:
				soup = BeautifulSoup(resp.content, "html.parser")
				try:
					im_p = soup.find(['table','td','div'],{'class':['infobox','infobox-image', 'infobox-full-data','sidebar-image','thumbinner']}).find('img')
					src = im_p['src']
					if src.startswith('//'):
						src = 'http:'+src
					scrap_im = requests.get(src, allow_redirects=True)
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
					if (w_image.size[0]/w_image.size[1])<1: #Try to avoid chopping off heads
						w_image = w_image.crop((0,0,w_image.size[0],w_image.size[0]*3/4))
					FT.SendBitmap(conn,w_image,multi=True)
					conn.ReceiveKey()
					conn.Sendall(TT.enable_CRSR()+TT.to_Text(0,15,15))
				except:
					pass
				WikiTitle(conn)
			tt = formatX(page.title)
			tt[0] = chr(P.CLEAR)+chr(P.BLACK)+tt[0]
			tt.append(chr(P.GREY1)+chr(P.HLINE)*40)

			tt += formatX(page.summary)	#<+

			tt.append('\r')

			tt += WikiSection(conn, page.sections,0)

			if conn.QueryFeature(TT.SCROLL) < 0x80:
				conn.Sendall(TT.set_Window(24,25)+chr(P.RVS_ON)+chr(P.BLUE)+TT.Fill_Line(24,160)+' <CRSR> TO SCROLL   <_> TO EXIT'+chr(P.RVS_OFF))
				conn.Sendall(TT.set_Window(2,23))
				text_displayer(conn,tt,22,wcolors)
			else:
				More(conn,tt,22,wcolors)

	conn.Sendall(TT.set_Window(0,24))	#Set Text Window

	#MenuBack()

def WikiSection(conn:Connection, sections, level = 0, lines = 0):

	tt = []
	for s in sections:
		title = ('-'*level)+s.title
		ts = formatX(title)
		ts[0] = chr(P.BLACK)+ts[0]
		tt += ts
		tt.append(chr(P.HLINE)*40+chr(P.GREY1))
		tt += formatX(s.text)	#<+
		tt.append('\r')
		tt += WikiSection(conn, s.sections, level + 1, lines)
	return(tt) #lines
