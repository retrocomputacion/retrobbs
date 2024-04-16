# Messaging sub-system
from common.connection import Connection
from datetime import datetime
from common import turbo56k as TT
from common.bbsdebug import _LOG
from common.style import RenderMenuTitle
from common.dbase import DBase
from common.helpers import formatX, crop
from tinydb import Query
from tinydb.table import Document
import time
import string
import difflib

###########################################
# Message db fields
# msg_id:       automatic from tinydb (doc_id)
# msg_from:     sender user id
# msg_board:    destination board (0 for PM)
# msg_to:       destination user id (only for PM)
# msg_sent:     send timestamp
# msg_read:     list of user ids that have read this msg
# msg_parent:   parent message (which this msg is replying to), 0 for first message
# msg_next:     next message in thread or 0 if none
# msg_prev:     prev message in thread, if first message in thread this points to the last one
# msg_topic:    message topic
# msg_text:     message text
###########################################

##############################################
# Read a message
##############################################
def readMessage(conn:Connection, msg_id:int):
    scwidth,scheight = conn.encoder.txt_geo
    if 'MSX' in conn.mode:
        hcode = 0x17
    else:
        hcode = 0x40
    db:DBase = conn.bbs.database
    table = db.db.table('MESSAGES')
    dbQ = Query()
    done = False
    while not done and conn.connected:
        dmsg = table.get(doc_id = msg_id)
        if dmsg != None:
            utable = db.db.table('USERS')
            if type(dmsg['msg_from'])==int:
                user = utable.get(doc_id = dmsg['msg_from'])
            else:
                user = dmsg['msg_from']
            # build option string
            ol = []
            keys = b'_'
            if conn.userclass == 10:    #Admin reading
                keys += b'D'
                adm = ' <RVSON>D<RVSOFF>elete'
            else:
                adm = ''
            if dmsg['msg_parent'] != 0:
                ol.append('<GREY3><RVSON>F<RVSOFF>irst/<RVSON>P<RVSOFF>rev')
                keys += b'FP'
            if (dmsg['msg_next'] != 0) and (dmsg['msg_next'] != msg_id):
                ol.append('<RVSON>N<RVSOFF>ext/<RVSON>L<RVSOFF>ast')
                keys += b'NL'
            if (int(conn.bbs.BoardOptions.get('board'+str(dmsg['msg_board'])+'post',1)) <= conn.userclass):
                if (dmsg['msg_board']!=0) or ((dmsg['msg_board']==0)and(type(dmsg['msg_from'])==int)and(type(dmsg['msg_to'])==int)):
                    ol.append('<RVSON>R<RVSOFF>eply')
                    keys += b'R'

            conn.SendTML(f'<WINDOW top=0 bottom={scheight}><CLR><GREEN>{dmsg["msg_topic"]}<GREY2><BR>'
                         f'by:<LTGREEN>{"*"+user if type(user)==str else " "+user["uname"]}')
            if conn.bbs.dateformat == 1:
                datestr = "%m/%d/%Y"
            elif conn.bbs.dateformat == 2:
                datestr = "%Y/%m/%d"
            else:
                datestr = "%d/%m/%Y"
            if dmsg['msg_board'] == 0:  # private message, display recipient
                if type(dmsg['msg_to'])==int:
                    rcp = utable.get(doc_id = dmsg['msg_to'])
                else:
                    rcp = dmsg['msg_to']
                conn.SendTML(f'<AT x={scwidth//2} y=1><GREY3><RVSON>to:<LTGREEN>{"*"+rcp if type(rcp)==str else " "+rcp["uname"]}<RVSOFF>')
            else:   # public message, display post date
                conn.SendTML(f'<AT x={scwidth//2} y=1><GREY3><RVSON>on:<LTGREEN>{datetime.utcfromtimestamp(dmsg["msg_sent"]):{datestr}}<RVSOFF>')
            conn.SendTML(f'{f"<YELLOW><LFILL row=2 code={hcode}><LFILL row={scheight-3} code={hcode}>" if conn.QueryFeature(TT.LINE_FILL)<0x80 else f"<AT x=0 y=2><YELLOW><HLINE n={scwidth}><AT x=0 y={scheight-3}><HLINE n={scwidth}>"}'
                         f'<AT x=0 y={scheight-2}><GREY3>')
            for i,o in enumerate(ol):
                conn.SendTML(o)
                if (i+1) < len(ol):
                    conn.Sendall('/')
            conn.SendTML(f'<BR><BACK> Exit{adm}<AT x=0 y=3><GREY3>')
            msg = formatX(dmsg['msg_text'],scwidth)
            # display message
            for i,l in enumerate(msg):
                conn.SendTML(l)
            conn.Sendall(TT.disable_CRSR())
            # mark it as read if needed
            if conn.userid != 0:
                if conn.userid not in dmsg['msg_read']:
                    dmsg['msg_read'].append(conn.userid)
                    table.upsert(Document({'msg_read':dmsg['msg_read']},doc_id=msg_id))
            while conn.connected:
                k = conn.ReceiveKey(keys)
                if k == b'_':
                    done = True
                    break
                elif k == b'F':
                    msg_id = dmsg['msg_parent']
                    break
                elif k == b'P':
                    msg_id = dmsg['msg_prev']
                    break
                elif k == b'N':
                    msg_id = dmsg['msg_next']
                    break
                elif k == b'L':
                    if dmsg['msg_parent'] != 0:
                        msg_id = table.get(doc_id = dmsg['msg_parent'])['msg_prev']
                    else:
                        msg_id = dmsg['msg_prev']
                    break
                elif k == b'R':
                    if dmsg['msg_board'] == 0:
                        uid = dmsg['msg_from'] if dmsg['msg_from'] != conn.userid else dmsg['msg_to']
                        dest = utable.get(doc_id=uid)['uname']
                    else:
                        dest = dmsg['msg_board']
                    conn.Sendall(TT.enable_CRSR())
                    r_id = writeMessage(conn, destination = dest, thread = (dmsg['msg_parent'] if dmsg['msg_parent']!=0 else msg_id))
                    if r_id != 0:
                        msg_id = r_id
                    break
                elif k == b'D': #Delete:
                    conn.SendTML(f'<RED>{f"<LFILL row=10 code={hcode}><LFILL row=14 code={hcode}>"if conn.QueryFeature(TT.LINE_FILL)<0x80 else f"<AT x=0 y=10><HLINE n={scwidth}><AT x=0 y=14><HLINE n={scwidth}>"}'
                                 f'<WINDOW top=11 bottom=13>'
                                 f'<CLR><CRSRD><WHITE>          Delete message?(Y/N)')
                    if conn.ReceiveKey(b'YN') == b'Y':
                        if dmsg['msg_parent'] == 0: #delete whole thread
                            deleteThread(conn,msg_id)
                            done = True
                            break
                        else:
                            msg_id = deleteMessage(conn,msg_id)
                            break
                    break
        else:
            _LOG('readMessage: ERROR - Invalid message',id=conn.id,v=1)
            conn.SendTML('ERROR - Invalid message<PAUSE n=1>')
            done = True

