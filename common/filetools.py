###################################
#       File transfer tools       #
###################################

import re
import os
import time
from common.connection import Connection
from common import helpers as H
from common import audio as AA
from PIL import Image
from common.imgcvt import convert_To, gfxmodes, ColorProcess
from io import BytesIO
from common import turbo56k as TT
from common import style as S
from common.bbsdebug import _LOG, bcolors
from crc import Calculator, Configuration

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
	keys= b'\r'
	tml = ''
	if width != 0:
		tml += f'''<RVSON> Original size: {width}x{height}<BR><BR>
<RVSON> Select:<BR><BR><RVSON> * &lt; M &gt; form multicolor conversion<BR>
<RVSON>   &lt; H &gt; for hi-res conversion<BR>'''
		keys += b'HM'
	if save:
		tml += '<BR><RVSON> &lt; S &gt; to save image<BR>'
		keys += b'S'
	tml += '<RVSON> &lt; RETURN &gt; to view image<BR><CURSOR enable=False>'
	conn.SendTML(tml)
	out = 1
	while conn.connected:
		k = conn.ReceiveKey(keys)
		if k == b'H' and out == 1:
			conn.SendTML('<RVSON><AT x=1 y=5> <CRSRD><CRSRL>*')
			out = 0
		elif k == b'M' and out == 0:
			conn.SendTML('<RVSON><AT x=1 y=6> <CRSRU><CRSRL>*')
			out = 1
		elif k == b'S':
			out |= 0x80
			break
		elif k == b'\r':
			break
	conn.SendTML('<RVSON><CURSOR>')
	return out

