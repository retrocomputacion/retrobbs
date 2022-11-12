###################################
#       File transfer tools       #
###################################

from common.connection import Connection
import common.petscii as P
from PIL import Image
from common.c64cvt import c64imconvert
from io import BytesIO
import common.turbo56k as TT

# Display image dialog
def ImageDialog(conn:Connection, title, width=0, height=0):
	conn.Sendall(chr(P.CLEAR)+chr(P.GREY3)+chr(P.RVS_ON)+chr(TT.CMDON))
	for y in range(0,10):
		conn.Sendall(chr(TT.LINE_FILL)+chr(y)+chr(160))
	conn.Sendall(chr(TT.CMDOFF)+chr(P.GREY1)+TT.Fill_Line(10,226)+chr(P.GREY3))
	conn.Sendall(title.center(40,chr(P.HLINE))+'\r\r')
	conn.Sendall(chr(P.RVS_ON)+' oRIGINAL SIZE: '+str(width)+'x'+str(height)+'\r\r')
	conn.Sendall(chr(P.RVS_ON)+' sELECT:\r\r'+chr(P.RVS_ON)+' < m > FOR MULTICOLOR CONVERSION\r')
	conn.Sendall(chr(P.RVS_ON)+' < h > FOR HI-RES CONVERSION')
	if conn.ReceiveKey(b'HM') == b'H':
		return 0
	return 1

#Send bitmap image
def SendBitmap(conn:Connection, filename, lines = 25, display = True, dialog = False, multi = True):


	ftype = {'.ocp':1,'.OCP':1,	#Advanced Art Studio
			'.koa':2,'.KOA':2,'.kla':2,'.KLA':2,	#Koala Paint
			'.art':3,'.ART':3,	#Art Studio
			'.gif':4,'.GIF':4,
			'.png':5,'.PNG':5,
			'.jpg':6,'.JPG':6}

	ftitle = {4:' gif  iMAGE ', 5:' png  iMAGE ', 6:' jpeg iMAGE '}

	#multi = False #Bitmap mode
	# Find image format
	Convert = [None]*5
	bgcolor = chr(0)

	if type(filename)==str:
		extension = filename[-4:]
		switch = ftype[extension]
	else:
		switch = 4

	if switch == 1:		#extension == '.ocp' or extension == '.OCP':
		# Open Advanced Art Studio image file
		archivo=open(filename,"rb")
		# Discard the first couple of bytes
		archivo.read(2)

		# Bitmap data
		Convert[1] = archivo.read(8000)
		# Screen data
		Convert[2] = archivo.read(1000)
		# Read border color
		borde = archivo.read(1)
		# Read background color
		bgcolor = archivo.read(1)
		# Skip the next 14 bytes
		archivo.read(14)
		# Color data
		Convert[3] = archivo.read(1000)

		archivo.close()
		multi = True #Multicolor bitmap

	elif switch == 2:	#extension == '.koa' or extension == '.KOA' or extension == '.kla' or extension == '.KLA':
		# Open the Koala Paint image file
		archivo=open(filename,"rb")
		# Skip the first couple of bytes
		archivo.read(2)

		# Bitmap data
		Convert[1] = archivo.read(8000)
		# Screen data
		Convert[2] = archivo.read(1000)
		# Color data
		Convert[3] = archivo.read(1000)
		# Read background color
		bgcolor = archivo.read(1)
		borde = bgcolor

		# Close the file
		archivo.close()
		multi = True #Multicolor bitmap

	elif switch == 3:	#extension == '.art' or extension == '.ART':
		# Open the Art Studio image file
		archivo=open(filename,"rb")
		# Skip the first couple of bytes
		archivo.read(2)

		# Bitmap data
		Convert[1] = archivo.read(8000)
		# Screen data
		Convert[2] = archivo.read(1000)
		# Read border color
		borde = archivo.read(1)

		# Close file
		archivo.close()
		multi = False #Hi-res bitmaps

	elif 4 <= switch <= 6:	#extension in ('.gif','.png','.jpg','.GIF','.PNG','.JPG'):
		# or bytes/image object sent as filename parameter
		conn.Sendall(chr(P.COMM_B)+chr(P.CRSR_LEFT))
		try:
			if type(filename)==str:
				Source = Image.open(filename)
			elif type(filename)==bytes:
				Source = Image.open(BytesIO(filename))
			elif isinstance(filename,Image.Image):
				Source = filename
			Source = Source.convert("RGB")
			if dialog:
				mode = ImageDialog(conn,ftitle[switch],Source.size[0],Source.size[1])
				conn.Sendall(chr(P.COMM_B)+chr(P.CRSR_LEFT))
			else:
				mode = 1 if multi == True else 0
			Convert = c64imconvert(Source,mode)
			Source.close()
			bgcolor = Convert[4].to_bytes(1,'little')
			borde = bgcolor
			multi = mode == 1
		except:
			return()

	# Sync
	binariofinal = b'\x00'
	# Enter command mode
	binariofinal += b'\xFF'

	tchars = 40*lines
	tbytes = 320*lines

	# Set the transfer pointer + $10 (bitmap memory)
	binariofinal += b'\x81\x10'
	# Transfer bitmap block + Byte count (low, high)
	binariofinal += b'\x82'
	binariofinal += tbytes.to_bytes(2,'little')	#Block size
	# Bitmap data
	binariofinal += Convert[1][0:tbytes] #Bitmap
	# Set the transfer pointer + $00 (screen memory)
	binariofinal += b'\x81\x00'
	# Transfer screen block + Byte count (low, high)
	binariofinal += b'\x82'
	binariofinal += tchars.to_bytes(2,'little')	#Block size
	# Screen Data
	binariofinal += Convert[2][0:tchars] #Screen

	if multi:
		# Set the transfer pointer + $20 (color memory)
		binariofinal += b'\x81\x20'
		# Transfer color block + Byte count (low, high)
		binariofinal += b'\x82'	# Color data
		binariofinal += tchars.to_bytes(2,'little')	#Block size
		binariofinal += Convert[3][0:tchars] #ColorRAM
		if display:
			# Switch to multicolor mode + Page number: 0 (default) + Border color: borde + Background color: bgcolor
			binariofinal += b'\x92\x00'
			binariofinal += borde
			binariofinal += bgcolor
	elif display:
		# Switch to hires mode + Page number: 0 (default) + Border color: borde
		binariofinal += b'\x91\x00'
		binariofinal += borde
	# Exit command mode
	binariofinal += b'\xFE'
	if display:
		conn.Sendall(TT.disable_CRSR())	#Disable cursor blink
	conn.Sendallbin(binariofinal)
	return bgcolor
