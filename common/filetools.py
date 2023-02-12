###################################
#       File transfer tools       #
###################################

import re
import os
import time
import itertools
from common.connection import Connection
import common.petscii as P
import common.helpers as H
from PIL import Image
from common.c64cvt import c64imconvert
from io import BytesIO
import common.turbo56k as TT
import common.style as S
from common.bbsdebug import _LOG, bcolors
from crc import Calculator, Crc16, Configuration

########################################################################
# Display image dialog
########################################################################
# conn: Connection
# title: Title of the dialog
# width/height: Original size of the image
# save: Show save option
########################################################################
# Returns:	Bit 1: Graphic mode 0: Hires | 1: Multicolor
#			Bit 7: 0: View Image | 1: Save image
########################################################################
def ImageDialog(conn:Connection, title, width=0, height=0, save=False):
	S.RenderDialog(conn, (11 if save and width !=0 else 10), title)
	conn.Sendall(TT.disable_CRSR())
	keys= b'\r'
	if width != 0:
		conn.Sendall(chr(P.RVS_ON)+' oRIGINAL SIZE: '+str(width)+'x'+str(height)+'\r\r')
		conn.Sendall(chr(P.RVS_ON)+' sELECT:\r\r'+chr(P.RVS_ON)+' * < m > FOR MULTICOLOR CONVERSION\r')
		conn.Sendall(chr(P.RVS_ON)+'   < h > FOR HI-RES CONVERSION\r')
		keys += b'HM'
	if save:
		conn.Sendall('\r'+chr(P.RVS_ON)+' < s > TO SAVE IMAGE\r')
		keys += b'S'
	conn.Sendall(chr(P.RVS_ON)+' < RETURN > TO VIEW IMAGE\r')
	out = 1
	while conn.connected:
		k = conn.ReceiveKey(keys)
		if k == b'H' and out == 1:
			conn.Sendall(chr(P.RVS_ON)+TT.set_CRSR(1,6)+' '+chr(P.CRSR_DOWN)+chr(P.CRSR_LEFT)+'*')
			out = 0
		elif k == b'M' and out == 0:
			conn.Sendall(chr(P.RVS_ON)+TT.set_CRSR(1,7)+' '+chr(P.CRSR_UP)+chr(P.CRSR_LEFT)+'*')
			out = 1
		elif k == b'S':
			out |= 0x80
			break
		elif k == b'\r':
			break
	conn.Sendall(chr(P.RVS_OFF)+TT.enable_CRSR())
	return out