###########################################################
# Send bitmap image
###########################################################
# conn: Connection to send the image/dialog to
# filename: file name or image object
# lines: Number of "text" lines to send, from the top
# display: Display the image after transfer
# dialog: Show convert options dialog before file transfer
# gfxmode: Graphic mode
# preproc: Preprocess image before converting
###########################################################
def SendBitmap(conn:Connection, filename, dialog = False, save = False, lines = 25, display = True,  gfxmode:gfxmodes = gfxmodes.C64MULTI, preproc:ColorProcess = None):

	ftype = {'.OCP':1,	#Advanced Art Studio
			'.KOA':2,'.KLA':2,	#Koala Paint
			'.ART':3,	#Art Studio
			'.DD':4,'.DDL':4,	#Doodle
			'.GIF':5,
			'.PNG':6,
			'.JPG':7}

	ftitle = {6:' GIF  Image ', 7:' PNG  Image ', 8:' JPEG Image '}

	fok = '<CLR><LOWER><GREEN>File transfer successful!<BR>'
	fabort = '<CLR><LOWER><ORANGE> File transfer aborted!<BR>'

	# Find image format
	data = [None]*3
	bgcolor = chr(0)

	mode = 1 if gfxmode == gfxmodes.C64MULTI else 0

	save &= conn.QueryFeature(TT.FILETR) < 0x80

	if type(filename)==str:
		extension = os.path.splitext(filename)[1]
		switch = ftype[extension.upper()]
	else:
		switch = 5

	if switch == 1:		#extension == '.ocp' or extension == '.OCP':
		if dialog and save:
			out = ImageDialog(conn,'Advanced Art Studio',0,0,True)
		else:
			out = 0
		if (out & 0x80) == 0x80:	# Save image
			savename = os.path.splitext(os.path.basename(filename))[0].upper()
			savename = savename.translate({ord(i): None for i in ':#$*?'})	#Remove CBMDOS reserved characters
			savename = (savename.ljust(12,' ') if len(savename)<12 else savename[:12])+'MPIC'
			if TransferFile(conn, filename, savename):
				conn.SendTML(fok)
			else:
				conn.SendTML(fabort)
			conn.SendTML('<KPROMPT t=RETURN>')
			return
		else:
			# Open Advanced Art Studio image file
			archivo=open(filename,"rb")
			# Discard the first couple of bytes
			archivo.read(2)

			# Bitmap data
			data[0] = archivo.read(8000)
			# Screen data
			data[1] = archivo.read(1000)
			# Read border color
			border = archivo.read(1)
			# Read background color
			bgcolor = archivo.read(1)
			# Skip the next 14 bytes
			archivo.read(14)
			# Color data
			data[2] = archivo.read(1000)

			archivo.close()
			gfxmode = gfxmodes.C64MULTI #Multicolor bitmap

	elif switch == 2:	#extension == '.koa' or extension == '.KOA' or extension == '.kla' or extension == '.KLA':
		if dialog and save:
			out = ImageDialog(conn,'Koala Paint',0,0,True)
		else:
			out = 0
		if (out & 0x80) == 0x80:	# Save image
			savename = os.path.splitext(os.path.basename(filename))[0].upper()
			savename = savename.translate({ord(i): None for i in ':#$*?'})	#Remove CBMDOS reserved characters
			savename = chr(0x81)+'PIC A '+(savename.ljust(8,' ') if len(savename)<8 else savename[:8])
			if TransferFile(conn, filename, savename):
				conn.SendTML(fok)
			else:
				conn.SendTML(fabort)
			conn.SendTML('<KPROMPT t=RETURN>')
			return
		else:
			# Open the Koala Paint image file
			archivo=open(filename,"rb")
			# Skip the first couple of bytes
			archivo.read(2)

			# Bitmap data
			data[0] = archivo.read(8000)
			# Screen data
			data[1] = archivo.read(1000)
			# Color data
			data[2] = archivo.read(1000)
			# Read background color
			bgcolor = archivo.read(1)
			border = bgcolor

			# Close the file
			archivo.close()
			gfxmode = gfxmodes.C64MULTI #Multicolor bitmap

	elif switch == 3:	#extension == '.art' or extension == '.ART':
		if dialog and save:
			out = ImageDialog(conn,'Art Studio',0,0,True)
		else:
			out = 0
		if (out & 0x80) == 0x80:	# Save image
			savename = os.path.splitext(os.path.basename(filename))[0].upper()
			savename = savename.translate({ord(i): None for i in ':#$*?'})	#Remove CBMDOS reserved characters
			savename = (savename.ljust(13,' ') if len(savename)<13 else savename[:13])+'PIC'
			if TransferFile(conn, filename, savename):
				conn.SendTML(fok)
			else:
				conn.SendTML(fabort)
			conn.SendTML('<KPROMPT t=RETURN>')
			return
		else:		# Open the Art Studio image file
			archivo=open(filename,"rb")
			# Skip the first couple of bytes
			archivo.read(2)

			# Bitmap data
			data[0] = archivo.read(8000)
			# Screen data
			data[1] = archivo.read(1000)
			# Read border color
			border = archivo.read(1)

			# Close file
			archivo.close()
			gfxmode = gfxmodes.C64HI #Hi-res bitmaps
	elif switch == 4:
		if dialog and save:
			out = ImageDialog(conn,'Doodle',0,0,True)
		else:
			out = 0
		if (out & 0x80) == 0x80:	# Save image
			savename = os.path.splitext(os.path.basename(filename))[0].upper()
			savename = savename.translate({ord(i): None for i in ':#$*?'})	#Remove CBMDOS reserved characters
			savename = 'DD'+(savename if len(savename)<14 else savename[:14])
			if TransferFile(conn, filename, savename):
				conn.SendTML(fok)
			else:
				conn.SendTML(fabort)
			conn.SendTML('<KPROMPT t=RETURN>')
			return
		else:		# Open the Art Studio image file
			archivo=open(filename,"rb")
			# Skip the first couple of bytes
			archivo.read(2)

			# Screen data
			data[1] = archivo.read(1000)
			#Skip
			archivo.read(24)
			# Bitmap data
			data[0] = archivo.read(8000)

			border = b'\x0c'

			# Close file
			archivo.close()
			gfxmode = gfxmodes.C64HI #Hi-res bitmaps
	elif 5 <= switch <= 7:	#extension in ('.gif','.png','.jpg','.GIF','.PNG','.JPG'):
		# or bytes/image object sent as filename parameter
		conn.SendTML('<CBM-B><CRSRL>')
		# try:
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
			conn.SendTML('<CBM-B><CRSRL>')
		else:
			mode = 1 if gfxmode == gfxmodes.C64MULTI else 0
		gfxmode = gfxmodes.C64MULTI if (mode & 0x7f) == 1 else gfxmodes.C64HI
		cvimg,data,gcolors = convert_To(Source, gfxmode, preproc)
		Source.close()
		bgcolor = gcolors[0].to_bytes(1,'big')	#Convert[4].to_bytes(1,'little')
		border = bgcolor
		# except Exception as e:
		# 	print(e)
		# 	return()


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
		binaryout += data[0][0:tbytes] #Bitmap
		# Set the transfer pointer + $00 (screen memory)
		binaryout += b'\x81\x00'
		# Transfer screen block + Byte count (low, high)
		binaryout += b'\x82'
		binaryout += tchars.to_bytes(2,'little')	#Block size
		# Screen Data
		binaryout += data[1][0:tchars] #Screen

		if gfxmode == gfxmodes.C64MULTI:
			# Set the transfer pointer + $20 (color memory)
			binaryout += b'\x81\x20'
			# Transfer color block + Byte count (low, high)
			binaryout += b'\x82'	# Color data
			binaryout += tchars.to_bytes(2,'little')	#Block size
			binaryout += data[2][0:tchars] #ColorRAM
			if display:
				# Switch to multicolor mode + Page number: 0 (default) + Border color: border + Background color: bgcolor
				binaryout += b'\x92\x00'
				binaryout += border
				binaryout += bgcolor
		elif display:
			# Switch to hires mode + Page number: 0 (default) + Border color: border
			binaryout += b'\x91\x00'
			binaryout += border
		# Exit command mode
		binaryout += b'\xFE'
		if display:
			conn.Sendall(TT.disable_CRSR())	#Disable cursor blink
		conn.Sendallbin(binaryout)
		return bgcolor
	else:	# Save to file
		savename = os.path.splitext(os.path.basename(filename))[0].upper()
		savename = savename.translate({ord(i): None for i in ':#$*?'})	#Remove CBMDOS reserved characters
		if gfxmode == gfxmodes.C64MULTI:
			binaryout = b'\x00\x20' # Advanced Art Studio Load address
			binaryout += data[0][0:tbytes] #Bitmap
			binaryout += data[1][0:tchars] #Screen
			binaryout += border
			binaryout += bgcolor
			binaryout += b'\x00'*14
			binaryout += data[2][0:tchars] #ColorRAM
			savename = (savename.ljust(12,' ') if len(savename)<12 else savename[:12])+'MPIC'
		else:
			binaryout = b'\x00\x20' # Art Studio Load address
			binaryout += data[0][0:tbytes] #Bitmap
			binaryout += data[1][0:tchars] #Screen
			binaryout += border
			savename = (savename.ljust(13,' ') if len(savename)<13 else savename[:13])+'PIC'
		if TransferFile(conn, binaryout, savename):
			conn.SendTML(fok)
		else:
			conn.SendTML(fabort)
		conn.SendTML('<KPROMPT t=RETURN>')
		return

