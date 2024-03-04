import time
import irc.client
import string
import select
import socket

from common.bbsdebug import _LOG,bcolors
from common import helpers as H
from common import style as S
from common.connection import Connection
from common import turbo56k as TT

###############
# Plugin setup
###############
def setup():
    fname = "IRC" #UPPERCASE function name for config.ini
    parpairs = [('server','irc.libera.chat'),('port',6667),('channel','')] #config.ini Parameter pairs (name,defaultvalue)
    return(fname,parpairs)

#######################################################
# Plugin function
#######################################################
def plugFunction(conn:Connection,server,port,channel):
    _dec = conn.encoder.decode
    _enc = conn.encoder.encode
    running = False
    kfilter = conn.encoder.non_printable.copy()
    kfilter.append('\r')
    nickname = ''
    keys = string.ascii_letters + string.digits + " !?';:[]()*/@+-_,.$%&"
    #Current cursor position in input window
    curcolumn = 0
    curline = 0

    # Send TML or PETSCII list to the chat window
    def printchat(text):
        conn.SendTML(f'<NUL n=2><WINDOW top=3 bottom={scheight-4}><AT x=0 y={scheight-7}>')
        if isinstance(text,list):
            for t in text:
                conn.SendTML(t)
        else:
            conn.SendTML(text)
        conn.SendTML(f'<WINDOW top={scheight-2} bottom={scheight-1}><AT x={curcolumn} y={curline}>{"<GREY3>" if "PET" in conn.mode else "<GREY>"}')

    def on_currenttopic(c, event):
        txt = H.formatX('['+event.arguments[0]+'] Topic is: '+event.arguments[1],scwidth)
        txt[0] = '<CYAN>'+txt[0]
        printchat(txt)

    def on_topic(c, event):
        txt = H.formatX('['+channel+'] Topic changed to: '+event.arguments[0]+'\r',scwidth)
        txt[0] = '<CYAN>'+txt[0]
        printchat(txt)

    def on_nicknameinuse(c, e):
        nonlocal nickname
        printchat(f'<CYAN>{nickname} in use<BR>Trying {nickname}-<BR>')
        nickname += '-'
        c.nick(nickname)
        conn.SendTML(f'<GREEN><LFILL row={scheight-3} code={hcode}><WINDOW top={scheight-3} bottom={scheight-3}><RVSON><CRSRR>{nickname}'
                     f'{"<GREY3>" if "PET" in conn.mode else "<GREY>"}<WINDOW top={scheight-2} bottom={scheight-1}><RVSOFF>')

    def on_pubmsg(connection, event):
        user = event.source
        if '!' in user:
            user = user[0:user.index('!')]
        elif '@' in user:
            user = user[0:user.index('@')]
        txt = H.formatX(user+': '+event.arguments[0],scwidth)
        txt[0]= f'<LTBLUE>{txt[0][0:len(user)+1]}{"<GREY2>" if "PET" in conn.mode else "<GREY>"}{txt[0][len(user)+2:]}'
        printchat(txt)

    def on_action(connection, event):
        user = event.source
        if '!' in user:
            user = user[0:user.index('!')]
        elif '@' in user:
            user = user[0:user.index('@')]
        txt = H.formatX('* '+user+' '+event.arguments[0],scwidth)
        txt[0]= f'{"<ORANGE>" if "PET" in conn.mode else "<DRED>"}{txt[0][0:len(user)+2]}{"<GREY3>" if "PET" in conn.mode else "<GREY>"}{txt[0][len(user)+2:]}'
        printchat(txt)

    def on_privmsg(connection, event):
        _LOG(event,id=conn.id,v=4)
    
    def on_privnotice(connection, event):
        txt = H.formatX(event.arguments[0],scwidth)
        txt[0] = ("<ORANGE>" if "PET" in conn.mode else "<DRED>")+txt[0]
        printchat(txt)

    def on_pubnotice(connection, event):
        txt = H.formatX('>'+_enc(event.target)+'<'+_enc(event.arguments[0]),scwidth)
        txt[0] = '<YELLOW>'+txt[0]
        for x in range(len(txt)):
            txt[x] = '<RVSON>'+txt[x]
        printchat(txt)

    def on_connect(connection, event):
        printchat(f'<CYAN>Connected to: {server}<BR>')
        txt = H.formatX(event.arguments[0],scwidth)
        txt[0] = '<CYAN>'+txt[0]
        printchat(txt)
        if irc.client.is_channel(channel):
            connection.join(channel)
        #main_loop(connection)

    def on_names(connection, event):
        text = H.formatX('Users in '+channel+': '+event.arguments[2],scwidth)
        text[0] = '<CYAN>'+text[0]
        for i in range(len(text)):
            x = text[i].find(':')
            if x !=-1:
                text[i] = text[i][:x+1]+'<GREEN>'+text[i][x+1:]
        printchat(text)

    def on_join(connection, event):
        nonlocal running

        user = (event.source.nick if event.source.nick != nickname else '')+' '
        printchat(f'<CYAN>{user}Joined {event.target}<BR>')
        running = True

    def on_part(connection, event):
        user = (event.source.nick if event.source.nick != nickname else '')+' '
        if len(event.arguments) != 0:
            msg = f' ({event.arguments[0]})'
        else:
            msg = ''
        printchat(f'<CYAN>{user}left {event.target}{msg}<BR>')

    def on_disconnect(connection, event):
        nonlocal running

        printchat('<YELLOW>Disconnected...<BR>')
        conn.socket.setblocking(1)
        conn.socket.settimeout(60*5)
        time.sleep(2)
        running = False

    def command_parser(connection,text):
        nonlocal running
        nonlocal nickname
        nonlocal channel
        if text.lower() == '/help':
            hstring = """----------------------------------------
Accepted commands:
    /help - This text
    _ - Exit chat
    /quit - Exit chat
    /nick nickname - Change nickname
    /join channel - Join channel 
                    (Parts current)
    /names - List users in channel
    /me action - Send action to the 
                 channel
----------------------------------------"""
            txt = H.formatX(hstring,scwidth)
            for i in range(len(txt)):
                txt[i] = txt[i].replace('_','<BACK>') #FIXME: this a PETSCII workaround
            printchat(txt)
        elif text.lower() == '/quit':
            running = False
            connection.part(['Using RetroBBS IRC plugin'])
            connection.quit('Using-RetroBBS-IRC-plugin')
            return
        elif text.lower().startswith('/nick'):
            pars = text.split(' ')
            if len(pars)>1:
                nickname = _dec(pars[1].translate({ord(i): None for i in '#?!@/()&$"'}))
                c.nick(nickname)
                conn.SendTML(f'<GREEN><LFILL row={scheight-3} code={hcode}><WINDOW top={scheight-3} bottom={scheight-3}><RVSON><CRSRR>{nickname}'
                             f'{"<GREY3>" if "PET" in conn.mode else "<GREY>"}<WINDOW top={scheight-2} bottom={scheight-1}><RVSOFF><AT x={curcolumn} y={curline}')
            else:
                printchat('Usage: NICK &lt;nick&gt;, change your nick<BR>')
        elif text.lower().startswith('/join'):
            pars = text.split(' ')
            if len(pars)>1:
                oldchan = channel
                channel = _dec(pars[1].translate({ord(i): None for i in '@/"'}))
                if channel[0] != '#':
                    channel = '#'+channel
                connection.part(oldchan,':Using-RetroBBS-IRC-plugin')
                #connection.send_raw('PART '+oldchan+' :Using-RetroBBS-IRC-plugin')
                connection.join(channel)
            else:
                printchat('Usage: JOIN &lt;channel&gt; join a new channel') #40 characters<<<<<
        elif text.lower().startswith('/names'):
            connection.names(channel)
        elif text.lower().startswith('/me'):
            pars = text.split(' ')
            if len(pars)>1:
                connection.action(channel,_dec(' '.join(pars[1:])))
                msg = H.formatX('* '+nickname+' '+_dec(' '.join(pars[1:])),scwidth)
                msg[0] = '<YELLOW>'+msg[0]
                printchat(msg)
            else:
                printchat(H.formatX('Usage: ME <action> send action (written in 3rd person) to the channel',scwidth))

    ####
    scwidth,scheight = conn.encoder.txt_geo
    if 'MSX' in conn.mode:
        bcode = 0xDB
        hcode = 0x17
    else:
        bcode = 0xA0
        hcode = 0x40
    S.RenderMenuTitle(conn,'IRC')
    conn.SendTML(f'<GREEN><LFILL row={scheight-3} code={hcode}>')
    if conn.userclass > 0:
        nickname = conn.username[0:9]
    else:
        conn.SendTML(f'<WINDOW top={scheight-2} bottom={scheight-1}><YELLOW>Enter nick: {"<GREY3>" if "PET" in conn.mode else "<GREY>"}')
        nickname = _dec(conn.ReceiveStr(bytes(keys,'ascii'), 9)) #Get nick
    nickname = nickname.translate({ord(i): None for i in '#?!@/()&$"'})
    conn.Sendall(TT.set_Window(0,scheight))
    if nickname == '':
        time.sleep(0.5)
        return
    conn.SendTML(f'<AT x=1 y={scheight-3}><RVSON><GREEN>{nickname}<BR>'
                 f'<WINDOW top={scheight-2} bottom={scheight-1}><CLR>')
    if channel == '':
        conn.SendTML(f'<YELLO>Enter channel: #{"<GREY3>" if "PET" in conn.mode else "<GREY>"}')
        channel = '#'+(conn.ReceiveStr(bytes(keys,'ascii'),20)).translate({ord(i): None for i in '#@/"'}) #Get channel
    conn.SendTML(f'<CLR><SPINNER><CRSRL>{"<GREY3>" if "PET" in conn.mode else "<GREY>"}')
    reactor = irc.client.Reactor()
    #reactor.server().buffer_class = buffer.LenientDecodingLineBuffer
    irc.client.ServerConnection.buffer_class.errors = "replace"
    try:
        c = reactor.server().connect(server, int(port), nickname)
    except irc.client.ServerConnectionError:
        printchat('<PINK>*** ERROR Connecting to server<BR>')
        conn.Sendall(TT.set_Window(0,scheight-1))
        _LOG(bcolors.FAIL+'Connection to IRC FAILED'+bcolors.ENDC,id=conn.id,v=1)
        time.sleep(2)
        return
    #Add handlers
    c.add_global_handler("welcome", on_connect)
    c.add_global_handler("join", on_join)
    c.add_global_handler("part", on_part)
    c.add_global_handler("disconnect", on_disconnect)
    c.add_global_handler("pubmsg", on_pubmsg)
    c.add_global_handler("nicknameinuse", on_nicknameinuse)
    c.add_global_handler("currenttopic", on_currenttopic)
    c.add_global_handler("topic", on_topic)
    c.add_global_handler("namreply", on_names)
    c.add_global_handler("pubnotice", on_pubnotice)
    #c.add_global_handler("privmsg", on_privmsg)
    c.add_global_handler("action", on_action)
    c.add_global_handler("privnotice", on_privnotice)

    running = False
    t0 = time.process_time()
    while running == False:
        reactor.process_once()
        time.sleep(0.1)
        if time.process_time()-t0 > 60.0:       #Abandon if connection takes more than a minute
            printchat('<PINK>*** TIMEOUT Connecting to server<BR>')
            _LOG(bcolors.FAIL+'Connection to IRC FAILED - TIMEOUT'+bcolors.ENDC,id=conn.id,v=2)
            conn.Sendall(TT.set_Window(0,scheight-1))
            time.sleep(1)
            return
    conn.SendTML('<CLR>')
    printchat('*** Use /help for help ***<BR>')
    conn.socket.setblocking(0)
    _LOG('Connected to IRC',id=conn.id,v=4)
    message = ''
    while running and conn.connected:
        r,w,e= select.select((conn.socket,), (), (), 0)
        if r:
            try:
                i_char = conn.socket.recv(1)
                if i_char == b'\r' and message != '':
                    if message =='_':
                        running = False
                        c.part(channel,'Using-RetroBBS-IRC-plugin')
                        c.quit('Using-RetroBBS-IRC-plugin')
                        continue
                    elif message.startswith('/'):
                        command_parser(c,message)
                        conn.SendTML('<CLR>')
                        message = ''
                        curcolumn = 0
                        curline = 0
                    else:
                        c.privmsg(channel, _dec(message))
                        conn.SendTML('<CLR>')
                        curline = 0
                        curcolumn = 0
                        msg = H.formatX(nickname+': '+_dec(message),scwidth)
                        msg[0] = '<YELLOW>'+msg[0][0:len(nickname)+1]+("<GREY2>" if "PET" in conn.mode else "<GREY>")+msg[0][len(nickname)+1:]
                        printchat(msg)
                        message =''
                elif len(message)<(scwidth*2)-1:
                    if chr(i_char[0]) == conn.encoder.bs:
                        if message != '':
                            message = message[:-1]
                            conn.Sendallbin(i_char)
                            curcolumn -=1
                            if curcolumn < 0:
                               curcolumn = scwidth-1
                               curline = 0
                    elif not (chr(i_char[0]) in kfilter):
                        message += chr(i_char[0])
                        conn.Sendallbin(i_char)
                        curcolumn +=1
                        if curcolumn >= scwidth:
                            curcolumn = 0
                            curline +=1
            except socket.error:
                running = False
                conn.connected = False
        else:
            time.sleep(0.1)
        reactor.process_once()
    conn.Sendall(TT.set_Window(0,scheight-1))            
    _LOG('Leaving IRC',id=conn.id,v=4)
    conn.socket.setblocking(1)
    conn.socket.settimeout(60*5)