###########################################################
# Send bitmap image
###########################################################
# conn: Connection to send the image/dialog to
# filename: file name or image object
# lines: Number of "text" lines to send, from the top
# display: Display the image after transfer
# dialog: Show convert options dialog before file transfer
# multi: Multicolor mode
# preproc: Preprocess image before converting
###########################################################
def SendBitmap(conn:Connection, filename, dialog = False, save = False, lines = 25, display = True,  multi = True, preproc = True):

	ftype = {'.ocp':1,'.OCP':1,	#Advanced Art Studio
			'.koa':2,'.KOA':2,'.kla':2,'.KLA':2,	#Koala Paint
			'.art':3,'.ART':3,	#Art Studio
			'.gif':4,'.GIF':4,
			'.png':5,'.PNG':5,
			'.jpg':6,'.JPG':6}

	ftitle = {4:' GIF  Image ', 5:' PNG  Image ', 6:' JPEG Image '}

	# Find image format
	Convert = [None]*5
	bgcolor = chr(0)

	mode = 1 if multi == True else 0

	save &= conn.QueryFeature(TT.FILETR) < 0x80

	if type(filename)==str:
		extension = os.path.splitext(filename)[1]
		switch = ftype[extension]
	else:
		switch = 4

	if switch == 1:		#extension == '.ocp' or extension == '.OCP':
		if dialog and save:
			out = ImageDialog(conn,'Advanced Art Studio',0,0,True)
		else:
			out = 0
		if (out & 0x80) == 0x80:	# Save image
			savename = os.path.splitext(os.path.basename(filename))[0].upper()
			savename = (savename.ljust(12,' ') if len(savename)<12 else savename[:12])+'MPIC'
			if TransferFile(conn, filename, savename):
				conn.Sendall(chr(P.CLEAR)+chr(P.TOLOWER)+chr(P.GREEN)+'fILE TRANSFER SUCCESSFUL!\r'+S.KeyPrompt('RETURN'))
			else:
				conn.Sendall(chr(P.CLEAR)+chr(P.TOLOWER)+chr(P.ORANGE)+'fILE TRANSFER ABORTED!\r'+S.KeyPrompt('RETURN'))
			return
		else:
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
		if dialog and save:
			out = ImageDialog(conn,'Koala Paint',0,0,True)
		else:
			out = 0
		if (out & 0x80) == 0x80:	# Save image
			savename = os.path.splitext(os.path.basename(filename))[0].upper()
			savename = chr(0x81)+'PIC A '+(savename.ljust(8,' ') if len(savename)<8 else savename[:8])
			if TransferFile(conn, filename, savename):
				conn.Sendall(chr(P.CLEAR)+chr(P.TOLOWER)+chr(P.GREEN)+'fILE TRANSFER SUCCESSFUL!\r'+S.KeyPrompt('RETURN'))
			else:
				conn.Sendall(chr(P.CLEAR)+chr(P.TOLOWER)+chr(P.ORANGE)+'fILE TRANSFER ABORTED!\r'+S.KeyPrompt('RETURN'))
			return
		else:
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
		if dialog and save:
			out = ImageDialog(conn,'Art Studio',0,0,True)
		else:
			out = 0
		if (out & 0x80) == 0x80:	# Save image
			savename = os.path.splitext(os.path.basename(filename))[0].upper()
			savename = (savename.ljust(13,' ') if len(savename)<13 else savename[:13])+'PIC'
			if TransferFile(conn, filename, savename):
				conn.Sendall(chr(P.CLEAR)+chr(P.TOLOWER)+chr(P.GREEN)+'fILE TRANSFER SUCCESSFUL!\r'+S.KeyPrompt('RETURN'))
			else:
				conn.Sendall(chr(P.CLEAR)+chr(P.TOLOWER)+chr(P.ORANGE)+'fILE TRANSFER ABORTED!\r'+S.KeyPrompt('RETURN'))
			return
		else:		# Open the Art Studio image file
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
				mode = ImageDialog(conn,ftitle[switch],Source.size[0],Source.size[1],save)
				if mode < 0:
					return()
				conn.Sendall(chr(P.COMM_B)+chr(P.CRSR_LEFT))
			else:
				mode = 1 if multi == True else 0
			Convert = c64imconvert(Source,mode & 0x7f,preproc=preproc)
			Source.close()
			bgcolor = Convert[4].to_bytes(1,'little')
			borde = bgcolor
			multi = (mode & 0x7f) == 1
		except:
			return()


	tchars = 40*lines
	tbytes = 320*lines

	if mode & 0x80 == 0:	# Transfer to memory
		# Sync
		binaryout = b'\x00'
		# Enter command mode
		binaryout += b'\xFF'
		# Set the transfer pointer + $10 (bitmap memory)
		binaryout += b'\x81\x10'
		# Transfer bitmap block + Byte count (low, high)
		binaryout += b'\x82'
		binaryout += tbytes.to_bytes(2,'little')	#Block size
		# Bitmap data
		binaryout += Convert[1][0:tbytes] #Bitmap
		# Set the transfer pointer + $00 (screen memory)
		binaryout += b'\x81\x00'
		# Transfer screen block + Byte count (low, high)
		binaryout += b'\x82'
		binaryout += tchars.to_bytes(2,'little')	#Block size
		# Screen Data
		binaryout += Convert[2][0:tchars] #Screen

		if multi:
			# Set the transfer pointer + $20 (color memory)
			binaryout += b'\x81\x20'
			# Transfer color block + Byte count (low, high)
			binaryout += b'\x82'	# Color data
			binaryout += tchars.to_bytes(2,'little')	#Block size
			binaryout += Convert[3][0:tchars] #ColorRAM
			if display:
				# Switch to multicolor mode + Page number: 0 (default) + Border color: borde + Background color: bgcolor
				binaryout += b'\x92\x00'
				binaryout += borde
				binaryout += bgcolor
		elif display:
			# Switch to hires mode + Page number: 0 (default) + Border color: borde
			binaryout += b'\x91\x00'
			binaryout += borde
		# Exit command mode
		binaryout += b'\xFE'
		if display:
			conn.Sendall(TT.disable_CRSR())	#Disable cursor blink
		conn.Sendallbin(binaryout)
		return bgcolor
	else:	# Save to file
		if multi:
			binaryout = b'\x00\x20' # Advanced Art Studio Load address
			binaryout += Convert[1][0:tbytes] #Bitmap
			binaryout += Convert[2][0:tchars] #Screen
			binaryout += borde
			binaryout += bgcolor
			binaryout += b'\x00'*14
			binaryout += Convert[3][0:tchars] #ColorRAM
			savename = os.path.splitext(os.path.basename(filename))[0].upper()
			savename = (savename.ljust(12,' ') if len(savename)<12 else savename[:12])+'MPIC'
		else:
			binaryout = b'\x00\x20' # Art Studio Load address
			binaryout += Convert[1][0:tbytes] #Bitmap
			binaryout += Convert[2][0:tchars] #Screen
			binaryout += borde
			savename = os.path.splitext(os.path.basename(filename))[0].upper()
			savename = (savename.ljust(13,' ') if len(savename)<13 else savename[:13])+'PIC'
		if TransferFile(conn, binaryout, savename):
			conn.Sendall(chr(P.CLEAR)+chr(P.TOLOWER)+chr(P.GREEN)+'fILE TRANSFER SUCCESSFUL!\r'+S.KeyPrompt('RETURN'))
		else:
			conn.Sendall(chr(P.CLEAR)+chr(P.TOLOWER)+chr(P.ORANGE)+'fILE TRANSFER ABORTED!\r'+S.KeyPrompt('RETURN'))
		return

