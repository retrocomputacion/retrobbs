#  Punter Transfer Protocol
# 
#  Based on the CBMTerm3 implementation
#  https://github.com/sixofdloc/CBMTerm3/
#
#  Ported to python and adapted for RetroBBS in 2026 by Pablo Roldán.

from common.connection import Connection
from common.bbsdebug import _LOG
import time

class Punter:
    def __init__(self,conn:Connection):
        self.data_buffer = bytearray(512)
        self.conn = conn
        self.__OKSTR = [b'ACK',b'GOO',b'BAD',b'SYN',b'S/B']
        self.__O1STR = [b'KAC',b'OGO',b'DBA',b'NSY',b'BS/']
        self.__O2STR = [b'CKA',b'OOG',b'ADB',b'YNS',b'/BS']

    def __set_checksum(self, len):
        cksum = 0
        clc = 0
        for data in self.data_buffer[4:len]:
            cksum += data
            clc ^= data
            clc = ((clc<<1) | (clc>>15)) & 65535
        cksum &= 65535
        self.data_buffer[0] = cksum & 0xff
        self.data_buffer[1] = cksum >> 8
        self.data_buffer[2] = clc & 0xff
        self.data_buffer[3] = clc >> 8

    def __getHandshake(self):
        h = self.conn.NBReceive(3,1)
        if h in self.__OKSTR:
            return h
        elif h in self.__O1STR:
            self.conn.NBReceive(1,0.5)
            return self.__getHandshake()
        elif h in self.__O2STR:
            self.conn.NBReceive(1,0.5)
            self.conn.NBReceive(1,0.5)
            return self.__getHandshake()
        return b''

    def __waitHandshake(self):
        self.conn.FlushAll()
        retries = 12
        while retries > 0:
            hs = self.__getHandshake()
            if hs != b'':
                return hs
            time.sleep(.1)
            retries -= 1
        return b''
    
    def __punterHandshake(self, send, wait):
        retries = 10
        while retries > 0:
            self.conn.Sendallbin(send)
            hs = self.__getHandshake()
            if hs == wait:
                return True
            time.sleep(1)
            retries -= 1
        return False
    
    def __waitForHandshake(self,wait, retries):
        while self.__waitHandshake() != wait:
            _LOG(f'Multi-Punter waiting for: {wait} - retries left: {retries-1}',id=self.conn.id, v=4)
            retries -= 1
            if retries == 0:
                return False
        return True
    
    def __sendPacket(self,length):
        self.conn.Sendallbin(self.data_buffer[:length])
        retries = 12
        while retries > 0:
            hs = self.__waitHandshake()
            if hs == b'GOO':
                self.conn.Sendallbin(b'ACK')
                return self.__waitForHandshake(b'S/B',2)
            elif hs == b'BAD':
                self.conn.Sendallbin(b'ACK')
                self.__waitForHandshake(b'S/B',2)
                return False
            retries -= 1
        return None

    #####################
    # Punter transmit
    #####################
    def send(self,data,ftype):
        dataPointer = 0
        self.conn.FlushAll()
        if not self.__waitForHandshake(b'GOO',10):
            return False
        self.conn.Sendallbin(b'ACK')
        if not self.__waitForHandshake(b'S/B',10):
            return False
        # Initial packet
        self.data_buffer[4] = 4     # next block length
        self.data_buffer[5] = 0xff  # block number lo
        self.data_buffer[6] = 0xff  # block number hi
        self.data_buffer[7] = 2 if ftype else 1     # 1 PRG - 2 SEQ - 3 Wordpro
        self.__set_checksum(8)
        if self.__sendPacket(8):
            self.conn.Sendallbin(b'SYN')
            if not self.__waitForHandshake(b'SYN',10):
                return False
            self.conn.Sendallbin(b'S/B')
            if not self.__waitForHandshake(b'GOO',10):
                return False
            self.conn.Sendallbin(b'ACK')
            if not self.__waitForHandshake(b'S/B',10):
                return False
            # Dummy packet
            self.data_buffer[4] = 255 if len(data) > 248 else len(data)+7
            self.data_buffer[5] = 0
            self.data_buffer[6] = 0
            self.__set_checksum(7)
            curLength = self.data_buffer[4]
            if self.__sendPacket(7):
                # Send file packets
                packetCount = int((len(data) / 248) + (1 if (len(data) / 248) > 0 else 0))
                lastLen = len(data)%248
                packetNumber = 0
                nextLen = 255
                byteCnt = 248
                for i in range(packetCount):
                    _LOG(f'Punter sending packet {i} of {packetCount}',id=self.conn.id, v=4)
                    if i < packetCount-2:
                        nextLen = 255
                        byteCnt = 248
                    elif i == packetCount-2:
                        nextLen = lastLen + 7
                    else:
                        nextLen = 0
                        packetNumber = 0xff00 | packetNumber
                        byteCnt = lastLen
                    self.data_buffer[4] = nextLen
                    self.data_buffer[5] = packetNumber & 255
                    self.data_buffer[6] = packetNumber >> 8
                    for i in range(curLength-7):
                        self.data_buffer[7+i] = data[dataPointer+i]
                    self.__set_checksum(curLength)
                    retries = 12
                    while True:
                        res = self.__sendPacket(curLength)
                        if res: # Success
                            dataPointer += curLength-7
                            curLength = nextLen
                            packetNumber += 1
                            break
                        elif res == False:  # Bad
                            retries -= 1
                            if retries == 0:
                                return False
                        else:   # No response
                            return False
                        _LOG(f'Multi-Punter retrying {12-retries}',id=self.conn.id, v=4)
                self.conn.Sendallbin(b'SYN')
                if not self.__waitForHandshake(b'SYN',10):
                    return False
                self.conn.Sendallbin(b'S/B')
                return True
        return False

    #####################################################
    # Single and Multi-Punter transmit
    #
    # args = data, seq for single file
    # args = [(filename,savename,seq)] for multi-file
    #####################################################
    def punterXmit(self,*args):
        MP_SYNC = b'\x09\x09\x09\x09\x09\x09\x09\x09\x09\x09\x09\x09\x09\x09\x09\x09'
        MP_END = b'\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04\x04'
        if len(args) == 0:
            return False
        elif len(args) == 1:   # Multi-Punter
            flist = args[0]
            result = True
            for i in range(5,0,-1):
                self.conn.SendTML(f'<BR>Download starts in {i}...')
                time.sleep(1)
            for f in flist:
                _LOG(f'Multi-Punter sending: {f[0]}',id=self.conn.id, v=4)
                with open(f[0],'rb') as rf:
                    data=rf.read()
                self.conn.Sendallbin(MP_SYNC)
                self.conn.Sendallbin(f[1].encode('latin1')+b','+(b'S\x0d' if f[2] else b'P\x0d'))
                # self.conn.Sendallbin(b'GOO')
                result &= self.send(data,f[2])
                time.sleep(1.5)
            self.conn.Sendallbin(MP_SYNC)
            self.conn.Sendallbin(MP_END)
            self.conn.Sendallbin(b'\x0d')
            return result
        else:   
            for i in range(5,0,-1):
                self.conn.SendTML(f'<BR>Download starts in {i}...')
                time.sleep(1)
            return self.send(args[0],args[1])
