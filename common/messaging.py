# Messaging sub-system
from common.connection import Connection
from datetime import datetime
from common import turbo56k as TT
from common.bbsdebug import _LOG
from common.style import RenderMenuTitle
from common.dbase import DBase
from common.helpers import text_displayer, crop, formatX, More
from html import escape
from tinydb import Query
from tinydb.table import Document
import time
import string
import difflib
import textwrap
import sys
import os

###################################################################################################
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
###################################################################################################

####################
# Read a message
####################
def readMessage(conn:Connection, msg_id:int):
    scwidth,scheight = conn.encoder.txt_geo
    if 'MSX' in conn.mode:
        hcode = 0x17
    elif 'ZX' in conn.mode:
        hcode = ord('-')
    else:
        hcode = 0x40
    db:DBase = conn.bbs.database
    table = db.db.table('MESSAGES')
    dbQ = Query()
    done = False
    win = conn.QueryFeature(TT.SET_WIN) < 0x80
    while not done and conn.connected:
        dmsg = table.get(doc_id = msg_id)
        if dmsg != None:
            # print(dmsg)
            utable = db.db.table('USERS')
            if type(dmsg['msg_from'])==int:
                user = utable.get(doc_id = dmsg['msg_from'])
            else:
                user = dmsg['msg_from']
            # build option string
            ol = [f'<INK c={conn.style.TxtColor}>']
            if win:
                keys = ''
            else:
                keys = conn.encoder.back

            if conn.userclass == 10:    # Admin reading
                keys += 'd'
                adm = ' <RVSON>D<RVSOFF>elete'
            else:
                adm = ''
            if dmsg['msg_parent'] != 0:
                ol.append('<RVSON>F<RVSOFF>irst/<RVSON>P<RVSOFF>rev')
                keys += 'fp'
            if (dmsg['msg_next'] != 0) and (dmsg['msg_next'] != msg_id):
                ol.append('<RVSON>N<RVSOFF>ext/<RVSON>L<RVSOFF>ast')
                keys += 'nl'
            if (int(conn.bbs.BoardOptions.get('board'+str(dmsg['msg_board'])+'post',1)) <= conn.userclass):
                if (dmsg['msg_board']!=0) or ((dmsg['msg_board']==0)and(type(dmsg['msg_from'])==int)and(type(dmsg['msg_to'])==int)):
                    ol.append('<RVSON>R<RVSOFF>eply')
                    keys += 'r'

            conn.SendTML(f'<WINDOW top=0 bottom={scheight}><CLR><GREEN>{crop(dmsg["msg_topic"],scwidth-2,conn.encoder.ellipsis)}<GREY2><BR>'
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
                conn.SendTML(f'<AT x={scwidth//2} y=1><GREY3><RVSON>on:<LTGREEN>{datetime.fromtimestamp(dmsg["msg_sent"]):{datestr}}<RVSOFF>')
            if win:
                conn.SendTML(f'{f"<YELLOW><LFILL row=2 code={hcode}><LFILL row={scheight-3} code={hcode}>" if conn.QueryFeature(TT.LINE_FILL)<0x80 else f"<AT x=0 y=2><YELLOW><HLINE n={scwidth}><AT x=0 y={scheight-3}><HLINE n={scwidth}>"}'
                            f'<AT x=0 y={scheight-2}><GREY3>')
                for i,o in enumerate(ol):
                    conn.SendTML(o)
                    if i > 0 and (i+1) < len(ol):
                        conn.Sendall('/')
                conn.SendTML(f'<BR><BACK> Exit{adm}<AT x=0 y=3><GREY3>')
            else:
                conn.SendTML(f'{f"<YELLOW><LFILL row=2 code={hcode}>" if conn.QueryFeature(TT.LINE_FILL)<0x80 else f"<AT x=0 y=2><YELLOW><HLINE n={scwidth}>"}<GREY3>')
            msg,lines = formatMsg(dmsg['msg_text'],scwidth)
            # escape html characters and add line breaks
            for i,l in enumerate(msg):
                l = l.replace('\n','')
                msg[i] = escape(l)
                if len(l)<scwidth:
                    msg[i] = msg[i]+'<BR>'

            conn.SendTML('<CURSOR enable=False>')
            # mark it as read if needed
            if conn.userid != 0:
                if conn.userid not in dmsg['msg_read']:
                    dmsg['msg_read'].append(conn.userid)
                    table.upsert(Document({'msg_read':dmsg['msg_read']},doc_id=msg_id))
            conn.SendTML(f'<WINDOW top=3 bottom={scheight-4}>')
            while conn.connected:
                if win:
                    k = text_displayer(conn,msg,scheight-6,None,keys)
                else:
                    More(conn,msg,scheight-1)
                    conn.SendTML('<DEL n=8>')
                    conn.SendTML(f'<YELLOW><HLINE n={scwidth}><GREY3>')
                    for i,o in enumerate(ol):
                        conn.SendTML(o)
                        if i > 0 and (i+1) < len(ol):
                            conn.Sendall('/')
                    conn.SendTML(f'<BR><BACK> Exit{adm}<AT x=0 y=3><GREY3>')
                    k = conn.ReceiveKey(list(keys))
                if k == conn.encoder.back:
                    done = True
                    break
                elif k == 'f':
                    msg_id = dmsg['msg_parent']
                    break
                elif k == 'p':
                    msg_id = dmsg['msg_prev']
                    break
                elif k == 'n':
                    msg_id = dmsg['msg_next']
                    break
                elif k == 'l':
                    if dmsg['msg_parent'] != 0:
                        msg_id = table.get(doc_id = dmsg['msg_parent'])['msg_prev']
                    else:
                        msg_id = dmsg['msg_prev']
                    break
                elif k == 'r':
                    if dmsg['msg_board'] == 0:
                        uid = dmsg['msg_from'] if dmsg['msg_from'] != conn.userid else dmsg['msg_to']
                        dest = utable.get(doc_id=uid)['uname']
                    else:
                        dest = dmsg['msg_board']
                    conn.SendTML(f'<CURSOR>')
                    r_id = writeMessage(conn, destination = dest, thread = (dmsg['msg_parent'] if dmsg['msg_parent']!=0 else msg_id))
                    if r_id != 0:
                        msg_id = r_id
                    break
                elif k == 'd': # Delete:
                    tml = ''
                    if conn.QueryFeature(TT.LINE_FILL) < 0x80:
                        tml += f'<RED><LFILL row=10 code={hcode}><LFILL row=14 code={hcode}>'
                    else:
                        tml += f'<RED><AT x=0 y=10><HLINE n={scwidth}><AT x=0 y=14><HLINE n={scwidth}>'
                    if conn.QueryFeature(TT.SET_WIN) < 0x80:
                        tml += '<WINDOW top = 11 bottom =13><CLR><CRSRD>'
                    else:
                        tml += f'<AT x=0 y=11><SPC n={scwidth-1}><DEL> <BR><SPC n={scwidth-1}><DEL> <BR><SPC n={scwidth-1}><DEL> <BR><CRSRU n=2>'
                    conn.SendTML(tml+f'<WHITE><SPC n={(scwidth-20)//2}>Delete message?(Y/N)')
                    if conn.ReceiveKey('yn') == 'y':
                        if dmsg['msg_parent'] == 0: # delete whole thread
                            deleteThread(conn,msg_id)
                            done = True
                            break
                        else:
                            msg_id = deleteMessage(conn,msg_id)
                            break
                    break

            conn.SendTML(f'<WINDOW top=0 bottom={scheight}>')
        else:
            _LOG('readMessage: ERROR - Invalid message',id=conn.id,v=1)
            conn.SendTML('ERROR - Invalid message<PAUSE n=1>')
            done = True

###########################################################
# Write a message
# destination = int for a public board
#               string for username PM
# thread = message id for this thread, 0 for new thread
# returns msg_id or 0 if unsuccessful
###########################################################
def writeMessage(conn:Connection, destination = 1, thread:int = 0):

    _dec = conn.encoder.decode
    _enc = conn.encoder.encode


    # Editor
    def composer(message = '', topic:str = ''):
    
        def dialog1(): # Send or cancel message
            nonlocal message
            conn.SendTML(f'<WINDOW top={scheight-2} bottom={scheight-1}>')
            k = ''
            while conn.connected:
                conn.SendTML('<CLR>Send/Edit/Quit(S/E/Q)?')
                k = conn.ReceiveKey('seq')
                if k == 's':
                    if sum(len(l) for l in fmessage) == 0:
                        conn.SendTML('<BR>EMPTY MESSAGE<PAUSE n=1.5>')
                    else:
                        break
                else:
                    break
            return(k)
        
        def help(): #Display help
            if win:
                htxt= f'''--- Line editor instructions ---

This editor allows you to type 
and edit a single line at a
time.
INSERT/DELETE and CLEAR and
HOME keys are supported
Press RETURN to accept a line
{line_k[1]} to select a new line
{quit_k[1]} to send/abort message

Press {_dec(conn.encoder.back)} to continue...'''
            else:
                htxt= f'''-- Simple message editor help --

Enter the following commands
on a separate line:

/s Send message
/q Abort message
/v View message
/p Edit previous line
/? This help screen
Press {_dec(conn.encoder.back)} to continue...'''
            conn.SendTML(f'<WINDOW top=3 bottom={scheight-4}><CLR>')
            text_displayer(conn,formatX(htxt,scwidth),tslines)

        def dispMsg(startline = 0): # Display message
            nonlocal fmessage
            if win:
                conn.SendTML(f'<WINDOW top=3 bottom={scheight-4}>{tcolor}<CLR>')
            endline = startline+(tslines)
            endline = endline if len(fmessage)>=endline else len(fmessage)
            for l in range(startline,endline):
                fline = fmessage[l].replace('\n','')
                conn.SendTML(fline)
                if len(fline)<scwidth:
                    conn.SendTML('<BR>')
            if not win:
                conn.SendTML('<CRSRU>')

        def updMsg(startline=0,scroll=0,rline=0):   # Update message display
            nonlocal fmessage, lines

            tfmessage,tlines = formatMsg(message,scwidth)
            if win:
                # Compare new and old formatted message
                # Find which line range differ after the edit.
                if rline >=0:
                    tmpc = ' ' if len(tline)== 0 else ' ' if tline[0] == '\n' else tline[0]    # Refresh first char of line being edited
                    conn.SendTML(f'<WINDOW top=3 bottom={scheight-4}><AT x=0 y={rline}>{tcolor}{tmpc}')
                for i in range(0+(startline-scroll),(tslines)+(startline-scroll)):
                    y = i-(startline-scroll)
                    if i < len(fmessage):
                        if i < len(tfmessage):
                            if tfmessage[i] != fmessage[i]:
                                if conn.QueryFeature(TT.LINE_FILL):
                                    conn.SendTML(f'<LFILL row={y+3} code=32>')
                                else:
                                    conn.SendTML(f'<AT x=0 y={y+3}><SPC n=32>')
                                tmp = tfmessage[i].replace('\n','')
                                conn.SendTML(f'<AT x=0 y={y}>'+tmp)
                                if len(tmp)<scwidth:
                                    conn.SendTML('<BR>')
                        else:   # edited message has less formatted lines than before
                            # Clear the rest of the lines
                            if conn.QueryFeature(TT.LINE_FILL):
                                conn.SendTML(f'<LFILL row={y+3} code=32>')
                            else:
                                conn.SendTML(f'<AT x=0 y={i+3}><SPC n=32>')
                    elif i < len(tfmessage):    # Edited message has more lines than before
                        tmp = tfmessage[i].replace('\n','')
                        conn.SendTML(f'<AT x=0 y={y}>'+tmp)
                        if len(tmp)<scwidth:
                            conn.SendTML('<BR>')
                    else:   # No more lines
                        break
                #Scroll
                if scroll != 0:
                    conn.SendTML(f'<SCROLL rows={scroll}>')
                    y = 0 if scroll==-1 else scheight-8
                    conn.SendTML(f'<AT x=0 y={y}>{tfmessage[startline] if y == 0 else tfmessage[startline+(scheight-8)]}')
                    if y == 0:
                        conn.SendTML('<HOME>')
                    else:
                        conn.SendTML(f'<AT x=0 y={y}>')
            fmessage = tfmessage
            lines = tlines

        def hl_line():  # Highlight selected line
            nonlocal fmessage, line
            if win:
                conn.SendTML(f'<AT x=0 y={line}>{hlcolor}')
                if (len(fmessage[line+ydisp]) == 0):
                    conn.Sendall('>')
                elif (fmessage[line+ydisp][0] in ' \n'):
                    conn.Sendall('>')
                else:
                    conn.SendTML(f'<RVSON>{fmessage[line+ydisp][0]}<RVSOFF>')
                conn.SendTML(f'<WINDOW top={scheight-3} bottom={scheight-3}><AT x=20 y=0>')
            else:
                conn.SendTML(f'<BR>Topic: {topic}<BR>Characters used: ')
            conn.SendTML(f'<RVSON><YELLOW>{len(message):0>4}/3000<RVSOFF>{tcolor}')
            if not win:
                conn.SendTML('<BR>')

        ydisp = 0   # Message display window offset

        scwidth,scheight = conn.encoder.txt_geo
        if conn.QueryFeature(TT.SET_WIN) < 0x80:
            tslines = scheight-7         # Number of visible message lines
            win = True
        else:
            tslines = scheight
            win = False
        if 'MSX' in conn.mode:
            hcode = 0x17
            tcolor = '<WHITE>'
            hlcolor = '<YELLOW>'
        elif 'ZX' in conn.mode:
            hcode = ord('-')
            tcolor = '<WHITE>'
            hlcolor = '<YELLOW>'
        else:
            hcode = 0x40
            tcolor = '<GREY3>'
            hlcolor = '<WHITE>'
        vfilter = string.ascii_letters + string.digits + " !?';:[]()*/@+-_,.$%&=<>#\\^" + chr(34)    # Valid input characters
        ckeys = conn.encoder.ctrlkeys
        if win:
            if conn.mode == 'PET64':
                help_k = (ckeys['F1'],'F1')
                line_k = (ckeys['F7'],'F7')
                quit_k = (ckeys['F8'],'F8')
            elif conn.mode == "PET264":
                help_k = (ckeys['HELP'],'HELP')
                line_k = (ckeys['F3'],'F3')
                quit_k = (ckeys['ESC'],'ESC')
            else: # MSX
                help_k = (ckeys['F1'],'F1')
                line_k = (ckeys['F5'],'F5')
                quit_k = (ckeys['F10'],'F10')
        else:
            help_k = line_k = quit_k = (chr(0),'')
        conn.SendTML(f'<SETOUTPUT><WINDOW top=0 bottom={scheight-1}><NUL n=2><TEXT border={conn.style.BoColor} background={conn.style.BgColor}><MTITLE t="Message Editor"><YELLOW>')
        if win:
            conn.SendTML(f'{f"<LFILL row={scheight-3} code={hcode}>"if conn.QueryFeature(TT.LINE_FILL)<0x80 else f"<AT x=0 y={scheight-3}><HLINE n={scwidth}>"}'
                     f'<AT x=1 y={scheight-3}><RVSON>{help_k[1]} Help - {quit_k[1]} Send<RVSOFF>')
        else:
            conn.SendTML('Enter /? for help')
        fmessage,lines = formatMsg(message,scwidth)
        conn.SendTML(f'<PAUSE n=1><WINDOW top={scheight-2} bottom={scheight-1}>{tcolor}')
        line = 0
        while topic == '' and conn.connected: # Get message topic if none provided
            if not win:
                conn.SendTML('<BR>')
            conn.SendTML('Topic title:<BR>')
            topic = _dec(conn.ReceiveStr(vfilter, maxlen = 32))
            if win:
                conn.SendTML('<PAUSE n=0.5><CLR>')
        dispMsg()
        hl_line()
        _LOG('Composing message',id=conn.id,v=4)
        running = True
        edit = True
        tline = fmessage[line]  # Line being edited
        column = 0
        conn.SendTML(f'<WINDOW top={scheight-2} bottom={scheight-1}>{tcolor}')
        conn.SendTML(tline)
        if win:
            conn.SendTML('<HOME>')
        if 'CRSRU' in ckeys:
            cursors = [ckeys['CRSRU'],ckeys['CRSRD'],ckeys['CRSRL'],ckeys['CRSRR']]
        else:
            cursors = [chr(0),chr(0),chr(0),chr(0)]
        cursors += [ckeys.get('HOME',chr(0)),ckeys.get('INSERT',chr(0)),ckeys.get('CLEAR',chr(0)),ckeys.get('DELETE',chr(0))]
        while running and conn.connected:
            try:
                i_char = conn.ReceiveKey([c for c in vfilter]+cursors+[conn.encoder.nl]+[help_k[0],line_k[0],quit_k[0]])
                if edit :   # Editing text
                    if i_char == conn.encoder.nl:   # New line
                        # check commands for non-turbo mode
                        if not win:
                            if tline == '/?':   # Help
                                help()
                                column = 0
                                tline = ''
                                hl_line()
                                dispMsg()
                                continue
                            elif tline == '/s': # Send
                                running = False
                                continue
                            elif tline == '/q': # Abort
                                running = False
                                message = None
                                continue  
                            elif tline == '/v': # View
                                tline = ''
                                hl_line()
                                dispMsg()
                                column = 0
                                continue
                            elif tline == '/p': # Edit previous line
                                hl_line()
                                if  len(fmessage) > 1:
                                    line = len(fmessage)-2
                                    conn.SendTML(f'<BR>{fmessage[line]}')
                                    tline = fmessage[line]
                                    column = len(tline)-1
                                else:
                                    column = 0
                                    tline = ''
                                continue
                        if column < len(tline):
                            if tline[column] != '\n':
                                tline = tline[0:column] + '\n' + tline[column:]
                        else:
                            tline += '\n'
                        if not win:
                            spc = scwidth - column
                            conn.SendTML(f'<SPC n={spc}>')
                        message = message[0:lines[line+ydisp][0]]+tline+(' ' if lines[line+ydisp][2] else '')+message[lines[line+ydisp][1]:]  # Insert edited line into original message
                        rline = line
                        if not lines[line+ydisp-1][2] or column != 0: # New line not at the start of a wordwrapped line
                            line += 1
                        if line > tslines-1:
                            ydisp += 1
                            scroll = 1
                            line = tslines-1
                        else:
                            scroll = 0
                        updMsg(ydisp,scroll,rline)
                        if line+ydisp >= len(lines):
                            line -= 1
                        if len(message) < 3000:
                            if line+ydisp > len(fmessage)-1:
                                fmessage.append('')
                            if win:
                                hl_line()
                                conn.SendTML(f'<WINDOW top={scheight-2} bottom={scheight-1}><CLR>{fmessage[line+ydisp]}<HOME>')
                            elif column > len(tline):
                                conn.SendTML('<BR>')
                        else:   # Past character limit
                            option = dialog1()
                            if option == 's':      # Send message
                                running = False
                            elif option == 'q':    # Abort editor
                                running = False
                                message = None
                            elif win:                   # Keep editing
                                conn.SendTML(f'<CLR>Select LINE (CRSR UP/DWN)<WINDOW top=3 bottom={scheight-4}><AT x=0 y={line}>')
                                edit = False
                        column = 0
                        tline = fmessage[line+ydisp]
                        if (len(tline) > 0) and not win:
                            conn.SendTML(tline)
                            column = len(tline)
                            if tline[-1] == '\n':
                                column -= 1
                    elif i_char == cursors[3] and (column < len(tline)) and tline[column] != '\n':   # Cursor right
                        column += 1
                        conn.Sendall(i_char)
                    elif i_char == cursors[2] and (column > 0):            # Cursor left
                        column -= 1
                        conn.Sendall(i_char)
                    elif i_char == cursors[4]:                                # Cursor home
                        if win:
                            conn.Sendall(i_char)
                        elif column > 0:
                            conn.SendTML(f'<CRSRL n={column}>')
                        column = 0
                    elif win and i_char == cursors[6]:                       # Clear line
                        column = 0
                        tline = ''
                        if win:
                            conn.Sendall(i_char)
                    elif (i_char == cursors[7]) and (len(tline)> 0) and (column > 0):   # Delete caracter
                        tline = tline[0:column-1] + tline[column:]
                        column -= 1
                        conn.SendTML('<DEL>')
                    elif (conn.mode not in ['MSXstd']) and (i_char == cursors[5]) and (scwidth > len(tline) > 0) and (column < len(tline)):   # Insert blank space
                        tline = tline[0:column] + ' ' + tline[column:]
                        conn.Sendall(i_char)
                    elif i_char == quit_k[0]:                                               # Finish editing
                        if conn.QueryFeature(TT.LINE_FILL):
                            conn.SendTML(f'<LFILL row={line+3} code=32>')
                        else:
                            conn.SendTML(f'<AT  x=0 y={line+3}><SPC n={scwidth}>')
                        conn.SendTML(f'<WINDOW top=3 bottom={scheight-4}><AT x=0 y={line}>{fmessage[line+ydisp]}') # Clear line in display window, print newly edited line
                        option = dialog1()
                        if option == 's':      # Send message
                            running = False
                        elif option == 'q':    # Abort editor
                            running = False
                            message = None
                        else:                   # Keep editing
                            conn.SendTML(f'<CLR>Select LINE (CRSR UP/DWN)<WINDOW top=3 bottom={scheight-4}><AT x=0 y={line}>')
                            edit = False
                    elif i_char == line_k[0]:   # Select line to edit
                        message = message[0:lines[line+ydisp][0]]+tline+(' ' if lines[line+ydisp][2] else '')+message[lines[line+ydisp][1]:]  # Insert edited line into original message
                        updMsg(ydisp,rline=line)
                        conn.SendTML(f'<WINDOW top={scheight-2} bottom={scheight-1}><CLR>Select LINE (CRSR UP/DWN)<WINDOW top=3 bottom={scheight-4}><AT x=0 y={line}>')
                        edit = False
                    elif i_char == help_k[0]:   # Display help screen
                        help()
                        dispMsg(ydisp)
                        conn.SendTML(f'<WINDOW top={scheight-2} bottom={scheight-1}><CLR>Select line (CRSR UP/DWN)<WINDOW top=3 bottom={scheight-4}><AT x=0 y={line}>')
                        edit = False
                    elif i_char in vfilter:
                        # Alphanumeric characters
                        column += 1
                        if column <= len(tline):
                            tline = tline[0:column-1] + i_char + tline[column:]
                        else:
                            tline += i_char
                        conn.Sendall(_enc(i_char))
                        if column == scwidth+1:
                            message = message[0:lines[line+ydisp][0]]+tline+(' ' if lines[line+ydisp][2] else '')+message[lines[line+ydisp][1]:]  # Insert edited line into original message
                            rline = line
                            line += 1
                            column = 0
                            if line+ydisp > len(fmessage)-1:
                                fmessage.append('')
                            if line > scheight-8:
                                ydisp += 1
                                scroll = 1
                                line = scheight-8
                            else:
                                scroll = 0
                            updMsg(ydisp,scroll,rline)
                            if len(message) < 3000:
                                if win:
                                    hl_line()
                                    conn.SendTML(f'<WINDOW top={scheight-2} bottom={scheight-1}><CLR>')
                                else:
                                    _tmp = scwidth-len(fmessage[line+ydisp-1])
                                    if _tmp > 0 and lines[line+ydisp-1][1]-lines[line+ydisp-1][0]<scwidth:
                                        if conn.mode in ['ATRSTL','ATRSTM','ATRSTH','ANSI']:
                                            conn.SendTML(f'<DEL><CRSRU><CRSRR n={scwidth-_tmp+1}><SPC n={_tmp-1}>') # ANSI and Atari ST dont wrap back to the previous line when deleting
                                        else:
                                            conn.SendTML(f'<DEL n={_tmp}><CRSRR n={_tmp-1}>')   # Use cursor instead of newline to avoid inserted line on some C64 terminals
                                    else:
                                        conn.SendTML('<DEL>')   # Last character was space and the previous line had 'scwidth' characters
                                conn.SendTML(f'{fmessage[line+ydisp]}')
                            else:   # Past character limit
                                option = dialog1()
                                if option == 's':      # Send message
                                    running = False
                                elif option == 'q':    # Abort editor
                                    running = False
                                    message = None
                                elif win:                   # Keep editing
                                    conn.SendTML(f'<CLR>Select LINE (CRSR UP/DWN)<WINDOW top=3 bottom={scheight-4}><AT x=0 y={line}>')
                                    edit = False
                            tline = fmessage[line+ydisp]
                            column = len(tline)
                else:   # Selecting line to edit
                    if i_char == cursors[1] and (line+ydisp < len(fmessage)-1):
                        line += 1
                        if line <= scheight-8:
                            conn.Sendall(i_char)
                        else:
                            line = scheight-8
                            ydisp += 1
                            scroll = 1
                            updMsg(ydisp,scroll,-1)
                    elif i_char == cursors[0]:
                        if (line > 0):
                            line -= 1
                            conn.Sendall(i_char)
                        elif ydisp > 0:
                            ydisp -= 1
                            scroll = -1
                            updMsg(ydisp,scroll,-1)
                    elif i_char == conn.encoder.nl:
                        edit = True
                        column = 0
                        hl_line()
                        tline = fmessage[line+ydisp]
                        conn.SendTML(f'<WINDOW top={scheight-2} bottom={scheight-1}><CLR>{tline}<HOME>')  # Update edit window
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                _LOG(e,id=conn.id,v=1)
                _LOG(fname+'|'+str(exc_tb.tb_lineno),id=conn.id,v=1)
                running = False
                fmessage = None
                message = None
                conn.connected = False
        conn.SendTML(f'<WINDOW top=0 bottom={scheight}>')
        return(topic,message)
    # check user is logged in
    if conn.username == '_guest_':
        return
    # check destination
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
    topic, message = composer(topic=topic)
    if message != None:
        if type(message) == list:
            i = 0
            while (sum(len(c) for c in message[i:])) > 0:
                i += 1
            msgtxt = _dec('\n'.join(l for l in message[:i]))
        else:
            msgtxt = message
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
        conn.SendTML('<CLR><LTGREEN>Message sent<BELL><PAUSE n=1.5>')
    else:
        _LOG('Messaging: Message cancelled',id=conn.id,v=4)
    return m_id

###############################################################
# Display user private messages (board = 0) or public board
###############################################################
def inbox(conn:Connection, board):
    scwidth,scheight = conn.encoder.txt_geo
    ellipsis = conn.encoder.ellipsis
    if 'MSX' in conn.mode:
        hcode = 0x17
    elif 'ZX' in conn.mode:
        hcode = ord('-')
    else:
        hcode = 0x40
    _dec = conn.encoder.decode
    _enc = conn.encoder.encode
    keys = string.ascii_letters + string.digits + ' +-_,.$%&'
    ckeys = conn.encoder.ctrlkeys
    db:DBase = conn.bbs.database
    conn.SendTML(f'<SETOUTPUT><NUL n=2><TEXT border={conn.style.BoColor} background={conn.style.BgColor}>')
    query = {'msg_board':board,'msg_parent':0}
    q2 = query.copy()
    if board == 0:
        if conn.username != '_guest_':
            title = "Private messages"
            query['msg_to'] = conn.userid   # Threads directed to user
            q2['msg_from'] = conn.userid    # Threads started by user
        else:
            return  # abort if not logged in
    else:
        title = conn.bbs.BoardOptions.get('board'+str(board),'bOARD '+str(board))  # Replace with board title from config.ini
    table = db.db.table('MESSAGES')
    dbQ = Query()
    page = 0
    done = False
    refresh = True
    utable = db.db.table('USERS')
    if 'CRSRU' in ckeys:
        cursors = [ckeys['CRSRU'],ckeys['CRSRD'],ckeys['CRSRL'],ckeys['CRSRR']]
        ctext = 'crsr'
    else:
        cursors = ['a','z','n','m']
        ctext = 'a/z/n/m'
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
            to = crop(i['msg_topic'],scwidth-16,ellipsis)
            tl = table.get(doc_id=i['msg_prev'])
            if type(tl['msg_from'])==int:
                user = utable.get(doc_id = tl['msg_from'])['uname']
            else:
                user = tl['msg_from']
            tu = crop(user,11,ellipsis)
            tt += f'{to}<YELLOW><CRSRR n={(scwidth-16)-len(to)}<VLINE><WHITE>{tu}'
            ts = tl['msg_sent']    # Get timestamp of last message in thread
            threads.append([tt,i.doc_id,um,ts])  # topic - thread_id, first unread, timestamp
        # sort by sent timestamp, newest thread first
        threads.sort(key=lambda threads: threads[3],reverse=True)
        conn.SendTML('<CURSOR>')
        if refresh:
            conn.SendTML(f'<WINDOW top=0 bottom={scheight}>')
            RenderMenuTitle(conn,title)
            if conn.QueryFeature(TT.SET_WIN) >= 0x80:
                win = False
                coff = 3
            else:
                win = True
                coff = 0
            if int(conn.bbs.BoardOptions.get('board'+str(board)+'post',1)) <= conn.userclass:
                tt = f'<RVSON>n<RVSOFF>ew {"thread" if board != 0 else "message"}{"<BR>" if conn.userclass < 10 else "-<RVSON>d<RVSOFF>elete"}'
            else:
                tt = '<BR>' #'\r'
            if conn.QueryFeature(TT.LINE_FILL) < 0x80:
                conn.SendTML(f'<YELLOW><LFILL row={scheight-3} code={hcode}>')
            else:
                conn.SendTML(f'<AT x=0 y={scheight-3}><YELLOW><HLINE n={scwidth}>')
            conn.SendTML(f'<AT x=0 y={scheight-2}><GREY3>Navigate with <RVSON>{ctext}<RVSOFF> - '+ tt +
                         f'<AT x=0 y={scheight-1}>Read <RVSON>f<RVSOFF>irst/<RVSON>l<RVSOFF>ast or <RVSON>u<RVSOFF>nread msg'
                         f'<WINDOW top=3 bottom={scheight-4}>')
            refresh = False
        if win:
            conn.SendTML('<CLR>')
        else:
            conn.SendTML('<AT x=0 y=3>')
        tpp = scheight-6    # threads per page
        last = len(threads) if len(threads) < (tpp*(page+1)) else tpp*(page+1)
        for i in range(tpp*page,last):
            conn.SendTML(threads[i][0])
            if i < last-1:
                conn.SendTML('<BR>')
        conn.SendTML('<CURSOR enable=False><CYAN>')
        pos = 0
        o_pos = 1
        back = conn.encoder.decode(conn.encoder.back)
        while conn.connected:
            if pos != o_pos:
                conn.SendTML(f'<AT x=0 y={pos+coff}>&gt;<CRSRL>')
                o_pos = pos
            k = conn.ReceiveKey(['f','l','u',conn.encoder.back,'n' if tt!= '' else '','d' if conn.userclass == 10 else '']+cursors)
            if len(threads) > 0:
                if k == cursors[1]:
                    if pos+1 < (len(threads)-(tpp*page)):    # move down
                        if pos < scheight-7:
                            pos += 1
                            conn.SendTML(' ')
                        elif len(threads)>(tpp*(page+1)):
                            page +=1
                            if not win:
                                refresh = True
                            break
                elif k == cursors[0]:                   # move up
                    if pos > 0:
                        pos -= 1
                        conn.SendTML(' ')
                    elif page > 0:
                        page -= 1
                        if not win:
                            refresh = True
                        break
                elif k == cursors[3]:                 # next page
                    if len(threads)>(tpp*(page+1)):
                        page +=1
                        if not win:
                            refresh = True
                        break
                elif k == cursors[2]:                # previous page
                    if page > 0:
                        page -= 1
                        if not win:
                            refresh = True
                        break
                elif k == 'f':                  # First message
                    conn.SendTML(f'<CURSOR><WINDOW top=0 bottom={scheight}>')
                    readMessage(conn,threads[pos+(tpp*page)][1])
                    refresh = True
                    break
                elif k == 'l':                  # Last message
                    m = table.get(doc_id=threads[pos+(tpp*page)][1])
                    conn.SendTML(f'<CURSOR><WINDOW top=0 bottom={scheight}>')
                    readMessage(conn,m['msg_prev'])
                    refresh = True
                    break
                elif k == 'u':                  # First unread message
                    if threads[pos+(tpp*page)][2] != None:
                        conn.SendTML(f'<CURSOR><WINDOW top=0 bottom={scheight}>')
                        readMessage(conn,threads[pos+(tpp*page)][2].doc_id)
                        refresh = True
                        break
                elif k == 'd':                 # Delete thread
                    tml = ''
                    if conn.QueryFeature(TT.LINE_FILL) < 0x80:
                        tml += f'<RED><LFILL row=10 code={hcode}><LFILL row=14 code={hcode}>'
                    else:
                        tml += f'<RED><AT x=0 y=10><HLINE n={scwidth}><AT x=0 y=14><HLINE n={scwidth}>'
                    if conn.QueryFeature(TT.SET_WIN) < 0x80:
                        tml += '<WINDOW top = 11 bottom =13><CLR><CRSRD>'
                    else:
                        tml += f'<AT x=0 y=11><SPC n={scwidth-1}><DEL> <BR><SPC n={scwidth-1}><DEL> <BR><SPC n={scwidth-1}><DEL> <BR><CRSRU n=2>'
                    conn.SendTML(tml+f'<WHITE><SPC n={(scwidth-20)//2}>Delete thread?(Y/N)')
                    if conn.ReceiveKey('yn') == 'y':
                        deleteThread(conn,threads[pos+(tpp*page)][1])
                    refresh = True
                    break
            if k == 'n':              # new thread
                conn.SendTML('<CURSOR>')
                if board == 0:
                    # get destination username
                    tml = ''
                    if conn.QueryFeature(TT.SET_WIN) < 0x80:
                        if conn.QueryFeature(TT.LINE_FILL) < 0x80:
                            tml += f'<LFILL row=10 code={hcode}><LFILL row=14 code={hcode}>'
                        else:
                            tml += f'<AT x=0 y=10><HLINE n={scwidth}><AT x=0 y=14><HLINE n={scwidth}>'
                    conn.SendTML(tml+'<WINDOW top=11 bottom=13>')
                    while conn.connected:
                        conn.SendTML('<CLR>Send PM to: ')
                        dest = _dec(conn.ReceiveStr(keys, 16, False))
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
                                    if conn.ReceiveKey('yn') == 'y':
                                        dest = match
                                        break
                            else:
                                break
                        elif dest == '':
                            break
                else:
                    dest = board
                conn.SendTML(f'<WINDOW top=0 bottom={scheight}>')
                if dest != '':
                    writeMessage(conn, destination=dest)
                refresh = True
                break
            if k == conn.encoder.back:
                conn.SendTML(f'<CURSOR><WINDOW top=0 bottom={scheight}>')
                done = True
                break

#################################################
# Toggle the read status of a private message
#################################################
def toggleRead(conn:Connection, msg_id):
    ...

###################################
# Get number of unread messages
###################################
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

################################################
# Get first unread message in a given thread
################################################
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

############################
# Delete thread
# Limited to admin users
############################
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

############################
# Delete message
# Limited to admin users
############################
def deleteMessage(conn:Connection,msg=0):
    m_id = 0
    if msg != 0 and conn.userclass == 10:
        table = conn.bbs.database.db.table('MESSAGES')
        dmsg = table.get(doc_id = msg)
        if dmsg != None:
            if dmsg['msg_parent'] == 0: # This is the first post in the thread, delete whole thread
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


##############################################################################
# Similar to formatX, but doesn't escape/unescape html entities
# Wordwrap the input text the given columns
# Preserves carriage returns
# Return a list of text lines and a list of start-end indices and wordwrap
# status for each line
##############################################################################
def formatMsg(text, columns = 40):
    output = []
    for i in text.replace('\n','\b\n').split('\n'):
        if i != '':
            if len(i) == columns+1 and i[-1] in [' ','\b']:
                output.append(i)
                output.append('')
            else:
              output.extend(textwrap.wrap(i,width=columns))
              if i[-1] == ' ':
                  output.append('')
        else:
            output.extend([''])
    lines = []
    ip = 0
    op = 0
    for i in range(len(output)):
        lwrap = False
        output[i] = output[i].replace('\b','\n')
        op = ip+len(output[i])
        if op < len(text):
            if text[op-1] != '\n':
                while text[op] == ' ':
                    op +=1
                    lwrap = True        # trailing space word-wrapped
                    if  op == len(text):
                        break
        lines.extend([[ip,op,lwrap]])
        ip = op
    return(output,lines)

##############
# TML tags
##############
t_mono = {'UNREAD':(lambda c:unreadCount(c),[('_R','_A'),('c','_C')])}
