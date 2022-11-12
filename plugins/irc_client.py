import time
import irc.client
import string
import select
import socket

from common.bbsdebug import _LOG,bcolors
import common.helpers as H
import common.style as S
from common.connection import Connection
import common.petscii as P
import common.turbo56k as TT
import common.filetools as FT
from jaraco.stream import buffer


#############################
#Plugin setup
def setup():
    fname = "IRC" #UPPERCASE function name for config.ini
    parpairs = [('server','irc.libera.chat'),('port',6667),('channel','')] #config.ini Parameter pairs (name,defaultvalue)
    return(fname,parpairs)
#############################


##########################################
#Plugin callable function
def plugFunction(conn:Connection,server,port,channel):

    running = False

    kfilter = P.NONPRINTABLE.copy()
    kfilter.append('\r')
    
    nickname = ''

    keys = string.ascii_letters + string.digits + " !?';:[]()*/@+-_,.$%&"

    #Current cursor position in input window
    curcolumn = 0
    curline = 0

    # Send petscii text to the chat window
    def printchat(text):
        conn.Sendall(chr(0)*2+TT.set_Window(3,21)+TT.set_CRSR(0,18))
        if isinstance(text,list):
            for t in text:
                conn.Sendall(t)
                tt = t.translate({ord(c):None for c in P.NONPRINTABLE})#Catches color codes
                if len(tt)<40 and t[-1]!='\r':
                    conn.Sendall('\r')
        else:
            conn.Sendall(text)
        conn.Sendall(TT.set_Window(23,24)+TT.set_CRSR(curcolumn,curline)+chr(P.GREY3))

    def on_currenttopic(c, event):
        txt = H.formatX('['+event.arguments[0]+'] Topic is: '+event.arguments[1])
        txt[0] = chr(P.CYAN)+txt[0]
        printchat(txt)

    def on_topic(c, event):
        txt = H.formatX('['+channel+'] Topic changed to: '+event.arguments[0]+'\r')
        txt[0] = chr(P.CYAN)+txt[0]
        printchat(txt)


    def on_nicknameinuse(c, e):
        nonlocal nickname
        printchat(chr(P.CYAN)+nickname+' IN USE\rtRYING '+nickname+'-\r')
        nickname += '-'
        c.nick(P.toASCII(nickname))
        conn.Sendall(chr(P.GREEN)+TT.Fill_Line(22,64)+TT.set_Window(22,22)+chr(P.RVS_ON)+chr(P.CRSR_RIGHT)+nickname)
        conn.Sendall(chr(P.GREY3)+TT.set_Window(23,24)+chr(P.RVS_OFF))

    def on_pubmsg(connection, event):
        user = event.source
        if '!' in user:
            user = user[0:user.index('!')]
        elif '@' in user:
            user = user[0:user.index('@')]
        txt = H.formatX(user+': '+event.arguments[0])
        txt[0]= chr(P.LT_BLUE)+txt[0][0:len(user)+1]+chr(P.GREY2)+txt[0][len(user)+2:]
        printchat(txt)

    def on_action(connection, event):
        user = event.source
        if '!' in user:
            user = user[0:user.index('!')]
        elif '@' in user:
            user = user[0:user.index('@')]
        txt = H.formatX('* '+user+' '+event.arguments[0])
        txt[0]= chr(P.ORANGE)+txt[0][0:len(user)+2]+chr(P.GREY3)+txt[0][len(user)+2:]
        printchat(txt)

    def on_privmsg(connection, event):
        print(event)
    
    def on_privnotice(connection, event):
        txt = H.formatX(chr(P.ORANGE)+P.toPETSCII(event.arguments[0]),convert=False)
        printchat(txt)

    def on_pubnotice(connection, event):
        txt = H.formatX(chr(P.YELLOW)+'>'+P.toPETSCII(event.target)+'<'+P.toPETSCII(event.arguments[0]),convert=False)
        for x in range(len(txt)):
            txt[x] = chr(P.RVS_ON)+txt[x]
        printchat(txt)

    def on_connect(connection, event):
        printchat(chr(P.CYAN)+'cONNECTED TO: '+P.toPETSCII(server)+'\r')
        txt = H.formatX(event.arguments[0])
        txt[0] = chr(P.CYAN)+txt[0]
        printchat(txt)
        if irc.client.is_channel(channel):
            connection.join(channel)
        #main_loop(connection)

    def on_names(connection, event):
        text = H.formatX(chr(P.CYAN)+'uSERS IN '+P.toPETSCII(channel)+': '+chr(P.GREEN)+P.toPETSCII(event.arguments[2]),convert=False)
        printchat(text)

    def on_join(connection, event):
        nonlocal running

        user = P.toPETSCII((event.source.nick if event.source.nick != nickname else '')+' ')
        printchat(chr(P.CYAN)+user+'jOINED '+P.toPETSCII(event.target)+'\r')
        running = True

    def on_part(connection, event):
        print(event)

        user = P.toPETSCII((event.source.nick if event.source.nick != nickname else '')+' ')
        if len(event.arguments) != 0:
            msg = ' ('+P.toPETSCII(event.arguments[0])+')'
        else:
            msg = ''
        printchat(chr(P.CYAN)+user+'lEFT '+P.toPETSCII(event.target)+msg+'\r')

    def on_disconnect(connection, event):
        nonlocal running

        printchat(chr(P.YELLOW)+'dISCONNECTED...\r')
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
    <Left Arrow> - Exit chat
    /quit - Exit chat
    /nick nickname - Change nickname
    /join channel - Join channel 
                    (Parts current)
    /names - List users in channel
    /me action - Send action to the 
                 channel
