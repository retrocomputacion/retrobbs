############ Connection Class ############
#########################################################################
#Changelog																#
#																		#
#	April  6-2021	: Moved all functions to methods inside the			#
#					  Connection class									#
#########################################################################

import socket
from common.bbsdebug import _LOG, bcolors
import datetime
from common import turbo56k as TT
from common.classes import BBS, bbsstyle, Encoder, template
import time
from common.parser import TMLParser
import errno
import string
from itertools import cycle

# Dictionary of client variant -> Encoder
clients = {'default':'PET64', 'SL':'PET64', 'SLU':'PET64', 'P4':'PET264', 'M1':'MSX1'}

########### Connection class ###########
class Connection:
    def __init__(self, socket, addr, bbs, id):
        self.connected = True
        self.socket = socket
        self.addr = addr
        self.id = id
        self.bbs:BBS = bbs

        # MenuDef entry:
        # [Function, (Parameters tuple), Title, UserClass , WaitKey, Mode]
        self.MenuDefs = {}			#Current Menu functions dictionary
        self.MenuParameters = {}	#Current Menu parameters dictionary
        self.MenuStack = []			#Menu stack

        self.waitkey = False		# Menu is waiting for a keypress
        self.showmenu = False		# Menu needs to be redrawn
        self.newmenu = 0			# Temporal menu id storage
        self.menu = 0				# Current menu id

        self.samplerate = 11520		# PCM audio stream samplerate 

        self.outbytes = 0			# Total bytes sent
        self.inbytes = 0			# Total bytes received

        self.username = '_guest_'
        self.userid	= 0
        self.userclass = 0			# 0 = Guest

        self.stime = time.time()	# Session start timestamp

        self.TermString = '' 		# Terminal identification string
        self.T56KVer = 0			# Terminal Turbo56K version
        self.TermFt = {i:None for i in range(128,256)}	# Terminal features
        self.TermFt[0xFF] = 0
        self.TermFt[0xFE] = 0
        self.ClientSetup = {0:[1,{'Platform':None,'Refresh':None}],1:[2,{'Text':None}],2:[1,{'Bitrate':None}],3:[2,{'RAM':None}],4:[2,{'VRAM':None}],5:[1,{'GFXModes':None}],6:[2,{'Synths':None,'PCM':None}]}
        self.mode = 'ASCII'			                        # Connection mode -> type of client
        self.encoder:Encoder = self.bbs.encoders[self.mode]	# Encoder for this connection
        self.style = bbsstyle(self.encoder.colors)
        self.templates = template(self,self.bbs.Template)
        self.parser = TMLParser(self)				        # TML parser
        self.p_running = False
        self.user_prefs = {'datef':bbs.dateformat}
        self.spinner = None                                 # Spinner cycle iterator
        self.on_hold = False                                # Is spinner on display?

        _LOG('Incoming connection from', addr,id=id,v=3)
    
    def __del__(self):
        try:
            self.socket.close()
        except:
            pass

    #################
    #Close socket
    #################
    def Close(self):
        _LOG("Total bytes sent/received: "+str(self.outbytes)+'/'+str(self.inbytes),id=self.id,v=3)
        try:
            self.connected = False
            self.socket.close()
        except:
            pass

    ######################################
    #Set mode from the terminal string
    ######################################
    def SetMode(self, idstring, t56kver):
        self.TermString = idstring
        self.T56KVer = t56kver
        mode = 'PET64' if b'-' not in idstring else self.bbs.clients.get(idstring.split(b' ')[0].split(b'-')[1],'PET64')
        if not self.p_running:		# Only change the mode if the TML parser object is not running
            self.mode = mode							#Connection mode -> type of client
            self.encoder = self.bbs.encoders[self.mode]	#Encoder for this connection
            tmp = self.encoder.setup(self,'default' if b'-' not in idstring else idstring.split(b' ')[0].split(b'-')[1])
            if tmp != None:
                self.encoder = tmp
                self.mode = tmp.name
            # Reinit Terminal features
            self.TermFt[0xb7] = None	# Maybe reinit the whole dictionary in the future?
            del(self.parser)
            self.parser = TMLParser(self)
            del(self.style)
            self.style = bbsstyle(self.encoder.colors)  # Init default colors
            del(self.templates)
            self.templates = template(self,self.bbs.Template)
            self.style = self.templates.GetStyle('default') # Set template colors
            self.templates.j2env.globals['st'] = self.style # Update the globals with the new colors
            if self.encoder.spinner['loop'] != None:
                self.spinner = cycle(self.encoder.spinner['loop'])
            else:
                self.spinner = None
            _LOG(f'Connection mode set to: {mode}', id=self.id, v=2)
            return True
        else:
            return False
    
    ##############################
    # Reset feature dictionary
    ##############################
    def ResetFeatures(self):
        self.TermFt = {i:None for i in range(128,256)}
        self.TermFt[0xFF] = 0
        self.TermFt[0xFE] = 0

    #####################################################
    # Query if the client terminal supports a feature
    #####################################################
    def QueryFeature(self, cmd:int):
        #return 0x80		# Uncomment this when testing commands
        if (self.T56KVer == 0) or (cmd < 128) or (cmd > 253):
            return 0x80
        if self.T56KVer > 0.5:
            if self.TermFt[cmd] == None:
                if self.T56KVer < 0.7:	#Try to avoid retroterm 0.14 bug
                    self.Flush(0.5)
                    time.sleep(0.5)
                self.Sendall(chr(TT.CMDON))
                self.Sendall(chr(TT.QUERYCMD)+chr(cmd))
                self.Sendall(chr(TT.CMDOFF))
                tmp = self.NBReceive(1)
                if len(tmp) > 0:
                    self.TermFt[cmd] = tmp[0] 	# Store as int
                else:
                    return 0x80                 # Command failed, return 0x80 but dont store it
        elif self.TermFt[cmd] == None:
            self.TermFt[cmd] = TT.T56Kold[cmd-128][0]
        return self.TermFt[cmd]

    ##############################
    # Query the client's setup
    ##############################
    def QueryClient(self,subsystem:int):
        platforms = ['Commodore 64','Commodore Plus/4','MSX','Commodore 128','Commodore VIC-20','ZX Spectrum','Atari','Apple ][','Amstrad','Amiga','Commodore PET']
        bitrates = [0,300,600,1200,1800,2400,4800,9600,19200,28800,38400,57600,76800,115200]
        spb = [8,2,1,0.5]   # samples per byte
        samplerates = [11050,16000,22050]   # fixed sample rates

        if self.QueryFeature(TT.QUERYCMD) < 128:
            if subsystem < 7:
                if None in self.ClientSetup[subsystem][1].values():
                    self.Sendall(chr(TT.CMDON)+chr(TT.QUERYCLIENT)+chr(subsystem)+chr(TT.CMDOFF))
                    count = self.NBReceive(1)
                    if len(count) < 1:
                        return None
                    if count[0] >= self.ClientSetup[subsystem][0]:
                        qdata = self.NBReceive(count[0])
                        if len(qdata) < count[0]:
                            return None
                        if subsystem == 0:  # Platform / refresh rate
                            if qdata[0] & 0x7F < len(platforms):
                                self.ClientSetup[subsystem][1]['Platform'] = platforms[qdata[0] & 0x7F]
                            else:
                                self.ClientSetup[subsystem][1]['Platform'] = 'unknown'
                            if qdata[0] & 0x80 == 0:
                                self.ClientSetup[subsystem][1]['Refresh'] = 50
                            else:
                                self.ClientSetup[subsystem][1]['Refresh'] = 60
                        if subsystem == 1:  # Text screen size
                            self.ClientSetup[subsystem][1]['Text'] = [qdata[0],qdata[1]]    # TODO: Update encoder with these values
                        if subsystem == 2:  # Bit rate
                            if qdata[0] < len(bitrates):
                                self.ClientSetup[subsystem][1]['Bitrate'] = bitrates[qdata[0]]
                            else:
                                self.ClientSetup[subsystem][1]['Bitrate'] = 57600
                        if subsystem == 3:  # RAM
                            self.ClientSetup[subsystem][1]['RAM'] = (qdata[1]*256)+qdata[0]
                        if subsystem == 4:  # VRAM
                            self.ClientSetup[subsystem][1]['VRAM'] = (qdata[1]*256)+qdata[0]
                        if subsystem == 5:  # Graphic modes
                            self.ClientSetup[subsystem][1]['GFXModes'] = qdata[0]   # Platform dependent - In the future the encoder should be configured here
                        if subsystem == 6:  # Audio
                            self.ClientSetup[subsystem][1]['Synths'] = qdata[0]   # Platform dependent - In the future the encoder should be configured here
                            self.ClientSetup[subsystem][1]['PCM'] = qdata[1]
                            if qdata[1] & 0b01111000 > 0:
                                tmp_s = spb[qdata[1] & 0b11]
                                tmp_sr = self.samplerate
                                channels = (qdata[1] & 0b100) >> 1
                                # tmp_s *= 1 if qdata[1] & 0b100 == 0 else 2
                                tmp = (qdata[1] & 0b01111000) >> 3
                                for i in range(4):  # Get lowest available samplerate (or dependent on connection speed)
                                    if tmp & 1 == 1:
                                        if i == 0:
                                            if self.ClientSetup[2][1]['Bitrate'] != None:
                                                tmp_sr = (self.ClientSetup[2][1]['Bitrate']/10)*tmp_s
                                            break
                                        else:
                                            tmp_sr = samplerates[i-1]
                                            break
                                    tmp = tmp >> 1
                                self.samplerate = tmp_sr
                    else:       # Response size is too small
                        _LOG(f"QueryClient: Response size too small / Subsystem {subsystem} not implemented", id = self.id,v=3)
                        return None
            else:
                return None
        if subsystem < 7:
            return self.ClientSetup[subsystem][1]
        else:
            return None

    #########################################################
    # Set the connection into hold mode (display spinner)
    #########################################################
    def SetHold(self):
        if not self.on_hold:
            self.SendTML(self.encoder.spinner['start'])
            self.on_hold = True

    #######################################################
    # Clear the hold mode (stop displaying the spinner)
    #######################################################
    def ClearHold(self):
        if self.on_hold:
            self.on_hold = False
            self.SendTML(self.encoder.spinner['stop'])
            if self.encoder.spinner['loop'] != None:
                self.spinner = cycle(self.encoder.spinner['loop'])  # Make a new iterator so it starts always on the same place

    ########################################################################################
    # Update spinner state
    # No safety checks, this method is only called from the connection management thread
    ########################################################################################
    def _HoldUpdate(self):
        self.on_hold = False
        self.SendTML(next(self.spinner))
        self.on_hold = True

    ##############################################################
    # Converts string to binary string and sends it via socket
    ##############################################################
    def Sendall(self, _string):
        self.ClearHold()
        if self.connected == True:
            _bytes = bytes(_string,'latin1')
            try:
                self.socket.sendall(_bytes)
                self.outbytes += len(_bytes)
            except socket.error:
                self.connected = False
                _LOG(bcolors.WARNING+'Remote disconnect/timeout detected - Sendall'+bcolors.ENDC, id=self.id,v=2)

    ###################################
    # Send binary string via socket
    ###################################
    def Sendallbin(self, _string=b''):
        self.ClearHold()
        if self.connected == True:
            try:
                self.socket.sendall(_string)
                self.outbytes += len(_string)
            except socket.error:
                #if e == errno.EPIPE:
                _LOG(bcolors.WARNING+'Remote disconnect/timeout detected - Sendallbin'+bcolors.ENDC, id=self.id,v=2)
                self.connected = False

    ############################################
    # Flush receive buffer for ftime seconds
    ############################################
    def Flush(self, ftime):
        self.socket.setblocking(0)	# Change socket to non-blocking
        t0 = time.time()
        while time.time()-t0 < ftime:
            try:
                self.socket.recv(10)
            except Exception as e:
                pass
        self.socket.setblocking(1)	# Change socket to blocking
        self.socket.settimeout(self.bbs.TOut)


    ############################################
    # Flush receive buffer empty
    ############################################
    def FlushAll(self):
        self.socket.setblocking(0)	# Change socket to non-blocking
        while True:
            try:
                self.socket.recv(1)
            except Exception as e:
                # We exit on any error, not just EAGAIN or EWOULDLOCK
                break
        self.socket.setblocking(1)	# Change socket to blocking
        self.socket.settimeout(self.bbs.TOut)

    ##############################################
    # Receive (count) binary chars from socket
    ##############################################
    def Receive(self, count):
        _string = b''
        if self.connected == True:
            for c in range(0,count):
                try:
                    _string += self.socket.recv(1)
                    self.inbytes += 1
                except socket.error:
                    _LOG(bcolors.WARNING+'Remote disconnect/timeout detected - Receive'+bcolors.ENDC, id=self.id,v=2)
                    self.connected = False
                    _string = b''
                    break
        return _string

    ###########################################################################################
    # Non-blocking receive up to (count) binary chars from socket, within (timeout) seconds
    ###########################################################################################
    def NBReceive(self, count:int=1, timeout:float=3):
        data = b""
        self.socket.setblocking(False)
        tmp = time.time()
        while ((time.time()-tmp) < timeout) and (len(data) < count):
            try:
                data += self.socket.recv(1) 
            except socket.error as e:
                err = e.args[0]
                if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
                    time.sleep(0.5)
                    continue
                else:
                    pass
        self.socket.setblocking(True)
        self.socket.settimeout(self.bbs.TOut)
        self.inbytes += len(data)
        return data

    ############################################
    # Receive single binary char from socket
    ############################################
    def ReceiveKey(self, charlist=b''):
        if type(charlist) != list:
            if charlist == b'':
                charlist = bytes(self.encoder.nl,'latin1')
            if type(charlist) == str:
                charlist = bytes(self.encoder.encode(charlist,True),'latin1') 
                decode = True
            else:
                decode = False
            t = True
            while t == True:
                _string = b''
                if self.connected == True:
                    try:
                        _LOG("ReceiveKey - Waiting...",id=self.id,v=4)
                        _string = self.socket.recv(1)
                        self.inbytes += 1
                        _LOG("ReceiveKey - Received", _string, id=self.id,v=4)
                        if _string != b'':
                            if ('PET' in self.mode) and (_string[0] in range(0xC1,0xDA + 1)):
                                _string = bytes([_string[0]-96])
                            if _string in charlist:
                                t = False
                        else:
                            self.connected = False
                            t = False
                    except socket.error:
                        #if e.errno == errno.ECONNRESET:
                        _LOG(bcolors.WARNING+'Remote disconnect/timeout detected - ReceiveKey'+bcolors.ENDC, id=self.id,v=2)
                        _string = ''
                        self.connected = False
                        t = False
                else:
                    t = False
            return _string if not decode else self.encoder.decode(_string.decode('latin1'))
        else:
            mlen = max([len(a) for a in charlist])
            vfilter = string.ascii_letters + string.digits + " !?';:[]()*/@+-_,.$%&=<>#\\^" + chr(34)
            _charlist = charlist.copy()
            eflag = [False]*len(_charlist)
            for i,item in enumerate(_charlist):     # Encode single characters
                if item in vfilter and item != self.encoder.back:
                    _charlist[i] = self.encoder.encode(item,True)
                    eflag[i] = True
            charlist = []
            for i in range(mlen):
                c = []
                for j in _charlist:
                    if len(j) >= i+1:
                        c.append(j[i])
                    else:
                        c.append('')
                charlist.append(c)
            received = ''
            while True and self.connected:
                try:
                    _LOG("ReceiveKey - Waiting...",id=self.id,v=4)
                    inchar = chr(self.socket.recv(1)[0])
                    if ('PET' in self.mode) and (ord(inchar) in range(0xC1,0xDA + 1)):
                        inchar = chr(ord(inchar)-96)
                    self.inbytes += 1
                    if inchar in charlist[len(received)]:
                        received += inchar
                        if received in _charlist:
                            break
                    else:
                        received = ''
                except socket.error:
                    #if e.errno == errno.ECONNRESET:
                    _LOG(bcolors.WARNING+'Remote disconnect/timeout detected - ReceiveKey'+bcolors.ENDC, id=self.id,v=2)
                    received = ''
                    self.connected = False
                    break
            if eflag[_charlist.index(received)]:
                return self.encoder.decode(received)
            else:
                return received

    #####################################################
    # Receive single binary char from socket - NO LOG
    #####################################################
    def ReceiveKeyQuiet(self, charlist=b''):
        if charlist == b'':
            charlist = bytes(self.encoder.nl,'latin1')
        if type(charlist) == str:
            charlist = bytes(self.encoder.encode(charlist,True),'latin1')
            decode = True
        else:
            decode = False
        t = True
        while t == True:
            _string = b''
            if self.connected == True:
                try:
                    _string = self.socket.recv(1)
                    self.inbytes += 1
                    if _string != b'':
                        if ('PET' in self.mode) and (_string[0] in range(0xC1,0xDA + 1)):
                            _string = bytes([_string[0]-96])
                        if _string in charlist:
                            t = False
                    else:
                        self.connected = False
                        t = False
                except socket.error:
                    #if e.errno == errno.ECONNRESET:
                    _LOG(bcolors.WARNING+'Remote disconnect/timeout detected - ReceiveKey'+bcolors.ENDC, id=self.id,v=2)
                    _string = ''
                    self.connected = False
                    t = False
            else:
                t = False
        return _string if not decode else self.encoder.decode(_string.decode('latin1'))

    ##################################################
    # Interactive string reception with echo
    # maxlen = max number of characters to receive
    # pw = True for password entry
    ##################################################
    def ReceiveStr(self, keys, maxlen = 20, pw = False):
        if type(keys) == str:
            keys  = bytes(self.encoder.encode(keys,True),'latin1')
        cr = bytes(self.encoder.nl,'latin1')
        bs = bytes(self.encoder.bs,'latin1')
        if cr not in keys:
            keys += cr	#Add RETURN if not originaly included
        if bs not in keys:
            keys += bs #Add DELETE if not originaly included
        _string = b''
        done = False
        while not done:
            if pw:
                k = self.ReceiveKeyQuiet(keys)
            else:
                k = self.ReceiveKey(keys)
            if self.connected:
                if k != cr and k != b'':
                    if k == bs:
                        if len(_string) > 0:
                            _string = _string[:-1]	#Delete character
                            self.SendTML('<DEL>')
                    elif len(_string) < maxlen:
                        _string += k	#Add character
                        if pw:
                            self.Sendall('*')
                        else:
                            self.Sendallbin(k)
                else:
                    done = True
            else:
                done = True
        return(_string.decode('latin1'))

    ####################################################################################
    # Interactive positive integer reception with echo
    # min = minimun value
    # max = maximun value
    # default = default value returned when pressing return
    # auto = if True entry can be canceled by pressing delete with no value entered,
    #		 and is completed if the number of digits matches the limits
    ####################################################################################
    def ReceiveInt(self, minv, maxv, defv, auto = False):
        cr = bytes(self.encoder.nl,'ascii')
        bs = bytes(self.encoder.bs,'ascii')
        ins = self.encoder.ctrlkeys.get('INSERT',None)
        if ins != None:
            ins = ord(ins).to_bytes(1,'big')
        if minv < 0:
            minv = -minv
        if maxv < 0:
            maxv = -maxv
        if maxv < minv:
            maxv = minv+1
        if not(minv <= defv <= maxv):
            defv = minv
        o_val = 0
        o_str = ''
        digits = 0
        keys = bs+cr+b'0123456789'
        while True:
            temp = self.ReceiveKey(keys)
            if temp == bs:
                if digits > 0:
                    self.SendTML('<DEL>')
                    o_val //=10
                    digits -= 1
            elif temp == cr:
                if digits == 0:
                    return defv
                elif o_val >= minv:
                    return o_val
            else: #Digits
                if (o_val*10)+int(temp) <= maxv:
                    o_val = (o_val*10)+int(temp)
                    digits += 1
                    self.Sendallbin(temp)



    def _ReceiveInt(self, minv, maxv, defv, auto = False):
        cr = bytes(self.encoder.nl,'ascii')
        bs = bytes(self.encoder.bs,'ascii')
        ins = self.encoder.ctrlkeys.get('INSERT',None)
        if ins != None:
            ins = ord(ins).to_bytes(1,'big')
        if minv < 0:
            minv = -minv
        if maxv < 0:
            maxv = -maxv
        if maxv < minv:
            maxv = minv+1
        if not(minv <= defv <= maxv):
            defv = minv
        temp = b''
        done = False
        vall = max(len(str(minv)),len(str(maxv))) #Max digits
        mins = str(minv).zfill(vall)	#Min value string with padding 0s
        maxs = str(maxv).zfill(vall)	#Max value string with padding 0s
        defs = str(defv).zfill(vall)	#Default value string with padding 0s
        tval = ['0']*vall
        d = 0
        minr = int(mins[0])
        maxr =int(maxs[0])+1
        while True:
            keys = bs
            if d < vall:
                for x in range(minr,maxr):
                    keys += bytearray(str(x),'utf-8')
                    if d == 0:
                        keys += cr
            else:
                keys += cr
            temp = self.ReceiveKey(keys)
            if not self.connected:
                return(None)
            if d == 0:
                if temp == bs:
                    if auto:
                        return(None)
                    else:
                        continue
                elif temp == cr:
                    self.Sendall(defs)
                    return(defv)
            if temp != cr:
                if temp != bs:
                    tval[d] = temp.decode('utf-8')
                    d += 1
                    self.Sendallbin(temp)
                else:
                    self.SendTML('<DEL>')
                    d -= 1
                    if ins != None:
                        self.Sendallbin(ins) #Insert
            else:
                break
            # Calculate next digit range
            if d == 0:
                minr = int(mins[0])
                maxr =int(maxs[0])+1
            elif d < vall:
                if int(tval[d-1]) == int(mins[d-1]):
                    minr = int(mins[d])
                else:
                    minr = 0
                if int(tval[d-1]) == int(maxs[d-1]):
                    maxr = int(maxs[d])+1
                else:
                    maxr = 10
            if d == vall and auto:
                break
        return(int(''.join(tval)))

    ##########################################################################
    # Receive a date, format taken from bbs instance
    # prompt: TML prompt
    # mindate: Earliest date possible
    # maxdate: Latest date possible
    # defdate: Default date
    # all dates of datetime.date type
    # Returns a datetime.date object, None if the parameters are incorrect
    ##########################################################################
    def ReceiveDate(self, prompt, mindate, maxdate, defdate):
        if (mindate > maxdate) or not (mindate <= defdate <= maxdate):
            return None
        
        cr = bytes(self.encoder.nl,'ascii')
        bs = bytes(self.encoder.bs,'ascii')

        odate = defdate
        dateord = [[0,1,2],[1,0,2],[2,1,0]]		#Fields order
        dateleft = [[0,3,3],[3,0,3],[3,5,0]]	#Left cursor count
        dord = dateord[self.bbs.dateformat]
        dleft = dateleft[self.bbs.dateformat]
        if self.bbs.dateformat == 1:
            datestr = "%m/%d/%Y"
            dout = "mm/dd/yyyy"
        elif self.bbs.dateformat == 2:
            datestr = "%Y/%m/%d"
            dout = "yyyy/mm/dd"
        else:
            datestr = "%d/%m/%Y"
            dout = "dd/mm/yyyy"
        while True:
            self.SendTML(prompt+dout+'<CRSRL n=10>')
            x = 0
            while True:
                if x == dord[0]: #0
                    day = self._ReceiveInt(1,31,defdate.day,True)
                    if not self.connected:
                        return
                    if day == None:
                        if x > 0:
                            self.SendTML(f'<CRSRL n={dleft[0]}>')
                            x -= 1
                        continue
                    if x < 2:
                        x += 1
                        self.SendTML('<CRSRR>')
                    else:
                        if self.ReceiveKey(bs+cr) == cr:
                            break
                        else:
                            self.SendTML('<DEL n=2>')
                if x == dord[1]: #1
                    month = self._ReceiveInt(1,12,defdate.month,True)
                    if not self.connected:
                        return
                    if month == None:
                        if x > 0:
                            self.SendTML(f'<CRSRL n={dleft[1]}>')
                            x -= 1
                        continue
                    if x < 2:
                        x += 1
                        self.SendTML('<CRSRR>')
                    else:
                        if self.ReceiveKey(bs+cr) == cr:
                            break
                        else:
                            self.SendTML('<DEL n=2>')
                if x == dord[2]: #2
                    year = self._ReceiveInt(mindate.year,maxdate.year,defdate.year,True)
                    if not self.connected:
                        return
                    if year == None:
                        if x > 0:
                            x -= 1
                            self.SendTML(f'<CRSRL n={dleft[2]}>')
                        continue
                    if x < 2:
                        x += 1
                        self.SendTML('<CRSRR>')
                    else:
                        if self.ReceiveKey(bs+cr) == cr:
                            break
                        else:
                            self.SendTML('<DEL n=4>')
            try:
                odate = datetime.date(year,month,day)
                if mindate <= odate <= maxdate:
                    break
                else:
                    self.SendTML("<BR>Invalid date!<BR>")
            except ValueError:
                self.SendTML("<BR>Invalid date!<BR>")
        return odate

    #####################
    # Send TML script
    #####################
    def SendTML(self, data, registers: dict = {'_A':None,'_S':'','_I':0}):
        self.ClearHold()
        if self.p_running:				# If original parser is in use
            parser = TMLParser(self)	# create new TML parser for each call, to allow for nested calls
            ret = parser.process(data,registers)
            del(parser)					# Delete aditional parser after use
        else:							# Use original parser if this is the first call, this is faster than just creating a new object every time
            self.p_running = True
            ret = self.parser.process(data,registers)
            self.p_running = False
        return ret