####################################################################
# Write a message
# destination = int for a public board
#               string for username PM
# thread = message id for this thread, 0 for new thread
# returns msg_id or 0 if unsuccessful
####################################################################
def writeMessage(conn:Connection, destination = 1, thread:int = 0):

    _dec = conn.encoder.decode
    _enc = conn.encoder.encode


    # Editor
    def composer(message = list(['']*18), topic:str = ''):
    
        def dialog1(): # Send or cancel message
            nonlocal message
            conn.Sendall(TT.set_Window(scheight-2,scheight-1))
            ond = True
            while ond:
                conn.SendTML('<CLR>Send/Edit/Quit(S/E/Q)?')
                k = conn.ReceiveKey(b'SEQ')
                if k == b'S':
                    if sum(len(l) for l in message) == 0:
                        conn.SendTML('<BR>EMPTY MESSAGE<PAUSE n=1.5>')
                    else:
                        ond = False
                else:
                    ond = False
            return(k)
        
        def dispMsg(): # Display message
            nonlocal message
            conn.SendTML(f'<WINDOW top=3 bottom={scheight-4}><GREY3><CLR>')
            for l in message:
                conn.Sendall(l)
                if len(l)<scwidth:
                    conn.SendTML('<BR>')

        def hl_line():  # Highlight selected line
            nonlocal message, line
            conn.SendTML(f'<AT x=0 y={line}><WHITE>')
            if (len(message[line]) == 0) or (message[line][0] == ' '):
                conn.Sendall('>')
            else:
                conn.SendTML(f'<RVSON>{_dec(message[line][0])}<RVSOFF>')
            conn.SendTML(f'<WINDOW top={scheight-3} bottom={scheight-3}><AT x=32 y=0><RVSON><YELLOW>{line+1:0>2}/18<RVSOFF><GREY3>')

        scwidth,scheight = conn.encoder.txt_geo
        if 'MSX' in conn.mode:
            hcode = 0x17
        else:
            hcode = 0x40
        vfilter = bytes(string.ascii_letters + string.digits + " !?';:[]()*/@+-_,.$%&=<>#\\^" + chr(34),'ascii')    #Valid input characters
        ckeys = conn.encoder.ctrlkeys
        if conn.mode == 'PET64':
            help_k = [ckeys['F1'],'F1']
            line_k = [ckeys['F7'],'F7']
            quit_k = [ckeys['F8'],'F8']
        elif conn.mode == "PET264":
            help_k = [ckeys['HELP'],'HELP']
            line_k = [ckeys['F3'],'F3']
            quit_k = [ckeys['ESC'],'ESC']
        else: #MSX
            help_k = [ckeys['F1'],'F1']
            line_k = [ckeys['F5'],'F5']
            quit_k = [ckeys['F10'],'F10']
        conn.SendTML(f'<SETOUTPUT><NUL n=2><TEXT border={conn.style.BoColor} background={conn.style.BgColor}><MTITLE t="Message Editor"><YELLOW>'
                     f'{f"<LFILL row={scheight-3} code={hcode}>"if conn.QueryFeature(TT.LINE_FILL)<0x80 else f"<AT x=0 y={scheight-3}><HLINE n={scwidth}>"}'
                     f'<AT x=1 y={scheight-3}><RVSON>{help_k[1]} for help<RVSOFF>')
        dispMsg()
        line = 0
        column = 0
        hl_line()
        conn.SendTML(f'<PAUSE n=1><WINDOW top={scheight-2} bottom={scheight-1}><GREY3>')
        while topic == '': # Get message topic if none provided
            conn.SendTML('Topic title:<BR>')
            topic = conn.ReceiveStr(vfilter, maxlen = 32)
            conn.SendTML('<PAUSE n=0.5><CLR>')
            topic = _dec(topic)
        _LOG('Composing message',id=conn.id,v=4)
        running = True
        edit = True
        while running and conn.connected:
            try:
                i_char = conn.ReceiveKey(vfilter+bytes([0x0d,ckeys['CRSRD'],ckeys['HOME'],ckeys['DELETE'],ckeys['CRSRR'],help_k[0],line_k[0],quit_k[0],ckeys['CRSRU'],ckeys['CLEAR'],ckeys['INSERT'],ckeys['CRSRL']])) #conn.socket.recv(1) #b'\r\x11\x13\x14\x1d\x85\x88\x8c\x91\x93\x94\x9d'
                if edit :   # Editing text
                    if i_char == b'\r':
                        tline = ' ' if len (message[line]) == 0 else message[line]
                        if conn.QueryFeature(TT.LINE_FILL):
                            conn.Sendall(TT.Fill_Line(line+3,32))
                        else:
                            conn.Sendall(TT.set_CRSR(0,line+3)+(' '*scwidth))
                        conn.SendTML(f'<WINDOW top=3 bottom={scheight-4}><AT x=0 y={line}>{_dec(tline)}')
                        if line < 17:
                            line += 1
                            column = 0
                            hl_line()
                            conn.SendTML(f'<WINDOW top={scheight-2} bottom={scheight-1}><CLR>{_dec(message[line])}<HOME>')
                        else:   # Past last line
                            option = dialog1()
                            if option == b'S':      # Send message
                                running = False
                            elif option == b'Q':    # Abort editor
                                running = False
                                message = None
                            else:                   # Keep editing
                                conn.SendTML(f'<CLR>Select LINE (CRSR UP/DWN)<WINDOW top=3 bottom={scheight-4}><AT x=0 y={line}>')
                                edit = False
                    elif (ord(i_char) == ckeys['CRSRR']) and (column < len(message[line])):   # Cursor right
                        column += 1
                        conn.Sendallbin(i_char)
                    elif (ord(i_char) == ckeys['CRSRL']) and (column > 0):                     # Cursor left
                        column -= 1
                        conn.Sendallbin(i_char)
                    elif ord(i_char) == ckeys['HOME']:                                             # Cursor home
                        column = 0
                        conn.Sendallbin(i_char)
                    elif ord(i_char) == ckeys['CLEAR']:                                            # Clear line
                        column = 0
                        message[line] = ''
                        conn.Sendallbin(i_char)
                    elif (ord(i_char) == ckeys['DELETE']) and (len(message[line]) > 0) and (column > 0):   # Delete caracter
                        message[line] = message[line][0:column-1] + message[line][column:]
                        column -= 1
                        conn.Sendallbin(i_char)
                    elif (ord(i_char) == ckeys['INSERT']) and (scwidth > len(message[line]) > 0) and (column < len(message[line])):   # Insert blank space
                        message[line] = message[line][0:column] + ' ' + message[line][column:]
                        conn.Sendallbin(i_char)
                    elif ord(i_char) == quit_k[0]:                                               # Finish editing
                        if conn.QueryFeature(TT.LINE_FILL):
                            conn.Sendall(TT.Fill_Line(line+3,32))
                        else:
                            conn.Sendall(TT.set_CRSR(0,line+3)+(' '*scwidth))
                        conn.SendTML(f'<WINDOW top=3 bottom={scheight-4}><AT x=0 y={line}>{_dec(message[line])}') # Clear line in display window, print newly edited line
                        option = dialog1()
                        if option == b'S':      # Send message
                            running = False
                        elif option == b'Q':    # Abort editor
                            running = False
                            message = None
                        else:                   # Keep editing
                            conn.SendTML(f'<CLR>Select LINE (CRSR UP/DWN)<WINDOW top=3 bottom={scheight-4}><AT x=0 y={line}>')
                            edit = False
                    elif ord(i_char) == line_k[0]:   # Select line to edit
                        tline = ' ' if len (message[line]) == 0 else message[line]
                        if conn.QueryFeature(TT.LINE_FILL):
                            conn.Sendall(TT.Fill_Line(line+3,32))
                        else:
                            conn.Sendall(TT.set_CRSR(0,line+3)+(' '*scwidth))
                        conn.SendTML(f'<WINDOW top=3 bottom={scheight-4}><AT x=0 y={line}>{_dec(message[line])}'
                                     f'<WINDOW top={scheight-2} bottom={scheight-1}><CLR>Select LINE (CRSR UP/DWN)<WINDOW top=3 bottom={scheight-4}><AT x=0 y={line}>')
                        edit = False
                    elif ord(i_char) == help_k[0]:   # Display help screen
                        conn.SendTML(f'<WINDOW top=3 bottom={scheight-4}><CLR>'
                                     '<YELLOW><BR>     ---Line editor instructions---<BR>'
                                     '<BR>This editor allows you to type and edit a single line at a time.<BR>'
                                     'INS/DEL and CLR/HOME are supported<BR>'
                                     f'Press RETURN to accept a line<BR>{line_k[1]} to select a new line<BR>{quit_k[1]} to send/abort message<BR>'
                                     '<BR>Press any key to continue...')
                        conn.Receive(1)
                        dispMsg()
                        conn.SendTML(f'<WINDOW top={scheight-2} bottom={scheight-1}><CLR>Select line (CRSR UP/DWN)<WINDOW top=3 bottom={scheight-4}><AT x=0 y={line}>')
                        edit = False
                    elif ord(i_char) in vfilter:
                        # Alphanumeric characters
                        column += 1
                        if column <= len(message[line]):
                            message[line] = message[line][0:column-1] + chr(ord(i_char)) + message[line][column:]
                            #message[line][column-1] = chr(ord(i_char))
                        else:
                            message[line] += chr(ord(i_char))
                        conn.Sendallbin(i_char)
                        if column == scwidth:
                            if conn.QueryFeature(TT.LINE_FILL):
                                conn.Sendall(TT.Fill_Line(line+3,32))
                            else:
                                conn.SendTML(f'<AT x=0 y={line+3}><SPC n={scwidth}>')
                            conn.SendTML(f'<WINDOW top=3 bottom={scheight-4}><AT x=0 y={line}>{_dec(message[line])}') # Clear line in display window, print newly edited line
                            if line < 17:
                                line += 1
                                column = 0
                            conn.SendTML(f'<PAUSE n=0.5><WINDOW top={scheight-2} bottom={scheight-1}><CLR>{_dec(message[line])}<HOME>')  # Update edit window
                else:   # Selecting line to edit
                    if (ord(i_char) == ckeys['CRSRD']) and (line < 17):
                        line += 1
                        conn.Sendallbin(i_char)
                    elif (ord(i_char) == ckeys['CRSRU']) and (line > 0):
                        line -= 1
                        conn.Sendallbin(i_char)
                    elif i_char == b'\r':
                        edit = True
                        column = 0
                        hl_line()
                        conn.SendTML(f'<WINDOW top={scheight-2} bottom={scheight-1}><CLR>{_dec(message[line])}<HOME>')  # Update edit window
            except Exception as e:
                running = False
                conn.connected = False
        conn.Sendall(TT.set_Window(0,scheight))
        return(topic,message)
    #check user is logged in
    if conn.username == '_guest_':
        return
    #check destination
    db = conn.bbs.database
    table = db.db.table('MESSAGES')
    dbQ = Query()
    # thread exist?
    dthread = None
    topic = ''
    m_id = 0
    if thread != 0:
        dthread = table.get(doc_id = thread)
        if  dthread == None:
            conn.SendTML('ERROR:Invalid thread')
            _LOG('Messaging: ERROR - Invalid thread',id=conn.id)
            return
        else: 
            topic = dthread['msg_topic']
    if type(destination) == str:    # Private message
        # user exist?
        duser = db.chkUser(destination)
        if duser != None:
            user = duser.doc_id
            board = 0
        else:
            conn.SendTML('ERROR:Invalid user')
            _LOG('Messaging: ERROR - Invalid user',id=conn.id)
            return
    else:   # Board message
        user = 0
        board = destination
    # Note - fixme: You can get to this point even if the thread doesnt belong to the destination board
    topic, message = composer(topic=topic)  ###### Test composer
    if message != None:
        i = 0
        while (sum(len(c) for c in message[i:])) > 0:
            i += 1
        msgtxt = _dec('\n'.join(l for l in message[:i]))
        # insert message
        m_id = table.insert({'msg_from':conn.userid, 'msg_to':user, 'msg_sent':time.time(), 'msg_read':[conn.userid], 'msg_parent':thread,
                'msg_next':0, 'msg_topic':topic, 'msg_text':msgtxt, 'msg_board':board})
        if thread != 0:
            prev = dthread['msg_prev']
            table.upsert(Document({'msg_prev':m_id}, doc_id = thread))  # Update thread's last message
            table.upsert(Document({'msg_next':m_id}, doc_id = prev))  # Update previous message
        else: # new thread
            prev = m_id
        table.upsert(Document({'msg_prev':prev}, doc_id=m_id))  # Update last message's previous/last message
        # Note - update() wont work with doc_id and will update all entries in table. Use upsert()
        # Note2 - update() uses doc_ids instead, but Im too lazy to change all the upsert() now ;)
        _LOG('Messaging: Message sent',id=conn.id,v=4)
        conn.SendTML('<CLR><LTGREEN>Message sent')
    else:
        _LOG('Messaging: Message cancelled',id=conn.id,v=4)
    return m_id

