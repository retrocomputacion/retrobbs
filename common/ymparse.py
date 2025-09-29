##############################
# YM2149 filetypes parser
# Support .YM .VTX and .VGZ
##############################

import lhafile
import gzip
from io import BytesIO
import os
import sys
from common.bbsdebug import _LOG

#YM formats magic strings
magicYM = [b'YM2!',b'YM3!',b'YM3b',b'YM4!',b'YM5!',b'YM6!']
#VTX format magic strings
magicVTX = [b'ym',b'ay']

#YM frequency -> platform dict
platform = {2000000:' - Atari', 1000000:' - Amstrad'}

#############################################################################################
# Decode BCD number
# https://stackoverflow.com/questions/11668969/python-how-to-decode-binary-coded-decimal-bcd
#############################################################################################
def bcd_decode(data: bytes, decimals: int):
    res = 0
    for n, b in enumerate(data):	#reversed(data) for big endian
        res += (b & 0x0F) * 10 ** (n * 2 - decimals)
        res += (b >> 4) * 10 ** (n * 2 + 1 - decimals)
    return res

################################
# Open file, returns data
# Depack file if its lha packed
################################
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

##############################
# Get metadata if there's any
##############################
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

#########################################################################
# Dump YM file, return list of frames with register values and Metadata
#########################################################################
def YMDump(data):
    meta = YMGetMeta(data)
    if meta != None:
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
    
#####################################################################
# Parse a YM file register dump into a Retroterm compatible stream
# t_freq: target PSG frequency
#####################################################################
def YMParser(filename, t_freq=1789773):
    dump = None
    frame = None
    try:
        if type(filename) == str:
            data = YMOpen(filename)
            if data != None:
                frames,meta = YMDump(data)
                ymfreq = meta['clock']
        elif type(filename) == list:
            # data = filename
            frames = filename
            ymfreq = t_freq

        if frames != None:
            # frames,meta = YMDump(data)
            # ymfreq = meta['clock']
            # print(ymfreq)
            if frames != None:
                dump = []
                p_regs = [0,0,0,0,0,0,0,0,0,0,0,0,0,0]
                rcount = 16 # 14 registers + 2 bytes from the bitmap
                rbitmap = 0b0011111111111111
                psg_regs = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'          #Init PSG
                # print(f'Frame #\trcount\t BM\t Regs')
                # print(f'0\t16\t{rbitmap}\t{psg_regs}')
                dump.append([rcount.to_bytes(1,'little'),rbitmap.to_bytes(2,'big'),psg_regs])
                for fn,frame in enumerate(frames):
                    rbitmap = 0
                    rcount = 2
                    psg_regs = b''
                    if t_freq != ymfreq:
                        v1f = (frame[0] + (frame[1]*256))
                        if v1f > 0:
                            v1f = t_freq/(ymfreq/v1f)
                        v2f = (frame[2] + (frame[3]*256))
                        if v2f > 0:
                            v2f = t_freq/(ymfreq/v2f)
                        v3f = (frame[4] + (frame[5]*256))
                        if v3f > 0:
                            v3f = t_freq/(ymfreq/v3f)
                        if frame[6] > 0:
                            nof = t_freq/(ymfreq/frame[6])
                        else:
                            nof = 0
                        enf = (frame[11] + (frame[12]*256))
                        if enf > 0:
                            enf = t_freq/(ymfreq/enf)
                        v1f = int(v1f if v1f <= 4095 else 4095)
                        v2f = int(v2f if v2f <= 4095 else 4095)
                        v3f = int(v3f if v3f <= 4095 else 4095)
                        nof = int(nof if nof <= 31 else 31)
                        enf = int(enf if enf <= 65535 else 65535)
                        frame[0] = v1f & 0xff
                        frame[1] = v1f >> 8
                        frame[2] = v2f & 0xff
                        frame[3] = v2f >> 8
                        frame[4] = v3f & 0xff
                        frame[5] = v3f >> 8
                        frame[6] = nof
                        frame[11] = enf & 0xff
                        frame[12] = enf >> 8
                    for rn in range(14):
                        if rn == 13 and frame[rn]!=0xff:
                            rbitmap |= 1<<rn
                            psg_regs += frame[rn].to_bytes(1,'little')
                            rcount +=1
                        elif p_regs[rn] != frame[rn]:
                            rbitmap |= 1<<rn
                            tmp = frame[rn]
                            if rn == 7:
                                tmp = (tmp & 0x3F)|0x80
                            psg_regs += tmp.to_bytes(1,'little')    #frame[rn].to_bytes(1,'little')
                            rcount +=1
                    dump.append([rcount.to_bytes(1,'little'),rbitmap.to_bytes(2,'big'),psg_regs])
                    p_regs = frame
                    # print(f'{fn}\t{rcount}\t{rbitmap}\t{psg_regs}')

        else:
            _LOG('YMParser: Error opening file')
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        _LOG(f'YMParser error:{exc_type} on {fname} line {exc_tb.tb_lineno}')
    return(dump)