#####################################################################################
# Sends a file to the client, calls the adequate function according to the filetype
#####################################################################################
# conn: Connection
# filename: path to the file to transfer
# dialog: Show dialog before transfer
# save: Allow file downloading to disc
###########################################
def SendFile(conn:Connection,filename, dialog = False, save = False):
	if os.path.exists(filename):
		ext = os.path.splitext(filename)[1].upper()
		if ext == '.PRG':
			if dialog:
				res = FileDialog(conn,os.path.basename(filename), os.path.getsize(filename), 'Commodore Program', save = save)
			else:
				res = 1+(1*save)
			if res == 1:
				SendProgram(conn,filename)
			elif res == 2:
				if TransferFile(conn,filename, P.toPETSCII(os.path.splitext(os.path.basename(filename))[0])):
					conn.Sendall(chr(P.CLEAR)+chr(P.TOLOWER)+chr(P.GREEN)+'fILE TRANSFER SUCCESSFUL!\r'+S.KeyPrompt('RETURN'))
				else:
					conn.Sendall(chr(P.CLEAR)+chr(P.TOLOWER)+chr(P.ORANGE)+'fILE TRANSFER ABORTED!\r'+S.KeyPrompt('RETURN'))
				conn.ReceiveKey()
			return
		elif ext in ['.SEQ','.TXT']:
			if dialog:
				res = FileDialog(conn,os.path.basename(filename), os.path.getsize(filename), 'Sequential/Text File', 'view', save = save)
			else:
				res = 1+(1*save)
			if res == 1:
				title = 'Viewing text file' if ext == '.TXT' else ''
				SendText(conn,filename,title)
			elif res == 2:
				if TransferFile(conn,filename, P.toPETSCII(os.path.splitext(os.path.basename(filename))[0]),True):
					conn.Sendall(chr(P.CLEAR)+chr(P.TOLOWER)+chr(P.GREEN)+'fILE TRANSFER SUCCESSFUL!\r'+S.KeyPrompt('RETURN'))
				else:
					conn.Sendall(chr(P.CLEAR)+chr(P.TOLOWER)+chr(P.ORANGE)+'fILE TRANSFER ABORTED!\r'+S.KeyPrompt('RETURN'))
				conn.ReceiveKey()
			return
		elif ext in ['.JPG','.GIF','.PNG','.OCP','.KOA','.KLA','.ART']:
			SendBitmap(conn,filename,dialog,save)
			conn.ReceiveKey()
		elif ext == '.C':
			...
		elif ext == '.PET':
			...
		elif save:	#Default -> download to disk
			if dialog:
				res = FileDialog(conn,os.path.basename(filename), os.path.getsize(filename), 'Commodore Program', prompt='save to disk', save = False)
			else:
				res = 1
			if res == 1:
				if TransferFile(conn,filename, P.toPETSCII(os.path.splitext(os.path.basename(filename))[0])):
					conn.Sendall(chr(P.CLEAR)+chr(P.TOLOWER)+chr(P.GREEN)+'fILE TRANSFER SUCCESSFUL!\r'+S.KeyPrompt('RETURN'))
				else:
					conn.Sendall(chr(P.CLEAR)+chr(P.TOLOWER)+chr(P.ORANGE)+'fILE TRANSFER ABORTED!\r'+S.KeyPrompt('RETURN'))
				conn.ReceiveKey()
	...

