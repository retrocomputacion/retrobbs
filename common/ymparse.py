##############################
# YM2149 filetypes parser
# Support .YM .VTX and .VGZ
##############################

import lhafile
import gzip
from io import BytesIO
from common.bbsdebug import _LOG


#YM formats magic strings
magicYM = [b'YM2!',b'YM3!',b'YM3b',b'YM4!',b'YM5!',b'YM6!']
#VTX format magic strings
magicVTX = [b'ym',b'ay']

#YM frequency -> platform dict
platform = {2000000:' - Atari', 1000000:' - Amstrad'}

def bcd_decode(data: bytes, decimals: int):
    '''
    Decode BCD number
    https://stackoverflow.com/questions/11668969/python-how-to-decode-binary-coded-decimal-bcd
    '''
    res = 0
    for n, b in enumerate(data):	#reversed(data) for big endian
        res += (b & 0x0F) * 10 ** (n * 2 - decimals)
        res += (b >> 4) * 10 ** (n * 2 + 1 - decimals)
    return res

# Open file, returns data
# Depack file if its lha packed
def YMOpen(filename:str):

	#Try for unpacked file first
	try:
		data = None
		with open(filename,'rb') as ymf:
			data = ymf.read()
		if data[0:4] in magicYM:
			return data
	except:
		_LOG('YMOpen: File not found')
		return None
	#Try for lha packed file
	if lhafile.is_lhafile(filename):
		try:
			ymf = lhafile.Lhafile(filename)
			data = ymf.read(ymf.infolist()[0].filename)
			if data[0:4] in magicYM:
				return data
		except Exception as e:
			pass
	else:
		#Try for VTX file
		try:
			data = None
			with open(filename,'rb') as ymf:
				data = ymf.read()
				offset = 16
				for i in range(5):	#skip header
					while data[offset] != 0:
						offset += 1
					offset += 1
				xhdr = data[:offset]	#VTX header
				xlha = data[offset:]	#VTX compressed data
				lhah =	b'-lh5-'+len(xlha).to_bytes(4,'little')+data[12:16]+	\
						b'\x00\x08\x4C\x14\x00\x00\x0AYM_0001.YM'+ lhafile.crc16(xlha).to_bytes(2,'little')	#<<< file crc
				lhah = bytes(chr(len(lhah)),'latin1')+bytes(chr(sum(lhah)&255),'latin1')+lhah + xlha + b'\x00'
				lf = lhafile.Lhafile(BytesIO(lhah))
				info = lf.NameToInfo[lf.infolist()[0].filename]
				# Using lf.read() fails because we're missing the original CRC
				fin = BytesIO(xlha+b'\x00')
				fout = BytesIO()
				session = lhafile.lzhlib.LZHDecodeSession(fin,fout,info)
				while not session.do_next():
					pass
				fout.seek(0)
				data = xhdr + fout.read()
			return data
		except Exception as e:
			pass
		#Try for Gzipped VGM file
		try:
			with gzip.open(filename, 'rb') as vgf:
				data = vgf.read()
			if data[:4] == b'Vgm ':
				return data
		except:
			pass

	_LOG('YMOpen: Unsupported file format',v=2)
	return None