############################################################
# Display user private messages (board = 0) or public board
############################################################
def inbox(conn:Connection, board):
    scwidth,scheight = conn.encoder.txt_geo
    ellipsis = conn.encoder.ellipsis
    if 'MSX' in conn.mode:
        hcode = 0x17
    else:
        hcode = 0x40
    _dec = conn.encoder.decode
    keys = string.ascii_letters + string.digits + ' +-_,.$%&'
    ckeys = conn.encoder.ctrlkeys
    db:DBase = conn.bbs.database
    conn.SendTML('<SETOUTPUT><NUL n=2><TEXT border={conn.style.BoColor} background={conn.style.BgColor}>')
    query = {'msg_board':board,'msg_parent':0}
    q2 = query.copy()
    if board == 0:
        if conn.username != '_guest_':
            title = "Private messages"
            query['msg_to'] = conn.userid   # Threads directed to user
            q2['msg_from'] = conn.userid    # Threads started by user
        else:
            return  #abort if not logged in
    else:
        title = conn.bbs.BoardOptions.get('board'+str(board),'bOARD '+str(board))  # Replace with board title from config.ini
    table = db.db.table('MESSAGES')
    dbQ = Query()
    page = 0
    done = False
    refresh = True
    utable = db.db.table('USERS')
    while not done and conn.connected:
        # display thread list
        msgs = table.search(dbQ.fragment(query)|dbQ.fragment(q2))
        threads = []
        for i in msgs:
            um = getUnread(conn,i.doc_id)
            if um == None:
                tt = f' <GREY1><UR-QUAD>{"<LTBLUE>" if i["msg_from"] == conn.userid else "<GREEN>"} '
            else:
                tt = f' <GREEN><UR-QUAD>{"<CYAN>" if i["msg_to"] == conn.userid else "<LTGREEN>"} '
            to = crop(i['msg_topic'],24,ellipsis)
            tl = table.get(doc_id=i['msg_prev'])
            if type(tl['msg_from'])==int:
                user = utable.get(doc_id = tl['msg_from'])['uname']
            else:
                user = tl['msg_from']
            tu = crop(user,11,ellipsis)
            tt += f'{to}<YELLOW><CRSRR n={24-len(to)}<VLINE><WHITE>{tu}'
            ts = tl['msg_sent']    # Get timestamp of last message in thread
            threads.append([tt,i.doc_id,um,ts])  #topic - thread_id, first unread, timestamp
        # sort by sent timestamp, newest thread first
        threads.sort(key=lambda threads: threads[3],reverse=True)
        conn.Sendall(TT.enable_CRSR())
        if refresh:
            conn.Sendall(TT.set_Window(0,scheight))
            RenderMenuTitle(conn,title)
            if int(conn.bbs.BoardOptions.get('board'+str(board)+'post',1)) <= conn.userclass:
                tt = f'<RVSON>n<RVSOFF>ew {"thread" if board != 0 else "message"}{"<BR>" if conn.userclass < 10 else "-<RVSON>d<RVSOFF>elete"}'
            else:
                tt = '<BR>' #'\r'
            if conn.QueryFeature(TT.LINE_FILL) < 0x80:
                tt += f'<YELLOW><LFILL row={scheight-3} code={hcode}>'
            else:
                tt += f'<AT x=0 y={scheight-3}><YELLOW><HLINE n={scwidth}>'
            conn.SendTML(f'<AT x=0 y={scheight-2}><GREY3>Navigate with <RVSON>crsr<RVSOFF> - '+ tt +
                         f'<AT x=0 y={scheight-1}>Read <RVSON>f<RVSOFF>irst/<RVSON>l<RVSOFF>ast or <RVSON>u<RVSOFF>nread msg'
                         f'<WINDOW top=3 bottom={scheight-4}>')
            refresh = False
        conn.SendTML('<CLR>')
        last = len(threads) if len(threads) < (19*(page+1)) else 19*(page+1)
        for i in range(19*page,last):
            conn.SendTML(threads[i][0])
            if i < last-1:
                conn.SendTML('<BR>')
        conn.SendTML('<CURSOR enable=False><CYAN>')
        pos = 0
        o_pos = 1
        while conn.connected:
            if pos != o_pos:
                conn.Sendall(TT.set_CRSR(0,pos)+'>')
                o_pos = pos
            k = conn.ReceiveKey(bytes([ckeys['CRSRD'],ckeys['CRSRU'],ckeys['CRSRL'],ckeys['CRSRR']]) + bytes('FLU_'+('N'if tt!='' else '')+('D'if conn.userclass == 10 else ''),'utf_8'))
            if len(threads) > 0:
                if ord(k) == ckeys['CRSRD']:
                    if pos+1 < (len(threads)-(19*page)):    # move down
                        if pos < 18:
                            pos += 1
                            conn.SendTML('<CRSRL> ')
                        elif len(threads)>(19*(page+1)):
                            page +=1
                            break
                elif ord(k) == ckeys['CRSRU']:                   # move up
                    if pos > 0:
                        pos -= 1
                        conn.SendTML('<CRSRL> ')
                    elif page > 0:
                        page -= 1
                        break
                elif ord(k) == ckeys['CRSRR']:                 # next page
                    if len(threads)>(19*(page+1)):
                        page +=1
                        break
                elif ord(k) == ckeys['CRSRL']:                # previous page
                    if page > 0:
                        page -= 1
                        break
                elif k == b'F':                  # First message
                    conn.Sendall(TT.enable_CRSR()+TT.set_Window(0,scheight))
                    readMessage(conn,threads[pos+(19*page)][1])
                    refresh = True
                    break
                elif k == b'L':                  # Last message
                    m = table.get(doc_id=threads[pos+(19*page)][1])
                    conn.Sendall(TT.enable_CRSR()+TT.set_Window(0,scheight))
                    readMessage(conn,m['msg_prev'])
                    refresh = True
                    break
                elif k == b'U':                  # First unread message
                    if threads[pos+(19*page)][2] != None:
                        conn.Sendall(TT.enable_CRSR()+TT.set_Window(0,scheight))
                        readMessage(conn,threads[pos+(19*page)][2].doc_id)
                        refresh = True
                        break
                elif k == b'D':                 # Delete thread
                    tml = ''
                    if conn.QueryFeature(TT.LINE_FILL) < 0x80:
                        tml += f'<RED><LFILL row=10 code={hcode}><LFILL row=14 code={hcode}>'
                    else:
                        tml += f'<RED><AT x=0 y=10><HLINE n={scwidth}><AT x=0 y=14><HLINE n={scwidth}>'
                    conn.SendTML(tml+'<WINDOW top=11 bottom=13><CLR><CRSRD><WHITE>           Delete thread?(Y/N)')
                    if conn.ReceiveKey(b'YN') == b'Y':
                        deleteThread(conn,threads[pos+(19*page)][1])
                    refresh = True
                    break
            if k == b'N':              # new thread
                conn.Sendall(TT.enable_CRSR())
                if board == 0:
                    # get destination username
                    tml = ''
                    if conn.QueryFeature(TT.LINE_FILL) < 0x80:
                        tml += f'<LFILL row=10 code={hcode}><LFILL row=14 code={hcode}>'
                    else:
                        tml += f'<AT x=0 y=10><HLINE n={scwidth}><AT x=0 y=14><HLINE n={scwidth}>'
                    conn.SendTML(tml+'<WINDOW top=11 bottom=13>')
                    while conn.connected:
                        conn.SendTML('<CLR>Send PM to: ')
                        dest = _dec(conn.ReceiveStr(bytes(keys,'ascii'), 16, False))
                        if (dest != '') and (dest != conn.username):
                            if db.chkUser(dest) == None:
                                # search for closest username
                                users = db.getUsers()
                                match = None
                                mr = 0
                                for u in users:
                                    ratio = difflib.SequenceMatcher(None,u[1],dest).ratio()
                                    if (ratio == 1) and (u[1] != conn.username):
                                        match = u[1]
                                        break
                                    elif (ratio > mr) and (u[1] != conn.username):
                                        match = u[1]
                                        mr = ratio
                                if match != None:
                                    conn.SendTML(f'<BR>Do you mean: {match} ?(Y/N)')
                                    if conn.ReceiveKey(b'YN') == b'Y':
                                        dest = match
                                        break
                            else:
                                break
                        elif dest == '':
                            break
                else:
                    dest = board
                conn.Sendall(TT.set_Window(0,scheight))
                if dest != '':
                    writeMessage(conn, destination=dest)
                refresh = True
                break
            if k == b'_':
                conn.Sendall(TT.enable_CRSR()+TT.set_Window(0,scheight))
                done = True
                break