##################################################################################
# Sends program file into the client memory at the correct address in turbo mode
##################################################################################
#conn: Connection to send the file to
#filename: name+path of the file to be sent
##################################################################################
def SendProgram(conn:Connection,filename):
    # Verify .prg extension
    if filename[-4:] == '.prg' or filename[-4:] == '.PRG':
        _LOG('Memory transfer, filename: '+filename, id=conn.id,v=3)
        # Open file
        archivo=open(filename,"rb")
        # Read load address
        binario=archivo.read(2)
        # Sync
        binaryout = b'\x00'
        # Enter command mode
        binaryout += b'\xFF'

        # Set the transfer pointer + load address (low:high)
        filesize = os.path.getsize(filename) - 2
        binaryout += b'\x80'
        if isinstance(binario[0],str) == False:
            binaryout += binario[0].to_bytes(1,'big')
            binaryout += binario[1].to_bytes(1,'big')
        else:
            binaryout += binario[0]
            binaryout += binario[1]
        # Set the transfer pointer + program size (low:high)
        binaryout += b'\x82'
        binaryout += filesize.to_bytes(2,'little')
        _LOG('Load Address: '+bcolors.OKGREEN+str(binario[1]*256+binario[0])+bcolors.ENDC, '/ Bytes: '+bcolors.OKGREEN+str(filesize)+bcolors.ENDC,id=conn.id,v=4)
        # Program data
        binaryout += archivo.read(filesize)

        # Exit command mode
        binaryout += b'\xFE'
        # Close file
        archivo.close()
        # Send the data
        conn.Sendallbin(binaryout)


####################################################################################
# Transfer a file to be stored in media by the client
####################################################################################
#conn: Connection to send the file to
#file: name+path of the file to be sent or bytes
#savename: if defined, the filename sent to the client (mandatory if file is bytes)
####################################################################################
def TransferFile(conn:Connection, file, savename = None, seq=False):
	if isinstance(file,str):
		if os.path.exists(file) == False:
			return False
		else:
			with open(file,'rb') as fb:
				data = fb.read()
	else:
		data = file
	if (conn.QueryFeature(TT.FILETR) < 0x80):
		basename = os.path.basename(file).upper()
		conn.Sendall(chr(TT.CMDON)+chr(TT.FILETR))
		if os.path.splitext(basename)[1] == '.SEQ' or seq:
			conn.Sendallbin(b'\x00')	# File type: SEQ
		else:
			conn.Sendallbin(b'\xF0')	# File type: PRG
		if savename != None:
			basename = savename
		else:
			basename = os.path.splitext(basename)[0]
		time.sleep(0.1)
		conn.Sendall(basename+chr(0))
		repeats = 0
		b_crc = Calculator(Configuration(width=16, polynomial=0x1021, init_value=0xffff, final_xor_value=0, reverse_input=False, reverse_output=False))
		if conn.ReceiveKey(b'\x81\x42\xAA') == b'\x81':
			for i in range(0,len(data),256):
				block = data[i:i+256]
				repeats = 0
				while repeats < 4:
					#print('Block: ',i//256,' length ',''.join(format(x,'02x') for x in len(block).to_bytes(2,'big')))
					conn.Sendallbin(len(block).to_bytes(2,'big')) # Endianess switched around because the terminal stores it back to forth
					#print('CRC ',''.join(format(x,'02x') for x in b_crc.checksum(block).to_bytes(2,'big')))
					conn.Sendallbin(b_crc.checksum(block).to_bytes(2,'big')) # Endianess switched around because the terminal stores it back to forth
					conn.Sendallbin(block)
					rpl = conn.ReceiveKey(b'\x81\x42\xAA')
					if  rpl == b'\x81':
						#print('OK')
						break   # Block OK get next block
					elif rpl == b'\xAA':
						#print('RETRY')
						repeats += 1    # Block error, resend
					else:
						#print('ABORT')
						repeats = 5     # Disk error/User abort

				if repeats >= 4:
					conn.Sendallbin(b'\x00\x00\x00\x00')    # Zero length block ends transfer
					#print('ABORTED!')
					break
		else:
			repeats = 5
		conn.Sendallbin(b'\x00\x00\x00\x00\x00\x00')    # Make sure terminal exits transfer mode. Zero length block ends transfer + NULL name + Sequential file
		if repeats < 4:
			_LOG('TransferFile: Transfer complete',id=conn.id,v=3)
		elif repeats == 4:
			_LOG('TransferFile: Transfer aborted, too many errors',id=conn.id,v=2)
		else:
			_LOG('TransferFile: Client aborted the transfer',id=conn.id,v=2)
		return repeats < 4
	else:
		_LOG("TransferFile: Client doesn't suppport File Transfer command", id = conn.id, v=2)
		return False