#####################################################################################
# Sends a file to the client, calls the adequate function according to the filetype
#####################################################################################
# conn: Connection
# filename: path to the file to transfer
# dialog: Show dialog before transfer
# save: Allow file downloading to disk
###########################################
def SendFile(conn:Connection,filename, dialog = False, save = False):
	fok = '<CLR><LOWER><GREEN>File transfer successful!<BR>'
	fabort = '<CLR><LOWER><ORANGE> File transfer aborted!<BR>'
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
				savename = os.path.splitext(os.path.basename(filename))[0].upper()
				savename = savename.translate({ord(i): None for i in ':#$*?'})	#Remove CBMDOS reserved characters
				if TransferFile(conn,filename, savename[:16]):
					conn.SendTML(fok)
				else:
					conn.SendTML(fabort)
				conn.SendTML('<KPROMPT t=RETURN>')
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
				if ext == '.TXT':
					if len(os.path.basename(filename)) > 16:
						fn = os.path.splitext(os.path.basename(filename))
						savename = (fn[0][:16-len(fn[1])]+fn[1]).upper()
					else:
						savename = os.path.basename(filename).upper()
				else:
					savename = os.path.splitext(os.path.basename(filename))[0].upper()
				savename = savename.translate({ord(i): None for i in ':#$*?'})	#Remove CBMDOS reserved characters
				if TransferFile(conn,filename, savename[:16],True):
					conn.SendTML(fok)
				else:
					conn.SendTML(fabort)
				conn.SendTML('<KPROMPT t=RETURN>')
				conn.ReceiveKey()
			return
		elif ext in ['.JPG','.GIF','.PNG','.OCP','.KOA','.KLA','.ART','.DD','.DDL']:
			SendBitmap(conn,filename,dialog,save)
			conn.SendTML('<INKEYS><CURSOR>')
		elif ext == '.C':
			...
		elif ext == '.PET':
			...
		elif ext in ['.MP3','.WAV'] and not save:
			AA.PlayAudio(conn,filename,None,dialog)
		elif ext == '.TML':     #TML script
			with open(filename,'r') as slide:
				tml = slide.read()
				conn.SendTML(tml)
		elif save:	#Default -> download to disk
			if dialog:
				res = FileDialog(conn,os.path.basename(filename), os.path.getsize(filename), 'Download file to disk', prompt='save to disk', save = False)
			else:
				res = 1
			if res == 1:
				if len(os.path.basename(filename)) > 16:
					fn = os.path.splitext(os.path.basename(filename))
					savename = (fn[0][:16-len(fn[1])]+fn[1]).upper()
				else:
					savename = os.path.basename(filename).upper()
				savename = savename.translate({ord(i): None for i in ':#$*?'})	#Remove CBMDOS reserved characters
				if TransferFile(conn,filename,savename[:16]):
					conn.SendTML(fok)
				else:
					conn.SendTML(fabort)
				conn.SendTML('<KPROMPT t=RETURN>')
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
        staddr = binario[0]+(binario[1]*256)
        # Sync
        binaryout = b'\x00'
        # Enter command mode
        binaryout += b'\xFF'

        # Set the transfer pointer + load address (low:high)
        filesize = os.path.getsize(filename) - 2
        endaddr = staddr + filesize
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
        conn.SendTML(   f'<CLR><RVSOFF><ORANGE>Program file transferred to ${staddr:0{4}x}-${endaddr:0{4}x}<BR>'
		                f'To execute this program, <YELLOW><RVSON>L<RVSOFF><ORANGE>og off from<BR>'
                        f'this BBS, and exit Retroterm with <BR>RUN/STOP.<BR>'
			            f'Then use RUN or the correct SYS.<BR>'
			            f'Or <YELLOW><RVSON>C<RVSOFF><ORANGE>ontinue your session')
        if conn.ReceiveKey(b'CL') == b'L':
            conn.connected = False

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
					conn.Sendallbin(len(block).to_bytes(2,'big')) # Endianess switched around because the terminal stores it back to forth
					conn.Sendallbin(b_crc.checksum(block).to_bytes(2,'big')) # Endianess switched around because the terminal stores it back to forth
					conn.Sendallbin(block)
					rpl = conn.ReceiveKey(b'\x81\x42\xAA')
					if  rpl == b'\x81':
						break   # Block OK get next block
					elif rpl == b'\xAA':
						repeats += 1    # Block error, resend
						_LOG('File download-Block CRC error',id=conn.id,v=3)
					else:
						_LOG('File download canceled',id=conn.id,v=3)
						repeats = 5     # Disk error/User abort

				if repeats >= 4:
					conn.Sendallbin(b'\x00\x00\x00\x00')    # Zero length block ends transfer
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
	tml = '<AT x=0 y=2>'
	keys = b'_\r'
	if filetype != None:
		tml += f'<RVSON> File: {H.crop(filename,32)}<BR>'
	if size > 0:
		tml += f'<RVSON> Size: {size}<BR><BR>'
	else:
		tml += '<BR>'
	if save:
		tml += '<RVSON> Press &lt;S&gt; to save to disk, or<BR><RVSON>'
		keys += b'S'
	else:
		tml += '<RVSON> Press'
	tml += f' &lt;RETURN&gt; to {prompt[:26]}<BR><RVSON> &lt;<LARROW>&gt; to cancel'
	conn.SendTML(tml)
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

    with open(filename,'rb') as rf:
        binary=rf.read()
        conn.Sendallbin(binary)

    # Wait for the user to press RETURN
    if wait == True:
        conn.ReceiveKey()


