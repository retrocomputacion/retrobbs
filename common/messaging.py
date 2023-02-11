# Messaging sub-system
from pydoc import doc
from common.connection import Connection
from datetime import datetime
import common.turbo56k as TT
import common.petscii as P
from common.bbsdebug import _LOG
from common.style import RenderMenuTitle
from common.dbase import DBase
from common.helpers import formatX, crop
from tinydb import Query
from tinydb.table import Document
from tinydb.operations import increment
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

#Read a message
def readMessage(conn:Connection, msg_id:int):
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
                adm = ' '+chr(P.RVS_ON)+'d'+chr(P.RVS_OFF)+'ELETE'
            else:
                adm = ''
            if dmsg['msg_parent'] != 0:
                ol.append(chr(P.GREY3)+chr(P.RVS_ON)+'f'+chr(P.RVS_OFF)+'IRST/'+chr(P.RVS_ON)+'p'+chr(P.RVS_OFF)+'REV')
                keys += b'FP'
            if (dmsg['msg_next'] != 0) and (dmsg['msg_next'] != msg_id):
                ol.append(chr(P.RVS_ON)+'n'+chr(P.RVS_OFF)+'EXT/'+chr(P.RVS_ON)+'l'+chr(P.RVS_OFF)+'AST')
                keys += b'NL'
            if (int(conn.bbs.BoardOptions.get('board'+str(dmsg['msg_board'])+'post',1)) <= conn.userclass):
                if (dmsg['msg_board']!=0) or ((dmsg['msg_board']==0)and(type(dmsg['msg_from'])==int)and(type(dmsg['msg_to'])==int)):
                    ol.append(chr(P.RVS_ON)+'r'+chr(P.RVS_OFF)+'EPLY')
                    keys += b'R'

            conn.Sendall(TT.set_Window(0,24)+chr(P.CLEAR))
            conn.Sendall(chr(P.GREEN)+P.toPETSCII(dmsg['msg_topic'])+chr(P.GREY2)+'\rBY:'+chr(P.LT_GREEN)+ (('*'+P.toPETSCII(user)) if type(user) == str else ' '+P.toPETSCII(user['uname'])))
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
                conn.Sendall(TT.set_CRSR(20,1)+chr(P.GREY3)+chr(P.RVS_ON)+'TO:'+chr(P.LT_GREEN)+ (('*'+P.toPETSCII(rcp)) if type(rcp) == str else ' '+P.toPETSCII(rcp['uname']))+chr(P.RVS_OFF))
            else:   # public message, display post date
                conn.Sendall(TT.set_CRSR(20,1)+chr(P.GREY3)+chr(P.RVS_ON)+'ON:'+chr(P.LT_GREEN)+ datetime.utcfromtimestamp(dmsg['msg_sent']).strftime(datestr) +chr(P.RVS_OFF))
            if conn.QueryFeature(TT.LINE_FILL) < 0x80:
                conn.Sendall(chr(P.YELLOW)+TT.Fill_Line(2,64)+TT.Fill_Line(22,64))
            else:
                conn.Sendall(TT.set_CRSR(0,2)+chr(P.YELLOW)+(chr(P.HLINE)*40))
                conn.Sendall(TT.set_CRSR(0,22)+(chr(P.HLINE)*40))
            conn.Sendall(TT.set_CRSR(0,23)+chr(P.GREY3))
            for i,o in enumerate(ol):
                conn.Sendall(o)
                if (i+1) < len(ol):
                    conn.Sendall('/')
            conn.Sendall('\r_ eXIT'+adm+TT.set_CRSR(0,3)+chr(P.GREY3))
            msg = formatX(dmsg['msg_text'])
            # display message
            for i,l in enumerate(msg):
                conn.Sendall(l)
                if (len(l)<40) and ('\r' not in l) and (i+1<len(msg)):
                    conn.Sendall('\r')
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
                    if conn.QueryFeature(TT.LINE_FILL) < 0x80:
                        conn.Sendall(chr(P.RED)+TT.Fill_Line(10,64)+TT.Fill_Line(14,64))
                    else:
                        conn.Sendall(chr(P.RED)+TT.set_CRSR(0,10)+(chr(P.HLINE)*40))
                        conn.Sendall(TT.set_CRSR(0,14)+(chr(P.HLINE)*40))
                    conn.Sendall(TT.set_Window(11,13))
                    conn.Sendall(chr(P.CLEAR)+chr(P.CRSR_DOWN)+chr(P.WHITE)+'          dELETE MESSAGE?(y/n)')
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
            conn.Sendall('error - iNVALID MESSAGE')
            time.sleep(1)
            done = True