###################################################################################################
# Generic file dialog
###################################################################################################
# conn: Connection
# filename: File basename
# size:	File size, 0 to ignore
# filetype: File type, shown as title, if none, filename is used as title
# prompt: <return> option prompt text
# save: Show save option
###################################################################################################
# Returns: 	0: Cancel
#			1: <RETURN> option
#			2: <S>ave option
###################################################################################################
def FileDialog(conn:Connection,filename:str,size=0,filetype=None,prompt='transfer to memory',save=False):
	S.RenderDialog(conn,5+(size!=0)+(filetype!=None)+save,(filename if filetype == None else filetype))
	conn.Sendall(TT.set_CRSR(0,2))
	keys = b'_\r'
	if filetype != None:
		conn.Sendall(chr(P.RVS_ON)+' fILE: '+H.crop(P.toPETSCII(filename),32)+'\r')
	if size > 0:
		conn.Sendall(chr(P.RVS_ON)+' sIZE: '+str(size)+'\r\r')
	else:
		conn.Sendall('\r')
	if save:
		conn.Sendall(chr(P.RVS_ON)+' pRESS <s> TO SAVE TO DISK, OR\r'+chr(P.RVS_ON))
		keys += b'S'
	else:
		conn.Sendall(chr(P.RVS_ON)+' pRESS')
	conn.Sendall(' <return> TO '+P.toPETSCII(prompt)[:26]+'\r')
	conn.Sendall(chr(P.RVS_ON)+' <_> to cancel')

	rc = conn.ReceiveKey(keys)
	return keys.index(rc)

#########################################################
# Sends a file directly without processing
#########################################################
#conn: Connection to send the file to
#filename: name+path of the file to be sent
#wait: boolean, wait for RETURN after sending the file
#########################################################
def SendRAWFile(conn:Connection,filename, wait=True):
    _LOG('Sending RAW file: ', filename, id=conn.id,v=3)

    archivo=open(filename,"rb")
    binario=archivo.read()
    conn.Sendallbin(binario)

    # Wait for the user to press RETURN
    if wait == True:
        conn.ReceiveKey()