##############################################################
# Sends a text or sequential file
##############################################################
def SendText(conn:Connection, filename, title='', lines=25):
    if title != '':
        S.RenderMenuTitle(conn, title)
        l = 22
        conn.Sendall(TT.set_Window(3,24))
    else:
        l = lines
        conn.SendTML('<CLR>')

    if filename.endswith(('.txt','.TXT')):
        #Convert plain text to PETSCII and display with More
        with open(filename,"r") as tf:
            ot = tf.read()
        text = H.formatX(ot)
    elif filename.endswith(('.seq','.SEQ')):
        # prompt='RETURN'
        with open(filename,"rb") as tf:
            ot = tf.read()
        tf.close()
        text = ot.decode('latin1')
    H.More(conn,text,l)

    if lines == 25:
        conn.Sendall(TT.set_Window(0,24))
    return -1

###########################################################
# Send C formatted C64 screens
########################################################### 
def SendCPetscii(conn:Connection,filename,pause=0):
    try:
        fi = open(filename,'r')
    except:
        return()
    text = fi.read()
    fi.close
    if text.find('upper') != -1:
        cs = '<UPPER>'
    else:
        cs = '<LOWER>'
    frames = text.split('unsigned char frame')
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
        binary+= b'\x81\x20\x82\xe8\x03'
        i = 0
        for line in fl[26:52]:
            for c in line.split(','):	#Color RAM
                if c.isnumeric():
                    binary += int(c).to_bytes(1,'big')
                    i+=1
        binary+= b'\xfe'
        conn.Sendallbin(binary)
        conn.SendTML(cs)
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
        conn.SendTML('<UPPER>')
    else:
        conn.SendTML('<LOWER>')
    return 0

################################################################
# TML tags
t_mono = {	'SENDRAW':(lambda c,file:SendRAWFile(c,file,False),[('c','_C'),('file','')]),
	        'SENDFILE':(lambda c,file,dialog,save:SendFile(c,file,dialog,save),[('c','_C'),('file',''),('dialog',False),('save',False)])}