# Get metadata if there's any
def YMGetMeta(data):
	if data != None:
		out = {'clock':2000000, 'interleave':True, 'frames':0, 'offset':4, 'title':'???', 'artist':'???','comments':'','copyright':'???', 'rate':50, 'type':'YM', 'subsongs':1, 'startsong':1}
		if data[0:4] in magicYM:
			version = magicYM.index(data[0:4])
		elif data[0:2] in magicVTX:
			version = 6
		elif data[0:4] == b'Vgm ':
			version = 7
		else:
			version = 10
		# Read header if needed
		if version < 2: #YM2 YM3
			out['frames'] = int((len(data)-4)/14)
			out['offset'] = 4
		elif version == 2: #YM3b
			out['frames'] = int((len(data)-8)/14)
			out['offset'] = 4
		elif (version < 6) and (data[4:12] == b'LeOnArD!'):   #YM4 YM5 YM6
			out['frames'] = int.from_bytes(data[12:16],'big')	#(data[12]*16777216)+(data[13]*65526)+(data[14]*256)+data[15]
			out['interleave'] = (data[19]&1)==1
			ddrums = int.from_bytes(data[20:22],'big')	#(data[20]*256)+data[21]
			if version == 3:    #YM4
				offset = 28
			else:	#YM5 YM6
				offset = 34
				out['rate'] = int.from_bytes(data[26:28],'big')		#(data[26]*256)+data[27]
			out['clock'] = int.from_bytes(data[22:26],'big')	#(data[22]*16777216)+(data[23]*65526)+(data[24]*256)+data[25]
			for x in range(ddrums):	#Iterate digidrums to get register data offset
				offset += int.from_bytes(data[offset:offset+4],'big')+4		#(data[offset]*16777216)+(data[offset+1]*65536)+(data[offset+2]*256)+data[offset+3]+4
			tmp = ''
			while data[offset] != 0:
				tmp += chr(data[offset])
				offset += 1
			offset += 1
			out['name'] = tmp
			tmp = ''
			while data[offset] != 0:
				tmp += chr(data[offset])
				offset += 1
			offset += 1
			out['artist'] = tmp
			tmp = ''
			while data[offset] != 0:
				tmp += chr(data[offset])
				offset += 1
			offset += 1
			out['comments'] = tmp
			out['offset'] = offset
		elif version == 6:	#VTX
			offset = 16
			tmp = ['']*5
			for i in range(5):	#skip header
				while data[offset] != 0:
					tmp[i] += chr(data[offset])
					offset += 1
				offset += 1
			out['title'] = tmp[0]
			out['artist'] = tmp[1]
			out['comments'] =  tmp[4]
			out['copyright'] = str(int.from_bytes(data[10:12],'little'))	#(data[11]*256)+data[10]
			out['frames'] = int((len(data)-offset)/14)
			out['clock'] = int.from_bytes(data[5:9],'little')	#(data[8]*16777216)+(data[7]*65526)+(data[6]*256)+data[5]
			out['rate'] = data[9]
			out['offset'] = offset
		elif version == 7:	#VGM
			out['rate'] = int.from_bytes(data[0x24:0x28],'little')
			out['clock'] = int.from_bytes(data[0x74:0x78],'little')
			if out['clock'] == 0:
				return None	# VGM file doesnt use the AY3-8910
			gd3offset = int.from_bytes(data[0x14:0x18],'little')+0x14
			if gd3offset != 0:
				...
				strings = []
				i = 12
				for x in range(11):
					tmp = ''
					while data[gd3offset+i:gd3offset+i+2] != b'\x00\x00':
						tmp += data[gd3offset+i:gd3offset+i+2].decode('utf-16le')
						i += 2
					i += 2
					strings.append(tmp)
				out['title'] = strings[0]
				out['artist'] = strings[6]
				out['copyright'] = strings[8][:4] if strings[8] != '' else '???'
				if out['rate'] == 0:
					if strings[4]in ['MSX','MSX2','Sharp X1 Turbo','Apple II']:
						out['rate'] = 60
					else:
						out['rate'] = 50
				out['frames'] = int.from_bytes(data[0x18:0x1c],'little')/(44100/out['rate'])
			if bcd_decode(data[8:12],2) <= 1.5:	# File too old
				return None
			out['offset'] = int.from_bytes(data[0x34:0x38],'little')+0x34
			...
		else:
			_LOG('YMGetMeta: Invalid file')
			return None
		out['songlength'] = [round(out['frames']/out['rate'])]
		out['type'] += platform.get(out['clock'],'')
		return out
	else:
		return None