def SIDtoYM(filename, ptime, order = 0, subtune = 1, t_freq=1789773):

    def sid_freq(f):
        if f < 1:
            f = 1
        return float(f) * float(SID_CLOCK) / 16777216.0

    # try:
    data_out = []
    siddump = SID.SIDParser(filename, ptime, order, subtune)
    psize = 0       # packet size
    pbm = 0         # packet bitmap
    pregs = b''     # packet registers

    sid = SidState()
    sid_voice1 = sid.get_voice(0)
    sid_voice2 = sid.get_voice(1)
    sid_voice3 = sid.get_voice(2)

    psg_regs = [0,0,0,0,0,0,0,0,0,0,0,0,0,0]

    pgate = [0,0,0]

    for frame in siddump:
        psize = frame[0][0]
        if psize > 0:
            pbm = int.from_bytes(frame[1],'big')
            pregs = frame[2]
            reg = 0

            #Handle hard-restart
            # Gate restart
            if pbm & (1<<31) != 0:
                sid_voice3.set_control(pgate[2] & 0xFE)
                sid_voice3.tick(4)
            if pbm & (1<<30) != 0:
                sid_voice2.set_control(pgate[1] & 0xFE)
                sid_voice2.tick(4)
            if pbm & (1<<29) != 0:
                sid_voice1.set_control(pgate[0] & 0xFE)
                sid_voice1.tick(4)
            # ADSR restart
            if pbm & (1<<28) != 0:
                sid_voice3.set_ad(0)
                sid_voice3.set_sr(0)
                sid_voice3.tick(4)
                # print('RA3 ',end='')
            if pbm & (1<<27) != 0:
                sid_voice2.set_ad(0)
                sid_voice2.set_sr(0)
                sid_voice2.tick(4)
                # print('RA2 ',end='')
            if pbm & (1<<26) != 0:
                sid_voice1.set_ad(0)
                sid_voice1.set_sr(0)
                sid_voice1.tick(4)
                # print('RA1 ',end='')

            #unpack frame packets
            while len(pregs) > 0:
                for b in range(reg,26):
                    if pbm & (1 << b) != 0:
                        if b in [4,11,18]:
                            pgate[(b-4)//7] = pregs[0]  # save gate state
                            # print(f' ${pregs[0]:02x} ',end='')
                        sid.set_register(b,pregs[0])
                        pregs = pregs[1:]
                        reg = b + 1
                        break
                    # else:
                        # if b in [4,11,18]:
                        #     print(' --- ',end='')
            # print()
            vf = int(round(float(t_freq)/(sid_freq(sid_voice1.get_frequency())*16.0)))
            psg_regs[0] = vf & 0xff
            psg_regs[1] = (vf>>8) & 0xff

            vf = int(round(float(t_freq)/(sid_freq(sid_voice2.get_frequency())*16.0)))
            psg_regs[2] = vf & 0xff
            psg_regs[3] = (vf>>8) & 0xff

            vf = int(round(float(t_freq)/(sid_freq(sid_voice3.get_frequency())*16.0)))
            psg_regs[4] = vf & 0xff
            psg_regs[5] = (vf>>8) & 0xff

            sid_noise_active = int(sid_voice1.isNoise()+sid_voice2.isNoise()+sid_voice3.isNoise())

            if sid_noise_active > 0:
                sid_noise_avg = (((sid_freq(sid_voice1.get_frequency()) if sid_voice1.isNoise() else 0)
                                + (sid_freq(sid_voice2.get_frequency()) if sid_voice2.isNoise() else 0)
                                + (sid_freq(sid_voice3.get_frequency()) if sid_voice3.isNoise() else 0)) / sid_noise_active) * 16.0
                ym_noise = int(((t_freq) / sid_noise_avg) / 16.0)
                if ym_noise > 31:
                    ym_noise = 31
                psg_regs[6] = ym_noise

            ym_mixer = ((9 if sid_voice1.isMute() else (1 if sid_voice1.isNoise() else 8))
                        | (18 if sid_voice2.isMute() else (2 if sid_voice2.isNoise() else 16))
                        | (36 if sid_voice3.isMute() or sid.is3off() else (4 if sid_voice3.isNoise() else 32)))
            psg_regs[7] = ym_mixer

            psg_regs[8] = get_ym_volume(float((sid_voice1.get_envelope_level()*sid.get_master_volume())/15.0)/255.0)>>1
            psg_regs[9] = get_ym_volume(float((sid_voice2.get_envelope_level()*sid.get_master_volume())/15.0)/255.0)>>1
            psg_regs[10] = get_ym_volume(float((sid_voice3.get_envelope_level()*sid.get_master_volume())/15.0)/255.0)>>1

            # print(psg_regs[8:11])
            sid.tick(int(SID_CLOCK/50))
            data_out.append(psg_regs.copy())
        else:
            break
    # print()
    return YMParser(data_out,t_freq)
    # except Exception as e:
    #     exc_type, exc_obj, exc_tb = sys.exc_info()
    #     fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    #     _LOG(f'SIDtoYM error:{exc_type} on {fname} line {exc_tb.tb_lineno}')

    return []

####### ---- SNIP ---- #######
# Following code adapted from:

# sid2ym.py
# SID to .YM files (YM2149 sound chip) music file format conversion utility
#
# Copyright (c) 2019 Simon Morris. All rights reserved.
#
# "MIT License":
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the Software
# is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

SID_PAL_CLOCK = 985248 # 17734475 / 18

SID_CLOCK = SID_PAL_CLOCK # set to SID_NTSC_CLOCK or SID_PAL_CLOCK


# Taken from: https://github.com/true-grue/ayumi/blob/master/ayumi.c
# However, it doesn't marry with the YM2149 spec sheet, nor with the anecdotal reports that the YM attentuation steps in -1.5dB increments. Still, I'm gonna run with the emulator version.
ym_amplitude_table = [
    0.0, 0.0,
    0.00465400167849, 0.00772106507973,
    0.0109559777218, 0.0139620050355,
    0.0169985503929, 0.0200198367285,
    0.024368657969, 0.029694056611,
    0.0350652323186, 0.0403906309606,
    0.0485389486534, 0.0583352407111,
    0.0680552376593, 0.0777752346075,
    0.0925154497597, 0.111085679408,
    0.129747463188, 0.148485542077,
    0.17666895552, 0.211551079576,
    0.246387426566, 0.281101701381,
    0.333730067903, 0.400427252613,
    0.467383840696, 0.53443198291,
    0.635172045472, 0.75800717174,
    0.879926756695, 1.0 ]

# given an amplitude (0-1), return the closest matching YM 5-bit volume level
def get_ym_volume(a):
    if True:
        dist = 1<<31
        index = 0
        for n in range(32):
            ya = ym_amplitude_table[n]
            p = a - ya
            d = p * p
            # we always round to the nearest louder level (so we are never quieter than target level)
            if d < dist and ya >= a:
                dist = d
                index = n

        return index
    else:        
        if (a == 0.0):
            v = 0
        else:
            v = int( 31 - ( (10*math.log(a, 10)) / -0.75 ) )
        #print "  Volume of amplitude " + str(a) + " is " + str(v)
        #if v > 31:
        #    print "TITS"
        v = min(31, v)
        v = max(0, v)
        return v 


# Class to manage simulated state of a SID voice based on register settings
class SidVoice(object):

    # class statics

    # these tables are mappings of ADSR register values to ms/step
    attack_table = [ 2, 8, 16, 24, 38, 56, 68, 80, 100, 250, 500, 800, 1000, 3000, 5000, 8000 ]
    decayrelease_table = [ 6, 24, 48, 72, 114, 168, 204, 240, 300, 750, 1500, 2400, 3000, 9000, 15000, 24000 ]
    # sustain table maps S of the ADSR registers to a target 8-bit volume from a 4-bit setting
    sustain_table = [ 0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88, 0x99, 0xaa, 0xbb, 0xcc, 0xdd, 0xee, 0xff ]

    # Envelope cycles
    EnvelopeCycle_Inactive = 0
    EnvelopeCycle_Attack = 1
    EnvelopeCycle_Decay = 2
    EnvelopeCycle_Sustain = 3
    EnvelopeCycle_Release = 4

    def __init__(self, voiceid):
        self.__voiceid = voiceid
        self.reset()

    def reset(self):
        ### internals

        # oscillator - 24-bit phase accumulator
        self.__accumulator = 0

        # waveform output level - 12-bits
        self.__waveform_level = 0

        # envelope counter - 16-bit counter for envelope period
        self.__envelope_counter = 0

        # envelope level - 24-bit value where top 8-bits are the 0-255 output level
        self.__envelope_level = 0
        # envelope Cycle - 0=inactive, 1=attack, 2=decay, 3=sustain, 4=release
        self.__envelope_cycle = SidVoice.EnvelopeCycle_Inactive

        ### registers
        self.__gate = False
        self.set_frequency(0)
        self.set_pulsewidth(0)
        self.set_control(0)
        self.set_ad(0)
        self.set_sr(0)

    # registers 0,1 - frequency (16-bits)
    def set_frequency(self, f):
        self.__frequency = f


    def get_frequency(self):
        return self.__frequency

    # registers 2,3 - pulse width (12-bits)
    def set_pulsewidth(self, p):
        self.__pulsewidth = p

    def get_pulsewidth(self):
        return self.__pulsewidth

    def isNoise(self):
        return self.__noise == True

    def isPulse(self):
        return self.__pulse == True

    def isTriangle(self):
        return self.__triangle == True

    def isSaw(self):
        return self.__sawtooth == True

    def isTest(self):
        return self.__test == True

    def isSync(self):
        return self.__sync == True

    def isRingMod(self):
        return self.__ringmod == True

    def isMute(self):
        return self.__test or not self.__wave_active

    # TODO:
    # support mode & filter registers

    # register 4 - control (8-bits)
    def set_control(self, c):

        last_gate = self.__gate

        # waveform generators enable flags
        self.__noise = ((c & 128) == 128)
        self.__pulse = ((c & 64) == 64)
        self.__triangle = ((c & 32) == 32)
        self.__sawtooth = ((c & 16) == 16)
        # control flags
        self.__test = ((c & 8) == 8)
        self.__ringmod = ((c & 4) == 4)
        self.__sync = ((c & 2) == 2)
        self.__gate = ((c & 1) == 1)

        # logic indicator if a waveform is active on this voice
        self.__wave_active = self.__noise or self.__pulse or self.__triangle or self.__sawtooth


        # handle gate trigger state change
        if self.__gate != last_gate:

            if self.__gate:
                # gate on - attack cycle triggered
                # one decay cycle tick before starting attack cycle
                self.__envelope_cycle = SidVoice.EnvelopeCycle_Decay
                self.tick_envelope(1)
                self.__envelope_cycle = SidVoice.EnvelopeCycle_Attack
            else:
                # gate cleareroff - release cycle triggered
                self.__envelope_cycle = SidVoice.EnvelopeCycle_Release

    # register 5,6 - envelope (4x 4-bits)
    def set_ad(self, r1):
        self.__attack = (r1 >> 4) & 15
        self.__decay = (r1 & 15)

    def set_sr(self,r2):
        self.__sustain = (r2 >> 4) & 15
        self.__release = (r2 & 15)

    # get the current envelope level / amplitude for this voice (0-255)
    def get_envelope_level(self):
        return self.__envelope_level #(self.__envelope_level >> 16) & 255
        #if self.__noise:
        #    return 0
        if self.__test:
            if self.__envelope_level > 0:
                print("NOTE: TEST bit set overrode ADSR volume")
            return 0
        else:
            return self.__envelope_level #(self.__envelope_level >> 16) & 255

    def get_waveform_level(self):
        #if self.__noise:
        #    return 0
        if self.___test:
            return 0
        else:
            return self.__waveform_level

    # advance envelope clock where t is 1/SID_CLOCK
    # returns true if ADSR is active
    def tick_envelope(self, t):

        #----------------------------
        # envelope generation
        #----------------------------

        adsr_active = True

        # Some early out scenarios can be handled here
        # ADSR doesn't need always updating so that's work we can detect & skip 
        # if (self.__envelope_cycle == SidVoice.EnvelopeCycle_Sustain):
        #     # if we're in sustain cycle, its an early out because only Gate change will affect it
        #     # and that cannot happen within this logic
        #     # print(" - Optimized sustain for voice " + str(self.__voiceid))
        #     adsr_active = False
        if (self.__envelope_cycle == SidVoice.EnvelopeCycle_Inactive):
            # print(" - Optimized ADSR for voice " + str(self.__voiceid) + " because Inactive")
            adsr_active = False

        # early out if inactive
        if not adsr_active:
            return adsr_active
        


        # gate bit set to one triggers the ADSR cycle
        # attack phase rises from 0-255 at the ms rate specified by attack register
        # decay phase moves from 255 to the sustain register level
        # sustain level holds until gate bit is cleared
        # release phases moves from sustain level to 0 at the rate specified by release register
        # register can be changed during each phase, but only take effect if new value is possible depending on ramp up/ramp down mode
        # gate bit can be cleared at any time to trigger release phase, even if ads phase incomplete
        # if gate bit is set before release phase has completed, the envelope generator continues attack phase from current setting


        # envelope process
        # see also https://sourceforge.net/p/vice-emu/code/HEAD/tree/trunk/vice/src/resid/envelope.cc

        precision = (2 ** 31)
        attack_rate = int( round( precision / (SidVoice.attack_table[self.__attack] * SID_CLOCK / 1000)))
        decay_rate = int( round( precision / (SidVoice.decayrelease_table[self.__decay] * SID_CLOCK / 1000)))
        release_rate = int( round( precision / (SidVoice.decayrelease_table[self.__release] * SID_CLOCK / 1000)))
        sustain_target = SidVoice.sustain_table[self.__sustain] << 24


        # iterate the ADSR logic for each tick. Suboptimal for now.
        iteration_count = t
        iteration_scale = 1
        if (self.__envelope_cycle == SidVoice.EnvelopeCycle_Attack) and ((self.__envelope_counter + attack_rate*t) <= precision):
            iteration_scale = t
            iteration_count = 1
            # print(" - Optimized attack for voice " + str(self.__voiceid))
        elif (self.__envelope_cycle == SidVoice.EnvelopeCycle_Decay) and ((self.__envelope_counter - decay_rate*t) > sustain_target):
            iteration_scale = t
            iteration_count = 1
            # print(" - Optimized decay for voice " + str(self.__voiceid))
        elif (self.__envelope_cycle == SidVoice.EnvelopeCycle_Release) and ((self.__envelope_counter - release_rate*t) >= 0):
            iteration_scale = t
            iteration_count = 1
            # print(" - Optimized release for voice " + str(self.__voiceid))
        elif (self.__envelope_cycle == SidVoice.EnvelopeCycle_Sustain):
            # if we're in sustain cycle, its an early out because only Gate change will affect it
            iteration_count = 1
            adsr_active = False
            # print(" - Optimized sustain for voice " + str(self.__voiceid))
        elif (self.__envelope_cycle == SidVoice.EnvelopeCycle_Inactive):
            iteration_count = 1
            adsr_active = False
            # print(" - Optimized ADSR for voice " + str(self.__voiceid) + " because Inactive")
        # else:
        #     print(" - " + str(iteration_count) + " ADSR Iterations for voice " + str(self.__voiceid) + ", cycle=" + str(self.__envelope_cycle))

        #elif (self.__envelope_cycle == SidVoice.EnvelopeCycle_Decay) and ((self.__envelope_counter - decay_rate*t) > 0):
        #    t = 1

        for n in range(iteration_count):
            #print("Iteration count=" + str(iteration_count) + ", n=" + str(n) + ", " #" + str(n))
            if self.__envelope_cycle == SidVoice.EnvelopeCycle_Inactive:
                # nothing to do
                break
            # attack cycle
            elif self.__envelope_cycle == SidVoice.EnvelopeCycle_Attack:
                self.__envelope_counter += attack_rate * iteration_scale
                self.__envelope_level = self.__envelope_counter >> 24
                if self.__envelope_level >= 255:
                    self.__envelope_level = 255
                    self.__envelope_cycle = SidVoice.EnvelopeCycle_Decay
            # decay cycle
            elif self.__envelope_cycle == SidVoice.EnvelopeCycle_Decay:
                self.__envelope_counter -= decay_rate * iteration_scale
                if self.__envelope_counter <= sustain_target:
                    self.__envelope_counter = sustain_target 
                    self.__envelope_cycle = SidVoice.EnvelopeCycle_Sustain if sustain_target > 0 else SidVoice.EnvelopeCycle_Inactive
                self.__envelope_level = self.__envelope_counter >> 24
            elif self.__envelope_cycle == SidVoice.EnvelopeCycle_Sustain:
                # sustain cycle
                # nothing to do
                # possibly check if sustain register has changed
                # cant change in this loop, so break
                if self.__envelope_level > (sustain_target >> 24):
                    self.__envelope_level = (sustain_target >> 24)
                    self.__envelope_counter = sustain_target
                break
                
            elif self.__envelope_cycle == SidVoice.EnvelopeCycle_Release:
                # release cycle
                self.__envelope_counter -= release_rate * iteration_scale
                self.__envelope_level = self.__envelope_counter >> 24
                if self.__envelope_level <= 0:
                    self.__envelope_level = 0
                    self.__envelope_cycle = SidVoice.EnvelopeCycle_Inactive
                    break

        return adsr_active


    # advance clock where t is 1/SID_CLOCK
    def tick(self, t):

        self.__accumulator += int( round(t * self.__frequency))

        # calculate the waveform D/A output (12-bit DAC)
        # sawtooth is the top 12 bits of the accumulator
        sawtooth_level = self.__accumulator >> 12

        # pulse output is the top 12 bits of the accumulator matching the pulsewidth register
        pulse_level = 4095 if ((self.__accumulator >>12 ) == self.__pulsewidth) else 0

        # triangle output is the top 12 bits, where the low 11 bits of this are inverted by the top bit, then shifted left
        triangle_invert = 2047 if (self.__accumulator & 8388608) else 0
        triangle_level = (((self.__accumulator >> 4) ^ triangle_invert) << 1) & 4095

        sawtooth_level = sawtooth_level if self.__sawtooth else 0
        pulse_level = pulse_level if self.__pulse else 0
        triangle_level = triangle_level if self.__triangle else 0

        # waveform generator outputs are AND'ed together
        self.__waveform_level = sawtooth_level & pulse_level & triangle_level

        # update envelope generator



        # We sub divide the incoming tick interval
        # to optimize ADSR intervals for faster processing 
        # which improves performance by a significant factor
        et = t

        ETICK_RESOLUTION = SID_CLOCK / 8
        while (et > 0):

            lt = ETICK_RESOLUTION
            if (lt > et):
                lt = et

            et -= lt

            adsr_active = self.tick_envelope(lt)
            if not adsr_active:
                # ADSR is in a cycle where it is longer needing any updates
                break

# Class to manage simulated state of a SID chip
# 3 Voices are indexed as 0/1/2
class SidState(object):

    
    def __init__(self):
        self.reset()

    def reset(self):
        #self.__registers[36] = [0,]
        self.__voices = [ SidVoice(1), SidVoice(2), SidVoice(3) ]

        self.set_filter_resonance(0)
        self.set_filter_control(0)
        self.set_master_volume(0)
        self.set_filter_cutoff(0)        

    def get_voice(self, voice):
        return self.__voices[voice]


    def set_register(self,r,v):
        if r >=0 and r < 25:
            if r == 21:     # Filter cutoff LSN
                self.__filter_cutoff = (self.__filter_cutoff & 0xff00) | (v << 5)
            elif r == 22:   # Filter cutoff MSB
                self.__filter_cutoff = (self.__filter_cutoff & 0xff) | v
            elif r == 23:   # Filter resonance/voice control
                self.__filter_voice1 = (v & 1) == 1
                self.__filter_voice2 = (v & 2) == 2
                self.__filter_voice3 = (v & 4) == 4
                self.__filter_ext = (v & 8) == 8
                self.__filter_resonance = v << 4
            elif r == 24:   # Filter mode and volume
                self.__filter_lo_pass = (v & 16) == 16
                self.__filter_bn_pass = (v & 32) == 32
                self.__filter_hi_pass = (v & 64) == 64
                self.__filter_3_off = (v & 128) == 128
                self.__master_volume = v & 15
            elif r < 7:     # Voice 1
                if r == 0:      # Frequency control LSB
                    self.__voices[0].set_frequency((self.__voices[0].get_frequency() & 0xff00) | v)
                elif r == 1:    # Frequency control MSB
                    self.__voices[0].set_frequency((self.__voices[0].get_frequency() & 0xff) | (v<<8))
                elif r == 2:    # Pulsewidth LSB
                    self.__voices[0].set_pulsewidth((self.__voices[0].get_pulsewidth() & 0xff00) | v)
                elif r == 3:    # Pulsewidth MSB
                    self.__voices[0].set_pulsewidth((self.__voices[0].get_pulsewidth() & 0xff) | (v<<8))
                elif r == 4:    # Waveform/gate control
                    self.__voices[0].set_control(v)
                elif r == 5:    # Attack Decay
                    self.__voices[0].set_ad(v)
                elif r == 6:    # Sustain Release
                    self.__voices[0].set_sr(v)
            elif r < 14:     # Voice 2
                if r == 7:      # Frequency control LSB
                    self.__voices[1].set_frequency((self.__voices[1].get_frequency() & 0xff00) | v)
                elif r == 8:    # Frequency control MSB
                    self.__voices[1].set_frequency((self.__voices[1].get_frequency() & 0xff) | (v<<8))
                elif r == 9:    # Pulsewidth LSB
                    self.__voices[1].set_pulsewidth((self.__voices[1].get_pulsewidth() & 0xff00) | v)
                elif r == 10:    # Pulsewidth MSB
                    self.__voices[1].set_pulsewidth((self.__voices[1].get_pulsewidth() & 0xff) | (v<<8))
                elif r == 11:    # Waveform/gate control
                    self.__voices[1].set_control(v)
                elif r == 12:    # Attack Decay
                    self.__voices[1].set_ad(v)
                elif r == 13:    # Sustain Release
                    self.__voices[1].set_sr(v)
            elif r < 21:     # Voice 3
                if r == 14:      # Frequency control LSB
                    self.__voices[2].set_frequency((self.__voices[2].get_frequency() & 0xff00) | v)
                elif r == 15:    # Frequency control MSB
                    self.__voices[2].set_frequency((self.__voices[2].get_frequency() & 0xff) | (v<<8))
                elif r == 16:    # Pulsewidth LSB
                    self.__voices[2].set_pulsewidth((self.__voices[2].get_pulsewidth() & 0xff00) | v)
                elif r == 17:    # Pulsewidth MSB
                    self.__voices[2].set_pulsewidth((self.__voices[2].get_pulsewidth() & 0xff) | (v<<8))
                elif r == 18:    # Waveform/gate control
                    self.__voices[2].set_control(v)
                elif r == 19:    # Attack Decay
                    self.__voices[2].set_ad(v)
                elif r == 20:    # Sustain Release
                    self.__voices[2].set_sr(v)

    # filter cutoff frequency (16-bits)
    # bits 3-7 are not used?
    # registers $15-$16
    def set_filter_cutoff(self, c):
        self.__filter_cutoff = c



    # filter enable controls (4-bits)
    # register $17 (bits 0-3)
    def set_filter_control(self, fc):
        self.__filter_voice1 = (fc & 1) == 1
        self.__filter_voice2 = (fc & 2) == 2
        self.__filter_voice3 = (fc & 4) == 4
        self.__filter_ext = (fc & 8) == 8


    # filter resonance (4-bits) (0-15) where 0 is no resonance
    # register $17 (bits 4-7)
    def set_filter_resonance(self, r):
        self.__filter_resonance = r

    # master volume (4-bits) (0-16) where 0 is no volume
    # register $18 (bits 0-3)
    def set_master_volume(self, v):
        self.__master_volume = v

    def get_master_volume(self):
        return self.__master_volume

    # filter mode (4-bits)
    # register $18 (bits 4-7)
    def set_filter_mode(self, m):
        self.__filter_lo_pass = (m & 1) == 1
        self.__filter_bn_pass = (m & 2) == 2
        self.__filter_hi_pass = (m & 4) == 4
        self.__filter_3_off = (m & 8) == 8

    def is3off(self):
        return self.__filter_3_off

    def tick(self, t):
        for voice in self.__voices:
            voice.tick(t)



####### ---- SNIP ---- #######

# Imported here to bypass 'circular' imports
from common import siddumpparser as SID