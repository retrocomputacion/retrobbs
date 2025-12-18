import json
import string
import os
from math import ceil

from common import style as S
from common.connection import Connection
from common import turbo56k as TT
from common.helpers import crop

##################
# Plugin setup
##################
def setup():
    fname = "ONELINER"  # UPPERCASE function name for config.ini
    parpairs = [] # config.ini Parameter pairs (name,defaultvalue)
    return(fname,parpairs)

######################
# Plugin  function
######################
def plugFunction(conn:Connection):

    def header():
        conn.SendTML(conn.templates.GetTemplate('oneliner/title',**{}))
        if conn.QueryFeature(TT.LINE_FILL) < 0x80:
            if 'MSX' in conn.mode:
                conn.SendTML(f'<CURSOR enable=False><PAPER c=13><WHITE><LFILL row=3 code=23><LFILL row={scheight-3} code=23><PAPER c={conn.style.BgColor}><CURSOR>')
            else:
                conn.SendTML(f'<PURPLE><LFILL row=3 code=192><LFILL row={scheight-3} code=192>') # Window borders
        else:
            conn.SendTML(f'<PURPLE><AT x=0 y=3><RVSON><HLINE n={scwidth}>')
            if conn.T56KVer > 0:
                conn.SendTML(f'<AT x=0 y={scheight-3}><HLINE n={scwidth}><RVSOFF>')
            else:
                conn.SendTML('<RVSOFF>')
 
    _dec = conn.encoder.decode
    keys = string.ascii_letters + string.digits + " !?';:[]()*/@+-_,.$%&"
    scwidth,scheight = conn.encoder.txt_geo
    if conn.T56KVer > 0:
        header()
    refr = True
    while conn.connected:
        if conn.T56KVer == 0 and refr:
            header()
        if refr == True:
            onelines = getOneliners()
            sendOneliners(conn, onelines)
            refr = False
        if conn.T56KVer > 0:
            conn.SendTML(f'<WINDOW top={scheight-2} bottom={scheight-1}><CLR>')
        else:
            conn.SendTML('<BR>')
        conn.SendTML(f'<KPROMPT t=RETURN><GREEN>new message <KPROMPT t={conn.encoder.back}><GREEN>exit')
        if conn.userclass == 10:    # Admin
            conn.SendTML(' <KPROMPT t=D><GREEN>elete')
            adm = 'd'
        else:
            adm = ''
        back = conn.encoder.decode(conn.encoder.back)
        comm = conn.ReceiveKey(back+conn.encoder.nl+adm)
        if comm == back:
            break
        elif comm == conn.encoder.nl:
            if conn.encoder.features['windows'] > 0:
                conn.SendTML('<CLR>')
            else:
                conn.SendTML('<BR>')
            if conn.userclass > 0:
                nick = conn.username
            else:
                conn.SendTML('<GREEN>Nick: <WHITE>')
                nick = _dec(conn.ReceiveStr(keys,20))
            if nick != '':
                if conn.T56KVer > 0:
                    conn.SendTML('<CLR>')
                else:
                    conn.SendTML('<BR>')
                conn.SendTML('<GREEN>Message:<BR><WHITE>')
                line = _dec(conn.ReceiveStr(keys, scwidth-1))
                if line != '':
                    onelines = getOneliners()
                    onelines.append([nick,line])
                    if len(onelines) > 9:
                        onelines.pop(0) # If there's more than 9 onelines, remove the oldest.
                    saveOneliners(onelines)
                    refr = True
                elif conn.encoder.features['windows'] == 0:
                    refr = True
        else:   # Admin delete messages
            onelines = getOneliners()
            if conn.encoder.features['windows'] > 0:
                conn.SendTML(f'<WINDOW top =4 bottom={conn.encoder.txt_geo[1]}><CLR>')
            else:
                conn.SendTML('<BR><WHITE>')
            for i,l in enumerate(onelines):
                line = crop(f'{l[0]} - {l[1]}', conn.encoder.txt_geo[0]-4, conn.encoder.ellipsis)
                conn.SendTML(f'{i}: {line}<BR>')
            conn.SendTML('Select message to delete: ')
            msg = conn.ReceiveKey(list(str(i) for i in range(len(onelines)-1)))
            conn.SendTML(f'{msg}<BR><BR>Are you sure (Y/N)?')
            if conn.ReceiveKey('yn') == 'y':
                del(onelines[int(msg)])
                saveOneliners(onelines)
            refr = True


    conn.SendTML(f'<WINDOW top=0 bottom={scheight}>')

##################################
# Send oneliners to connection
##################################
def sendOneliners(conn:Connection,lines):
    conn.SendTML(f'<WINDOW top=4 bottom={conn.encoder.txt_geo[1]-4}>')
    if conn.T56KVer > 0:
        conn.SendTML('<CLR>')
    for i,l in enumerate(lines):
        if 'MSX' in conn.mode:
            txtc = '<GREY>'
        else:
            txtc = '<GREY3>'
        line = crop(l[1],conn.encoder.txt_geo[0],conn.encoder.ellipsis)
        conn.SendTML(f'<YELLOW>{l[0]} says:<BR>{txtc}{line}')
        if (i<8) and (len(line)<conn.encoder.txt_geo[0]):
            conn.SendTML('<BR>')
        if i == 8:  # Just in case the json file has more than 9 entries
            break

#######################
# Get the oneliners
#######################
def getOneliners():
    try:    # Refresh oneliners in case another user posted in the meanwhile
        olf = open('plugins/oneliners.json','r')
        onelines = json.load(olf)
        olf.close()
    except:
        onelines = []
    return onelines

########################
# Save the oneliners
########################
def saveOneliners(onelines):
    with open('plugins/oneliners.json','w') as olf:
        json.dump(onelines,olf,indent=4)
        olf.flush()
        os.fsync(olf.fileno())  # Make sure the file is updated on disk