#Write a message
# destination = int for a public board
#               string for username PM
# thread = message id for this thread, 0 for new thread
# returns msg_id or 0 if unsuccessful
def writeMessage(conn:Connection, destination = 1, thread:int = 0):

    # Editor
    def composer(message = list(['']*18), topic:str = ''):

        def dialog1(): # Send or cancel message
            nonlocal message
            conn.Sendall(TT.set_Window(23,24))
            ond = True
            while ond:
                conn.Sendall(chr(P.CLEAR)+"sEND/eDIT/qUIT(s/e/q)?")
                k = conn.ReceiveKey(b'SEQ')
                if k == b'S':
                    if sum(len(l) for l in message) == 0:
                        conn.Sendall('\rempty message')
                        time.sleep(1.5)
                    else:
                        ond = False
                else:
                    ond = False
            return(k)
        
        def dispMsg(): # Display message
            nonlocal message
            conn.Sendall(TT.set_Window(3,21)+chr(P.GREY3)+chr(P.CLEAR))
            for l in message:
                conn.Sendall(l)
                if len(l)<40:
                    conn.Sendall('\r')

        def hl_line():  # Highlight selected line
            nonlocal message, line
            conn.Sendall(TT.set_CRSR(0,line)+chr(P.WHITE))
            if (len(message[line]) == 0) or (message[line][0] == ' '):
                conn.Sendall('>')
            else:
                conn.Sendall(chr(P.RVS_ON) + message[line][0] + chr(P.RVS_OFF))
            conn.Sendall(TT.set_Window(22,22)+TT.set_CRSR(32,0)+chr(P.RVS_ON)+chr(P.YELLOW)+str(line+1).zfill(2)+'/18'+chr(P.RVS_OFF)+chr(P.GREY3))

        vfilter = bytes(string.ascii_letters + string.digits + " !?';:[]()*/@+-_,.$%&=<>#\\^" + chr(34),'ascii')    #Valid input characters
        conn.Sendall(TT.to_Screen())
        # Sync
        conn.Sendall(chr(0)*2)
        # Text mode
        conn.Sendall(TT.to_Text(0,0,0))
        RenderMenuTitle(conn,'Message Editor')
        if conn.QueryFeature(TT.LINE_FILL):
            conn.Sendall(chr(P.YELLOW)+TT.Fill_Line(22,64))
        else:
            conn.Sendall(chr(P.YELLOW)+TT.set_CRSR(0,22)+(chr(P.HLINE)*40))
        conn.Sendall(TT.set_CRSR(1,22)+chr(P.RVS_ON)+'f1 FOR hELP'+chr(P.RVS_OFF))

        dispMsg()
        line = 0
        column = 0
        hl_line()

        time.sleep(1)
        conn.Sendall(TT.set_Window(23,24)+chr(P.GREY3))

        while topic == '': # Get message topic if none provided
            conn.Sendall('tOPIC TITLE:\r')
            topic = conn.ReceiveStr(vfilter, maxlen = 32)
            time.sleep(0.5)
            conn.Sendall(chr(P.CLEAR))

        _LOG('Composing message',id=conn.id,v=4)
        #message = list(['']*18)
            
        running = True
        edit = True
        while running and conn.connected:
            #r,w,e= select.select((conn.socket,), (), (), 0)
            #if r:
            try:
                #conn.socket.setblocking(0)
                i_char = conn.ReceiveKey(vfilter+b'\r\x11\x13\x14\x1d\x85\x88\x8c\x91\x93\x94\x9d') #conn.socket.recv(1)
                if edit :   # Editing text
                    if i_char == b'\r':
                        tline = ' ' if len (message[line]) == 0 else message[line]
                        if conn.QueryFeature(TT.LINE_FILL):
                            conn.Sendall(TT.Fill_Line(line+3,32))
                        else:
                            conn.Sendall(TT.set_CRSR(0,line+3)+(' '*40))
                        conn.Sendall(TT.set_Window(3,21)+TT.set_CRSR(0,line)+tline) # Clear line in display window, print newly edited line
                        if line < 17:
                            line += 1
                            column = 0
                            hl_line()
                            conn.Sendall(TT.set_Window(23,24)+chr(P.CLEAR)+message[line]+chr(P.HOME)) # Update edit window
                        else:   # Past last line
                            option = dialog1()
                            if option == b'S':      # Send message
                                running = False
                            elif option == b'Q':    # Abort editor
                                running = False
                                message = None
                            else:                   # Keep editing
                                conn.Sendall(chr(P.CLEAR)+'sELECT line (crsr up/dwn)'+TT.set_Window(3,21)+TT.set_CRSR(0,line))
                                edit = False
                    elif (ord(i_char) == P.CRSR_RIGHT) and (column < len(message[line])):   # Cursor right
                        column += 1
                        conn.Sendallbin(i_char)
                    elif (ord(i_char) == P.CRSR_LEFT) and (column > 0):                     # Cursor left
                        column -= 1
                        conn.Sendallbin(i_char)
                    elif ord(i_char) == P.HOME:                                             # Cursor home
                        column = 0
                        conn.Sendallbin(i_char)
                    elif ord(i_char) == P.CLEAR:                                            # Clear line
                        column = 0
                        message[line] = ''
                        conn.Sendallbin(i_char)
                    elif (ord(i_char) == P.DELETE) and (len(message[line]) > 0) and (column > 0):   # Delete caracter
                        message[line] = message[line][0:column-1] + message[line][column:]
                        column -= 1
                        conn.Sendallbin(i_char)
                    elif (ord(i_char) == P.INSERT) and (40 > len(message[line]) > 0) and (column < len(message[line])):   # Insert blank space
                        message[line] = message[line][0:column] + ' ' + message[line][column:]
                        conn.Sendallbin(i_char)
                    elif ord(i_char) == P.F8:                                               # Finish editing
                        if conn.QueryFeature(TT.LINE_FILL):
                            conn.Sendall(TT.Fill_Line(line+3,32))
                        else:
                            conn.Sendall(TT.set_CRSR(0,line+3)+(' '*40))
                        conn.Sendall(TT.set_Window(3,21)+TT.set_CRSR(0,line)+message[line]) # Clear line in display window, print newly edited line
                        option = dialog1()
                        if option == b'S':      # Send message
                            running = False
                        elif option == b'Q':    # Abort editor
                            running = False
                            message = None
                        else:                   # Keep editing
                            conn.Sendall(chr(P.CLEAR)+'sELECT line (crsr up/dwn)'+TT.set_Window(3,21)+TT.set_CRSR(0,line))
                            edit = False
                    elif ord(i_char) == P.F7:   # Select line to edit
                        tline = ' ' if len (message[line]) == 0 else message[line]
                        if conn.QueryFeature(TT.LINE_FILL):
                            conn.Sendall(TT.Fill_Line(line+3,32))
                        else:
                            conn.Sendall(TT.set_CRSR(0,line+3)+(' '*40))
                        conn.Sendall(TT.set_Window(3,21)+TT.set_CRSR(0,line)+message[line]) # Clear line in display window, print newly edited line
                        conn.Sendall(TT.set_Window(23,24)+chr(P.CLEAR)+'sELECT line (crsr up/dwn)'+TT.set_Window(3,21)+TT.set_CRSR(0,line))
                        edit = False
                    elif ord(i_char) == P.F1:   # Display help screen
                        conn.Sendall(TT.set_Window(3,21)+chr(P.CLEAR))
                        conn.Sendall(chr(P.YELLOW)+'\r     ---lINE EDITOR INSTRUCTIONS---\r')
                        conn.Sendall('\rtHIS EDITOR ALLOWS YOU TO TYPE AND EDIT A SINGLE LINE AT A TIME.\r')
                        conn.Sendall('ins/del AND clr/home ARE SUPPORTED\r')
                        conn.Sendall('pRESS return TO ACCEPT A LINE\rf7 TO SELECT A NEW LINE\rf8 TO SEND/ABORT MESSAGE\r')
                        conn.Sendall('\rpRESS ANY KEY TO CONTINUE...')
                        conn.Receive(1)
                        dispMsg()
                        conn.Sendall(TT.set_Window(23,24)+chr(P.CLEAR)+'sELECT line (crsr up/dwn)'+TT.set_Window(3,21)+TT.set_CRSR(0,line))
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
                        if column == 40:
                            if conn.QueryFeature(TT.LINE_FILL):
                                conn.Sendall(TT.Fill_Line(line+3,32))
                            else:
                                conn.Sendall(TT.set_CRSR(0,line+3)+(' '*40))
                            conn.Sendall(TT.set_Window(3,21)+TT.set_CRSR(0,line)+message[line]) # Clear line in display window, print newly edited line
                            if line < 17:
                                line += 1
                                column = 0
                            time.sleep(0.5)
                            conn.Sendall(TT.set_Window(23,24)+chr(P.CLEAR)+message[line]+chr(P.HOME)) # Update edit window
                else:   # Selecting line to edit
                    if (ord(i_char) == P.CRSR_DOWN) and (line < 17):
                        line += 1
                        conn.Sendallbin(i_char)
                    elif (ord(i_char) == P.CRSR_UP) and (line > 0):
                        line -= 1
                        conn.Sendallbin(i_char)
                    elif i_char == b'\r':
                        edit = True
                        column = 0
                        hl_line()
                        conn.Sendall(TT.set_Window(23,24)+chr(P.CLEAR)+message[line]+chr(P.HOME)) # Update edit window
            except Exception as e:
                running = False
                conn.connected = False

        conn.Sendall(TT.set_Window(0,24))
        return(P.toASCII(topic),message)

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
            conn.Sendall('error:iNVALID THREAD')
            _LOG('Messaging: ERROR - Invalid thread',id=conn.id)
            return
        else: 
            topic = dthread['msg_topic']
        ...
    if type(destination) == str:    # Private message
        # user exist?
        duser = db.chkUser(destination)
        if duser != None:
            user = duser.doc_id
            board = 0
        else:
            conn.Sendall('error:iNVALID USER')
            _LOG('Messaging: ERROR - Invalid user',id=conn.id)
            return
    else:   # Board message
        user = 0
        board = destination

    # Note - fixme: You can get to this point even if the thread doesnt belong to the destination board

    topic, message = composer(topic=P.toPETSCII(topic))  ###### Test composer
    if message != None:
        i = 0
        while (sum(len(c) for c in message[i:])) > 0:
            i += 1
        msgtxt = P.toASCII('\n'.join(l for l in message[:i]))
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
        conn.Sendall(chr(P.CLEAR)+chr(P.LT_GREEN)+'mESSAGE SENT')
    else:
        _LOG('Messaging: Message cancelled',id=conn.id,v=4)
    return m_id