#################################################
# Dummy Connection object
# Doesnt actually sends or receives anything,
# just decodes/buffers all input data until
# getOutput() is called
# Dummy connection objects have negative IDs
#################################################
class DummyConn(Connection):
    
    def __init__(self, conn:Connection):
        _output = ''
        super().__init__(None,0,conn.bbs,-conn.id)
        self.mode = conn.mode
        self.encoder = conn.encoder
        self.TermString = conn.TermString
        self.T56KVer = conn.T56KVer
        self.TermFt[0xb7] = None	# Maybe reinit the whole dictionary in the future?
        del(self.parser)
        self.parser = TMLParser(self)
        del(self.style)
        self.style = bbsstyle(self.encoder.colors)


    def getOutput(self):
        _tmp = self._output
        self._output = ''
        return _tmp

    # Query if the client terminal supports a feature
    def QueryFeature(self, cmd:int):
        return 0x80		# Dummy connection doesn't support any command
    
    def Sendall(self,_string):
        _output = _output + _string
    
    def Sendallbin(self, _string=b''):
        self.Sendall(_string.decode('latin1'))
    
    def Flush(self, ftime):
        return
    
    def Receive(self, count):
        return ''

    def ReceiveKey(self, charlist=b''):
        return ''
    
    def ReceiveKeyQuiet(self, charlist=b''):
        return ''
    
    def ReceiveStr(self, keys, maxlen=20, pw=False):
        return ''
    
    def ReceiveInt(self, minv, maxv, defv, auto=False):
        return defv

    def ReceiveDate(self, prompt, mindate, maxdate, defdate):
        return defdate

