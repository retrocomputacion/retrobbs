#!/usr/bin/env python3
import requests
from common.connection import Connection

idBot = '5417963401:AAEccO2JhiivQUGtXCoN8_xRVggvqUPg8Ag' #bot sotanomsxbbs
idGrupo = '-1001815725036' #id mis cosas
#idGrupo = '-1001769522024' #id sotano chat

###############
# Plugin setup
###############
def setup():
    fname = "LOGINBOT" #UPPERCASE function name for config.ini
    parpairs = [] #config.ini Parameter pairs (name,defaultvalue)
    return(fname,parpairs)
#############################

def enviarMensaje(mensaje):
    requests.post('https://api.telegram.org/bot' + idBot + '/sendMessage',
              data={'chat_id': idGrupo, 'text': mensaje, 'parse_mode': 'HTML'})

def enviarDocumento(ruta):
    requests.post('https://api.telegram.org/bot' + idBot + '/sendDocument',
              files={'document': (ruta, open(ruta, 'rb'))},
              data={'chat_id': idGrupo, 'caption': 'atd "sotanomsxbbs.org:6400"'})

###################################
# Plugin  function
###################################
def plugFunction(conn:Connection):

    enviarMensaje("New login at Retro_Sotano_Msx_BBS !!! ")
    enviarDocumento("/home/x1pepe/retrobbs-MSX-support/plugins/retrobbsbot/RetroBBS Sotano Msx BBS.jpg")
    enviarMensaje("Build your own WIFI modem at: http://www.pastbytes.com/wifimodem/?fbclid=IwY2xjawEhQh1leHRuA2FlbQIxMQABHUMYThlRnsTdFzGAYwAIdMPAXVfHmYj9ZeFnZ35xGOD53qlc1IxEOHD2Wg_aem_u5bfEnkYbuERIL3r_F6vSw#msx")





#define CHAT_ID "-1001769522024" // ID del grupo "Sotano chat"
#define CHAT_ID "-1001815725036" // ID del grupo "Mis cosas"
