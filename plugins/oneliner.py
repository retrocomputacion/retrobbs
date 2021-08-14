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
def plugFunction(conn):

    keys = string.ascii_letters + string.digits + " !?';:[]()*/@+-_,.$%&"

    try:
        f = open('plugins/oneliner.seq','rb')
        title = f.read()
        conn.Sendallbin(title)
    except:
        S.RenderMenuTitle(conn,'oNELINER')
        conn.Sendall(chr(P.PURPLE))
    conn.Sendall(TT.Fill_Line(3,192)+TT.Fill_Line(22,192)) # Window borders
 
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
            #print(onelines)
            sendOneliners(conn, onelines)
            refr = False

        comm = conn.ReceiveKey(b'\r_')
        if comm == b'_':
            break
        conn.Sendall(TT.set_Window(23,24)+chr(P.CLEAR))
        conn.Sendall(chr(P.GREEN)+'nICK: '+chr(P.WHITE))
        nick = conn.ReceiveStr(bytes(keys,'ascii'),20)
        if nick != '':
            conn.Sendall(chr(P.CLEAR)+chr(P.GREEN)+'mESSAGE:\r'+chr(P.WHITE))
            line = conn.ReceiveStr(bytes(keys,'ascii'), 39)
            if line != '':
                onelines.append([nick,line])
                #print(onelines)
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
    i = 0
    for l in lines:
        conn.Sendall(chr(P.YELLOW)+l[0]+' SAYS:\r'+chr(P.GREY3)+l[1])
        if len(l[1]) and i<8:
            conn.Sendall('\r')
        i+=1
        if i == 9:  #Just in case the json file has more than 9 entries
            continue
