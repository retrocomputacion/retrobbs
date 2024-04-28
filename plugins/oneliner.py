import json
import string
from math import ceil

from common import style as S
from common.connection import Connection
from common import turbo56k as TT
from common.helpers import crop

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
        if 'PET' in conn.mode:
            f = open('plugins/oneliner.seq','rb')
            title = f.read()
            conn.Sendallbin(title)
        else:
            raise ValueError('Not PET')
    except:
        S.RenderMenuTitle(conn,'Oneliner')
        conn.SendTML('<PURPLE>')
    scwidth,scheight = conn.encoder.txt_geo
    if conn.QueryFeature(TT.LINE_FILL) < 0x80:
        if 'MSX' in conn.mode:
            conn.SendTML(f'<CURSOR n=0><PAPER c=13><INK c=15><LFILL row=3 code=23><LFILL row={scheight-3} code=23><PAPER c={conn.style.BgColor}>')
        else:
            conn.Sendall(TT.Fill_Line(3,192)+TT.Fill_Line(scheight-3,192)) # Window borders
    else:
        conn.SendTML(f'<AT x=0 y=3><RVSON><HLINE n={scwidth}><AT x=0 y={scheight-3}><HLINE n={scwidth}><RVSOFF>')
    refr = True
    while conn.connected:
        conn.SendTML(f'<WINDOW top={scheight-2} bottom={scheight-1}><CLR><KPROMPT t=RETURN><GREEN>new message {S.KeyPrompt(conn,"<BACK>",TML=True)}<GREEN>exit')
        if refr == True:
            try:
                olf = open('plugins/oneliners.json','r')
                onelines = json.load(olf)
                olf.close()
            except:
                onelines = []
            sendOneliners(conn, onelines)
            refr = False
        comm = conn.ReceiveKey(conn.encoder.back+conn.encoder.nl)
        if comm == conn.encoder.back:
            break
        conn.SendTML(f'<WINDOW top={scheight-2} bottom={scheight-1}><CLR>')
        if conn.userclass > 0:
            nick = conn.username
        else:
            conn.SendTML('<GREEN>Nick: <WHITE>')
            nick = _dec(conn.ReceiveStr(bytes(keys,'ascii'),20))
        if nick != '':
            conn.SendTML('<CLR><GREEN>Message:<BR><WHITE>')
            line = _dec(conn.ReceiveStr(bytes(keys,'ascii'), scwidth-1))
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
    # count = ceil(conn.encoder.txt_geo[0]/3)-1
    conn.SendTML(f'<WINDOW top=4 bottom={conn.encoder.txt_geo[1]-4}><CLR>')
    for i,l in enumerate(lines):
        if 'MSX' in conn.mode:
            txtc = '<GREY>'
        else:
            txtc = '<GREY3>'
        line = crop(l[1],conn.encoder.txt_geo[0],conn.encoder.ellipsis)
        conn.SendTML(f'<YELLOW>{l[0]} says:<BR>{txtc}{line}')
        if (i<8) and (len(line)<conn.encoder.txt_geo[0]):
            conn.SendTML('<BR>')
        if i == 8:  #Just in case the json file has more than 9 entries
            break