##############################################
# Toggle the read status of a private message
##############################################
def toggleRead(conn:Connection, msg_id):
    ...

##################################
# Get number of unread messages
##################################
def unreadCount(conn:Connection):
    table = conn.bbs.database.db.table('MESSAGES')
    dbQ = Query()
    tt = table.search(dbQ.msg_board!=0)
    count = [0,0]
    if tt != None:
        for m in tt:
            if conn.userid not in m['msg_read']:
                count[0] += 1
    tt = table.search(dbQ.fragment({'msg_board':0,'msg_to':conn.userid}))
    if tt != None:
        for m in tt:
            if conn.userid not in m['msg_read']:
                count[1] += 1
    return count

#############################################
# Get first unread message in a given thread
#############################################
def getUnread(conn:Connection, thread:int):
    table = conn.bbs.database.db.table('MESSAGES')
    tt = table.get(doc_id=thread)
    res = None
    if tt != None:
        while conn.connected:
            if conn.userid not in tt['msg_read']:
                res = tt
                break
            elif tt['msg_next'] != 0:
                tt = table.get(doc_id=tt['msg_next'])
                if tt == None:
                    _LOG('Messaging: ERROR-broken thread link',id=conn.id)
                    break
            else:
                break
    else:
        _LOG('Messaging: ERROR-invalid thread',id=conn.id)
    return res

