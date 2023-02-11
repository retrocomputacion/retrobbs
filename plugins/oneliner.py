import json
import string

from common.bbsdebug import _LOG,bcolors
import common.helpers as H
import common.style as S
from common.connection import Connection
import common.petscii as P
import common.turbo56k as TT


#############################
#Plugin setup
def setup():
    fname = "ONELINER" #UPPERCASE function name for config.ini
    parpairs = [] #config.ini Parameter pairs (name,defaultvalue)
    return(fname,parpairs)
#############################

 

##########################################
#Plugin callable function
def plugFunction(conn:Connection):

    keys = string.ascii_letters + string.digits + " !?';:[]()*/@+-_,.$%&"

    try:
        f = open('plugins/oneliner.seq','rb')
        title = f.read()
        conn.Sendallbin(title)
    except:
        S.RenderMenuTitle(conn,'Oneliner')
        conn.Sendall(chr(P.PURPLE))
    if conn.QueryFeature(TT.LINE_FILL) < 0x80:
        conn.Sendall(TT.Fill_Line(3,192)+TT.Fill_Line(22,192)) # Window borders
    else:
        conn.Sendall(TT.set_CRSR(0,3)+chr(P.RVS_ON)+(chr(P.HLINE)*40))
        conn.Sendall(TT.set_CRSR(0,22)+(chr(P.HLINE)*40)+chr(P.RVS_OFF))

    refr = True
    while conn.connected:
        conn.Sendall(TT.set_Window(23,24)+chr(P.CLEAR)+S.KeyPrompt('return')+chr(P.GREEN)+"TO ENTER MESSAGE "+S.KeyPrompt('_')+chr(P.GREEN)+"TO GO BACK")
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
        conn.Sendall(TT.set_Window(23,24)+chr(P.CLEAR))
        if conn.userclass > 0:
            nick = conn.username
        else:
            conn.Sendall(chr(P.GREEN)+'nICK: '+chr(P.WHITE))
            nick = P.toASCII(conn.ReceiveStr(bytes(keys,'ascii'),20))
        if nick != '':
            conn.Sendall(chr(P.CLEAR)+chr(P.GREEN)+'mESSAGE:\r'+chr(P.WHITE))
            line = P.toASCII(conn.ReceiveStr(bytes(keys,'ascii'), 39))
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
######################

def sendOneliners(conn,lines):
    conn.Sendall(TT.set_Window(4,21)+chr(P.CLEAR))
    for i,l in enumerate(lines):
        conn.Sendall(chr(P.YELLOW)+P.toPETSCII(l[0])+' SAYS:\r'+chr(P.GREY3)+P.toPETSCII(l[1]))
        if len(l[1]) and i<8:
            conn.Sendall('\r')
        if i == 8:  #Just in case the json file has more than 9 entries
            continue