#Display user private messages (board = 0) or public board
def inbox(conn:Connection, board):
    keys = string.ascii_letters + string.digits + ' +-_,.$%&'
    db:DBase = conn.bbs.database
    # Select screen output
    conn.Sendall(TT.to_Screen())
    # Sync
    conn.Sendall(chr(0)*2)
    # Text mode
    conn.Sendall(TT.to_Text(0,0,0))
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
                tt = ' '+chr(P.GREY1)+chr(188)+(chr(P.LT_BLUE) if i['msg_from']==conn.userid else chr(P.GREEN))+' '
            else:
                tt = ' '+chr(P.GREEN)+chr(188)+(chr(P.CYAN) if i['msg_to']==conn.userid else chr(P.LT_GREEN))+' '
            to = crop(i['msg_topic'],24) #i['msg_topic'] if len(i['msg_topic'])<25 else i['msg_topic'][0:21]+'...'
            tl = table.get(doc_id=i['msg_prev'])
            if type(tl['msg_from'])==int:
                user = utable.get(doc_id = tl['msg_from'])['uname']
            else:
                user = tl['msg_from']
            tu = crop(user,11)  #user if len(user)<12 else user[0:8]+'...'
            tt = tt+P.toPETSCII(to)+chr(P.YELLOW)+(chr(P.CRSR_RIGHT)*(24-len(to)))+chr(P.VLINE)+chr(P.WHITE)+P.toPETSCII(tu)
            ts = tl['msg_sent']    # Get timestamp of last message in thread
            threads.append([tt,i.doc_id,um,ts])  #topic - thread_id, first unread, timestamp

        # sort by sent timestamp, newest thread first
        threads.sort(key=lambda threads: threads[3],reverse=True)
        conn.Sendall(TT.enable_CRSR())
        if refresh:
            conn.Sendall(TT.set_Window(0,24))
            RenderMenuTitle(conn,title)
            if int(conn.bbs.BoardOptions.get('board'+str(board)+'post',1)) <= conn.userclass:
                tt = chr(P.RVS_ON)+'N'+chr(P.RVS_OFF)+'EW '+('THREAD' if board != 0 else 'MESSAGE')+('\r' if conn.userclass < 10 else ('-'+chr(P.RVS_ON)+'D'+chr(P.RVS_OFF)+'ELETE'))
            else:
                tt = '\r'
            if conn.QueryFeature(TT.LINE_FILL) < 0x80:
                conn.Sendall(chr(P.YELLOW)+TT.Fill_Line(22,64))
            else:
                conn.Sendall(TT.set_CRSR(0,22)+chr(P.YELLOW)+(chr(P.HLINE)*40))
            conn.Sendall(TT.set_CRSR(0,23)+chr(P.GREY3)+'nAVIGATE WITH '+chr(P.RVS_ON)+'CRSR'+chr(P.RVS_OFF)+' - '+tt)
            conn.Sendall(TT.set_CRSR(0,24)+'rEAD '+chr(P.RVS_ON)+'F'+chr(P.RVS_OFF)+'IRST/'+chr(P.RVS_ON)+'L'+chr(P.RVS_OFF)+'AST OR '+chr(P.RVS_ON)+'U'+chr(P.RVS_OFF)+'NREAD MESSAGE')
            conn.Sendall(TT.set_Window(3,21))
            refresh = False

        conn.Sendall(chr(P.CLEAR))
        last = len(threads) if len(threads) < (19*(page+1)) else 19*(page+1)
        for i in range(19*page,last):
            conn.Sendall(threads[i][0])
            if i < last-1:
                conn.Sendall('\r')

        conn.Sendall(TT.disable_CRSR()+chr(P.CYAN))
        pos = 0
        o_pos = 1
        while conn.connected:
            if pos != o_pos:
                conn.Sendall(TT.set_CRSR(0,pos)+'>')
                o_pos = pos
            k = conn.ReceiveKey(bytes(chr(P.CRSR_DOWN)+chr(P.CRSR_UP)+chr(P.CRSR_LEFT)+chr(P.CRSR_RIGHT)+'FLU_'+('N'if tt!='' else '')+('D'if conn.userclass == 10 else ''),'utf_8'))
            if len(threads) > 0:
                if ord(k) == P.CRSR_DOWN:
                    if pos+1 < (len(threads)-(19*page)):    # move down
                        if pos < 18:
                            pos += 1
                            conn.Sendall(chr(P.CRSR_LEFT)+' ')
                        elif len(threads)>(19*(page+1)):
                            page +=1
                            break
                elif ord(k) == P.CRSR_UP:                   # move up
                    if pos > 0:
                        pos -= 1
                        conn.Sendall(chr(P.CRSR_LEFT)+' ')
                    elif page > 0:
                        page -= 1
                        break
                elif ord(k) == P.CRSR_RIGHT:                 # next page
                    if len(threads)>(19*(page+1)):
                        page +=1
                        break
                elif ord(k) == P.CRSR_LEFT:                # previous page
                    if page > 0:
                        page -= 1
                        break
                elif k == b'F':                  # First message
                    conn.Sendall(TT.enable_CRSR()+TT.set_Window(0,24))
                    readMessage(conn,threads[pos+(19*page)][1])
                    refresh = True
                    break
                elif k == b'L':                  # Last message
                    m = table.get(doc_id=threads[pos+(19*page)][1])
                    conn.Sendall(TT.enable_CRSR()+TT.set_Window(0,24))
                    readMessage(conn,m['msg_prev'])
                    refresh = True
                    break
                elif k == b'U':                  # First unread message
                    if threads[pos+(19*page)][2] != None:
                        conn.Sendall(TT.enable_CRSR()+TT.set_Window(0,24))
                        readMessage(conn,threads[pos+(19*page)][2].doc_id)
                        refresh = True
                        break
                elif k == b'D':                 # Delete thread
                    if conn.QueryFeature(TT.LINE_FILL) < 0x80:
                        conn.Sendall(chr(P.RED)+TT.Fill_Line(10,64)+TT.Fill_Line(14,64))
                    else:
                        conn.Sendall(chr(P.RED)+TT.set_CRSR(0,7)+(chr(P.HLINE)*40))
                        conn.Sendall(TT.set_CRSR(0,11)+(chr(P.HLINE)*40))
                    conn.Sendall(TT.set_Window(11,13))
                    conn.Sendall(chr(P.CLEAR)+chr(P.CRSR_DOWN)+chr(P.WHITE)+'           dELETE THREAD?(y/n)')
                    if conn.ReceiveKey(b'YN') == b'Y':
                        deleteThread(conn,threads[pos+(19*page)][1])
                    refresh = True
                    break
            if k == b'N':              # new thread
                conn.Sendall(TT.enable_CRSR())
                if board == 0:
                    # get destination username
                    if conn.QueryFeature(TT.LINE_FILL) < 0x80:
                        conn.Sendall(TT.Fill_Line(10,64)+TT.Fill_Line(14,64))
                    else:
                        conn.Sendall(TT.set_CRSR(0,7)+(chr(P.HLINE)*40))
                        conn.Sendall(TT.set_CRSR(0,11)+(chr(P.HLINE)*40))
                    conn.Sendall(TT.set_Window(11,13))
                    while conn.connected:
                        conn.Sendall(chr(P.CLEAR)+'sEND pm TO: ')
                        dest = P.toASCII(conn.ReceiveStr(bytes(keys,'ascii'), 16, False))
                        print(len(dest),len(conn.username))
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
                                    conn.Sendall('\rdO YOU MEAN: '+P.toPETSCII(match)+' ?(y/n)')
                                    if conn.ReceiveKey(b'YN') == b'Y':
                                        dest = match
                                        break
                            else:
                                break
                        elif dest == '':
                            break
                else:
                    dest = board
                conn.Sendall(TT.set_Window(0,24))
                if dest != '':
                    writeMessage(conn, destination=dest)
                refresh = True
                break
            if k == b'_':
                conn.Sendall(TT.enable_CRSR()+TT.set_Window(0,24))
                done = True
                break
    #conn.ReceiveKey()

#Toggle the read status of a private message
def toggleRead(conn:Connection, msg_id):
    ...

#Get number of unread messages since last login
def unreadCount(conn:Connection):
    ...

#Get first unread message in a given thread
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