# Parse YM file, return list of frames with register values and Metadata
def YMDump(data):

	if (meta := YMGetMeta(data))!= None:
		if data[:4] == b'Vgm ':	#.VGM
			ix = meta['offset']
			if meta['rate'] == 0:
				meta['rate'] = 50
			# Based on vgmparser.py by Simon Morris
			count = 0
			frames = []
			regs = [0,0,0,0,0,0,0,0,0,0,0,0,0,0]
			samples = 0
			while ix < len(data):
				regs[13] = 0xff
				cmd = data[ix]
				dd = None
				# 0x4f dd - Game Gear PSG stereo, write dd to port 0x06
				# 0x50 dd - PSG (SN76489/SN76496) write value dd
				if cmd in [0x4f,0x50]:
					dd = data[ix+1]
					ix += 2
				# 0x51 -> 0x5f - Yamaha chips writes
				elif 0x51 <= cmd <= 0x5f:
					dd = data[ix+1:ix+2]
					ix +=3
				# 0x61 nn nn - Wait n samples, n can range from 0 to 65535
				elif cmd == 0x61:
					dd = int.from_bytes(data[ix+1:ix+3],'little')
					ix +=3
					samples += dd
				# 0x62 - Wait 735 samples (60th of a second)
				elif cmd == 0x62:
					ix += 1
					dd = None
					samples += 735
				# 0x63 - Wait 882 samples (50th of a second)
				# 0x66 - End of sound data
				elif cmd in [0x63,0x66]:
					ix +=1
					dd = None
					samples += 882
					if cmd == 0x66:
						break
				# 0x67 0x66 tt ss ss ss ss - Data block
				elif cmd == 0x67:
					dbsz = int.from_bytes(data[ix+2:ix+6],'little')
					dd = data[ix+6:ix+6+dbsz]	#Data block
					ix += 6+dbsz
				# 0x68 0x66 cc oo oo oo dd dd dd ss ss ss -  PCM RAM writes
				elif cmd == 0x68:
					dd = data[ix+2:ix+12]
					ix += 12
				# 0x7n - Wait n+1 samples, n can range from 0 to 15
				# 0x8n - YM2612 port 0 address 2A write from the data bank, then
				#        wait n samples; n can range from 0 to 15
				elif 0x70 <= cmd <= 0x8f:
					ix += 1
					dd = None
					samples += (cmd & 15)+(1 if cmd < 0x80 else 0)
				# 0x90 ss tt pp cc - Setup Stream Control
				# 0x91 ss dd ll bb - Set Stream Data
				# 0x95 ss bb bb ff - Start Stream (fast call)
				elif cmd in [0x90,0x91,0x95]:
					dd = data[ix+1:ix+5]
					ix += 5
				# 0x92 ss ff ff ff ff - Set Stream Frequency
				elif cmd == 0x92:
					dd = data[ix+1:ix+6]
					ix += 6
				# 0x93 ss aa aa aa aa mm ll ll ll ll - Start Stream
				elif cmd == 0x93:
					dd = data[ix+1:ix+11]
					ix += 11
				# 0x94 ss - Stop Stream
				elif cmd == 0x94:
					dd = data[ix+1]	
					ix += 2
				# ------------------------------------------
				# 0xa0 - AY-3-8910 write
				elif cmd == 0xa0:
					dd = data[ix+1:ix+3]
					regs[data[ix+1]&15] = data[ix+2]
					ix += 3					
				#-------------------------------------------
				# 0xa1 -> 0xbf - 2 byte chip writes
				elif 0xa1 <= cmd <= 0xbf:
					dd = data[ix+1:ix+3]
					ix += 3
				# 0xc0 -> 0xd6 - 3 byte chip writes
				elif 0xc0 <= cmd <= 0xd6:
					dd = data[ix+1:ix+4]
					ix += 4
				# 0xe0 dddddddd - Seek to offset dddddddd (Intel byte order) in PCM
				#                 data bank
				elif cmd == 0xe0:
					dd = data[ix+1:ix+5]
					ix += 5
				# 0x30 dd - dual chip command
				elif cmd == 0x30:
					dd = data[ix+1]
					ix += 2
				# 0x31 dd - AY-3-8910 stereo mask
				elif cmd == 0x31:
					dd = data[ix+1]
					ix += 2

				count +=1
				if samples >= (44100/meta['rate']):
					for i in range(round(samples/(44100/meta['rate']))):	#
						frames.append(regs.copy())
						regs[13] = 0xff
					samples = 0
			...
		else:					#.YM .VTX
			frcnt = meta['frames']
			ymclk = meta['clock']
			offset = meta['offset']
			frames = [[0]*14 for i in range(frcnt)]
			#Iterate frames
			if meta['interleave']:
				for reg in range(14):
					for f in range(frcnt):
						frames[f][reg] = data[f+(frcnt*reg)+offset]
			else:
				for f in range(frcnt):
					for reg in range(14):
						frames[f][reg] = data[(f*16)+reg+offset]
		return frames, meta
	else:
		return None, None