############################################
# Delete thread
# Limited to admin users
############################################
def deleteThread(conn:Connection,thread=0):
    if thread != 0 and conn.userclass == 10:
        table = conn.bbs.database.db.table('MESSAGES')
        dbQ = Query()
        if table.contains(doc_id=thread):
            msgs = table.search(dbQ.msg_parent == thread)
            if msgs != None:
                for m in msgs:
                    table.remove(doc_ids=[m.doc_id])
            table.remove(doc_ids=[thread])
            _LOG('Thread id:'+str(thread)+' DELETED',id=conn.id,v=3)
        else:
            _LOG("ERROR: thread id:"+str(thread)+' not found',id=conn.id)
    else:
        _LOG("ERROR: deleteThread - invalid thread or user class")

##########################################
# Delete message
# Limited to admin users
##########################################
def deleteMessage(conn:Connection,msg=0):
    m_id = 0
    if msg != 0 and conn.userclass == 10:
        table = conn.bbs.database.db.table('MESSAGES')
        dmsg = table.get(doc_id = msg)
        if dmsg != None:
            if dmsg['msg_parent'] == 0: #This is the first post in the thread, delete whole thread
                deleteThread(conn,msg)
            else:
                m_id = dmsg['msg_prev']
                next = dmsg['msg_next']
                # Update links
                table.upsert(Document({'msg_next':next},doc_id=m_id))
                if next != 0:
                    table.upsert(Document({'msg_prev':m_id},doc_id=next))
                else:   # Deleting last message in thread
                    if m_id != dmsg['msg_parent']:
                        table.upsert(Document({'msg_prev':m_id},doc_id=dmsg['msg_parent']))
                    else:
                        table.upsert(Document({'msg_prev':dmsg['msg_parent']},doc_id=dmsg['msg_parent']))
                table.remove(doc_ids= [msg])
                _LOG('Message id:'+str(msg)+' DELETED',id=conn.id,v=3)
        else:
            _LOG('ERROR: Message not found', id=conn.id)
    else:
        _LOG('ERROR: Delete Message - Invalid message or user class')
    return m_id # Return the previous message


###########
# TML tags
###########
t_mono = {'UNREAD':(lambda c:unreadCount(c),[('_R','_A'),('c','_C')])}
