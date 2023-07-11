import json
import string

from common import style as S
from common.connection import Connection
from common import turbo56k as TT

###############
# Plugin setup
###############
def setup():
    fname = "ONELINER" #UPPERCASE function name for config.ini
    parpairs = [] #config.ini Parameter pairs (name,defaultvalue)
    return(fname,parpairs)
#############################

###################################
# Plugin  function
###################################
def plugFunction(conn:Connection):

    _dec = conn.encoder.decode
    keys = string.ascii_letters + string.digits + " !?';:[]()*/@+-_,.$%&"
    try:
        f = open('plugins/oneliner.seq','rb')
        title = f.read()
        conn.Sendallbin(title)
    except:
        S.RenderMenuTitle(conn,'Oneliner')
        conn.SendTML('<PURPLE>')
    if conn.QueryFeature(TT.LINE_FILL) < 0x80:
        conn.Sendall(TT.Fill_Line(3,192)+TT.Fill_Line(22,192)) # Window borders
    else:
        conn.SendTML('<AT x=0 y=3><RVSON><HLINE n=40><AT x=0 y=22><HLINE n=40><RVSOFF>')
    refr = True
    while conn.connected:
        conn.SendTML(f'<WINDOW top=23 bottom=24><CLR><KPROMPT t=RETURN><GREEN>to enter message {S.KeyPrompt(conn,"<LARROW>",TML=True)}<GREEN>to go back')
        if refr == True:
            try:
                olf = open('plugins/oneliners.json','r')
                onelines = json.load(olf)
                olf.close()
            except:
                onelines = []
            sendOneliners(conn, onelines)
            refr = False
        comm = conn.ReceiveKey(b'\r_')
        if comm == b'_':
            break
        conn.SendTML('<WINDOW top=23 bottom=24><CLR>')
        if conn.userclass > 0:
            nick = conn.username
        else:
            conn.SendTML('<GREEN>Nick: <WHITE>')
            nick = _dec(conn.ReceiveStr(bytes(keys,'ascii'),20))
        if nick != '':
            conn.SendTML('<CLR><GREEN>Message:<BR><WHITE>')
            line = _dec(conn.ReceiveStr(bytes(keys,'ascii'), 39))
            if line != '':
                try:    # Refresh oneliners in case another user posted in the meanwhile
                    olf = open('plugins/oneliners.json','r')
                    onelines = json.load(olf)
                    olf.close()
                except:
                    onelines = []
                onelines.append([nick,line])
                if len(onelines) > 9:
                    onelines.pop(0) #If there's more than 9 onelines, remove the oldest.
                olf = open('plugins/oneliners.json','w')        
                json.dump(onelines,olf)
                olf.close()
                refr = True
    conn.Sendall(TT.set_Window(0,24))

##########################################
# Send oneliners to connection
##########################################
def sendOneliners(conn:Connection,lines):
    conn.SendTML('<WINDOW top=4 bottom=21><CLR>')
    for i,l in enumerate(lines):
        conn.SendTML(f'<YELLOW>{l[0]} says:<BR><GREY3>{l[1]}')
        if len(l[1]) and i<8:
            conn.SendTML('<BR>')
        if i == 8:  #Just in case the json file has more than 9 entries
            continue