##############################################################
# Sends a text or sequential file
##############################################################
def SendText(conn:Connection, filename, title='', lines=25):
    colors = (P.BLACK,P.WHITE,P.RED,P.PURPLE,P.CYAN,P.GREEN,P.BLUE,P.YELLOW,P.BROWN,P.PINK,P.ORANGE,P.GREY1,P.GREY2,P.LT_BLUE,P.LT_GREEN,P.GREY3)
    if title != '':
        S.RenderMenuTitle(conn, title)
        l = 22
        conn.Sendall(TT.set_Window(3,24))
    else:
        l = lines
        conn.Sendall(chr(P.CLEAR))

    if filename.endswith(('.txt','.TXT')):
        #Convert plain text to PETSCII and display with More
        tf = open(filename,"r")
        ot = tf.read()
        tf.close()
        text = H.formatX(ot)

        H.More(conn,text,l)

    elif filename.endswith(('.seq','.SEQ')):
        prompt='RETURN'
        tf = open(filename,"rb")
        text = tf.read()
        cc=0
        ll=0
        page = 0
        rvs = ''
        color = ''
        for c in text:
            char = c.to_bytes(1,'big')
            conn.Sendallbin(char)
            #Keep track of cursor position
            if char[0] in itertools.chain(range(32,128),range(160,256)): #Printable chars
                cc += 1
            elif char[0] == P.CRSR_RIGHT:
                cc += 1
            elif char[0] == P.CRSR_LEFT or char == P.DELETE:
                cc -= 1
            elif char[0] == P.CRSR_UP:
                ll -= 1
            elif char[0] == P.CRSR_DOWN:
                ll += 1
            elif char == b'\x0d':
                ll += 1
                cc = 0
                rvs = ''
            elif char[0] == P.HOME or char[0] == P.CLEAR:
                ll = 0
                page = 0
                cc = 0
            elif char[0] in colors:
                color = chr(char[0])
            elif char[0] == P.RVS_ON:
                rvs = chr(P.RVS_ON)
            elif char[0] == P.RVS_OFF:
                rvs = ''
            elif char[0] == P.TOLOWER:
                prompt = 'RETURN'
            elif char[0] == P.TOUPPER:
                prompt = 'return'
            if cc == 40:
                cc = 0
                ll += 1
            elif cc < 0:
                if ll!=l*page:
                    cc = 39
                    ll -= 1
                else:
                    cc = 0
            if ll < l*page:
                ll = l*page
            elif ll >= (l*page)+(l-1):
                if cc !=0:
                    conn.Sendall('\r')
                conn.Sendall(S.KeyPrompt(prompt+' OR _'))
                k = conn.ReceiveKey(b'\r_')
                if conn.connected == False:
                    conn.Sendall(TT.set_Window(0,24))
                    return -1
                if k == b'_':
                    conn.Sendall(TT.set_Window(0,24))
                    return -1
                conn.Sendall(chr(P.DELETE)*13+rvs+color+TT.set_CRSR(cc,(22-l)+ll-(l*page)))
                page += 1
        if cc !=0:
            conn.Sendall('\r')
        conn.Sendall(S.KeyPrompt(prompt))
        conn.ReceiveKey()

    if lines == 25:
        conn.Sendall(TT.set_Window(0,24))
    return -1

###########################################################
# Send C formatted C64 screens
########################################################### 
def SendCPetscii(conn:Connection,filename,pause=0):
    print("<<<<<<<<<<<<<<")
    try:
        fi = open(filename,'r')
    except:
        return()
    text = fi.read()
    fi.close
    #### Falta fijarse si es upper o lower
    if text.find('upper') != -1:
        cs = P.TOUPPER
    else:
        cs = P.TOLOWER
    frames = text.split('unsigned char frame')
    print(frames)
    for f in frames:
        if f == '':
            continue
        binary = b''
        fr = re.sub('(?:[0-9]{4})*\[\]={// border,bg,chars,colors\n','',f)
        fl = fr.split('\n')
        scc = fl[0].split(',')
        bo = int(scc[0]).to_bytes(1,'big') #border
        bg = int(scc[1]).to_bytes(1,'big') #background
        binary += b'\xff\xb2\x00\x90\x00'+bo+bg+b'\x81\x00\x82\xe8\x03'
        i = 0
        for line in fl[1:26]:
            for c in line.split(','):	#Screen codes
                if c.isnumeric():
                    binary += int(c).to_bytes(1,'big')
                    i += 1
        print(i)
        binary+= b'\x81\x20\x82\xe8\x03'
        i = 0
        for line in fl[26:52]:
            for c in line.split(','):	#Color RAM
                if c.isnumeric():
                    binary += int(c).to_bytes(1,'big')
                    i+=1
        print(i)
        binary+= b'\xfe'
        conn.Sendallbin(binary)
        conn.Sendall(chr(cs))
        if pause > 0:
            time.sleep(pause)
        else:
            conn.ReceiveKey()
    conn.Sendall(TT.enable_CRSR())
    return -1

##############################################
# Send .PET formatted C64 screens
##############################################
def SendPETPetscii(conn:Connection,filename):
    try:
        f = open(filename,'rb')
    except:
        return -1
    pet = f.read()
    bo = pet[2].to_bytes(1,'big')
    bg = pet[3].to_bytes(1,'big')
    binary = b'\xff\xb2\x00\x90\x00'+bo+bg+b'\x81\x00\x82\xe8\x03'
    binary += pet[5:1005]
    binary += b'\x81\x20\x82\xe8\x03'
    binary += pet[1005:]
    binary += b'\xfe'
    conn.Sendallbin(binary)
    if pet[4] == 1:
        conn.Sendall(chr(P.TOUPPER))
    else:
        conn.Sendall(chr(P.TOLOWER))
    #time.sleep(5)
    return 0