----------------------------------------"""
            printchat(H.formatX(hstring))
        elif text.lower() == '/quit':
            running = False
            connection.part(['Using RetroBBS IRC plugin'])
            connection.quit('Using-RetroBBS-IRC-plugin')
            return
        elif text.lower().startswith('/nick'):
            pars = text.split(' ')
            if len(pars)>1:
                nickname = pars[1].translate({ord(i): None for i in '#?!@/()&$"'})
                c.nick(P.toASCII(nickname))
                conn.Sendall(chr(P.GREEN)+TT.Fill_Line(22,64)+TT.set_Window(22,22)+chr(P.RVS_ON)+chr(P.CRSR_RIGHT)+nickname)
                conn.Sendall(chr(P.GREY3)+TT.set_Window(23,24)+chr(P.RVS_OFF)+TT.set_CRSR(curcolumn,curline))
            else:
                printchat('uSAGE: nick <NICK>, CHANGE YOUR NICK\r')
        elif text.lower().startswith('/join'):
            pars = text.split(' ')
            if len(pars)>1:
                oldchan = channel
                channel = P.toASCII(pars[1].translate({ord(i): None for i in '@/"'}))
                if channel[0] != '#':
                    channel = '#'+channel
                connection.part(oldchan,':Using-RetroBBS-IRC-plugin')
                #connection.send_raw('PART '+oldchan+' :Using-RetroBBS-IRC-plugin')
                connection.join(channel)
            else:
                printchat('uSAGE: join <CHANNEL> JOIN A NEW CHANNEL') #40 characters<<<<<
        elif text.lower().startswith('/names'):
            connection.names(channel)
        elif text.lower().startswith('/me'):
            pars = text.split(' ')
            if len(pars)>1:
                connection.action(channel,P.toASCII(' '.join(pars[1:])))
                msg = H.formatX(nickname+' '+(' '.join(pars[1:])),convert=False)
                msg[0] = chr(P.YELLOW)+msg[0]
                printchat(msg)
            else:
                printchat(H.formatX('Usage: ME <action> send action (written in 3rd person) to the channel'))


    ####
    S.RenderMenuTitle(conn,'IRC')
    conn.Sendall(chr(P.GREEN)+TT.Fill_Line(22,64))
    if conn.userclass > 0:
        nickname = P.toPETSCII(conn.username[0:9])
    else:
        conn.Sendall(TT.set_Window(23,24)+chr(P.YELLOW)+'eNTER NICK: '+chr(P.GREY3))
        nickname = conn.ReceiveStr(bytes(keys,'ascii'), 9) #Get nick
    nickname = nickname.translate({ord(i): None for i in '#?!@/()&$"'})
    conn.Sendall(TT.set_Window(0,24))
    if nickname == '':
        time.sleep(0.5)
        return
    conn.Sendall(TT.set_CRSR(1,22)+chr(P.RVS_ON)+chr(P.GREEN)+nickname+'\r')
    conn.Sendall(TT.set_Window(23,24)+chr(P.CLEAR))
    if channel == '':
        conn.Sendall(chr(P.YELLOW)+'eNTER CHANNEL: #'+chr(P.GREY3))
        channel = '#'+(conn.ReceiveStr(bytes(keys,'ascii'),20)).translate({ord(i): None for i in '#@/"'}) #Get channel
    conn.Sendall(chr(P.CLEAR)+chr(P.COMM_B)+chr(P.CRSR_LEFT)+chr(P.GREY3))

    reactor = irc.client.Reactor()
    #reactor.server().buffer_class = buffer.LenientDecodingLineBuffer
    irc.client.ServerConnection.buffer_class.errors = "replace"
    try:
        c = reactor.server().connect(server, int(port), P.toASCII(nickname))
    except irc.client.ServerConnectionError:
        printchat(chr(P.PINK)+'*** error cONNECTING TO SERVER ***\r')
        conn.Sendall(TT.set_Window(0,24))
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
            printchat(chr(P.PINK)+'*** timeout cONNECTING TO SERVER ***\r')
            _LOG(bcolors.FAIL+'Connection to IRC FAILED - TIMEOUT'+bcolors.ENDC,id=conn.id,v=2)
            conn.Sendall(TT.set_Window(0,24))
            time.sleep(1)
            return

    conn.Sendall(chr(P.CLEAR))

    printchat('*** uSE /HELP FOR HELP ***\r')

    conn.socket.setblocking(0)
    _LOG('Connected to IRC',id=conn.id,v=4)
    message = ''
    while running and conn.connected:
        r,w,e= select.select((conn.socket,), (), (), 0)
        if r:
            try:
                #conn.socket.setblocking(0)
                i_char = conn.socket.recv(1)
                if i_char == b'\r' and message != '':
                    if message =='_':
                        running = False
                        c.part(channel,'Using-RetroBBS-IRC-plugin')
                        c.quit('Using-RetroBBS-IRC-plugin')
                        continue
                    elif message.startswith('/'):
                        command_parser(c,message)
                        conn.Sendall(chr(P.CLEAR))
                        message = ''
                        curcolumn = 0
                        curline = 0
                    else:
                        c.privmsg(channel, P.toASCII(message))
                        conn.Sendall(chr(P.CLEAR))
                        curline = 0
                        curcolumn = 0
                        msg = H.formatX(nickname+': '+message,convert=False)
                        msg[0] = chr(P.YELLOW)+msg[0][0:len(nickname)+1]+chr(P.GREY2)+msg[0][len(nickname)+2:]
                        printchat(msg)
                        message =''
                elif len(message)<79:
                    if chr(i_char[0]) == chr(P.DELETE):
                        if message != '':
                            message = message[:-1]
                            conn.Sendallbin(i_char)
                            curcolumn -=1
                            if curcolumn < 0:
                               curcolumn = 39
                               curline = 0
                    elif not (chr(i_char[0]) in kfilter):
                        message += chr(i_char[0])
                        conn.Sendallbin(i_char)
                        curcolumn +=1
                        if curcolumn >= 40:
                            curcolumn = 0
                            curline +=1
                #conn.socket.setblocking(1)
            except socket.error:
                running = False
                conn.connected = False
        else:
            time.sleep(0.1)
        reactor.process_once()


    conn.Sendall(TT.set_Window(0,24))            
    _LOG('Leaving IRC',id=conn.id,v=4)
    conn.socket.setblocking(1)
    conn.socket.settimeout(60*5)
#################