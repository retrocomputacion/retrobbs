########### Style ############
# Quite lean for now
from common.connection import Connection
from common import turbo56k as TT
from common import helpers as H
from common.classes import bbsstyle

# default_style = bbsstyle()

def RenderMenuTitle(conn:Connection, title, style:bbsstyle=None):
    if type(title) == tuple:
        title = title[0]
    parms = {'title':title}
    if style != None:
        parms['st':style]
    tml = conn.templates.GetTemplate('main/menutitle',**parms)
    conn.SendTML(tml)

# Returns '[text]' prompt string in the selected style
# TML: True to return TML sequence
def KeyPrompt(conn:Connection, text, style:bbsstyle=None, TML=False):
    if style == None:
        style = conn.style
    pal = conn.encoder.palette
    if pal != {}:
        if TML:
            return(f'<INK c={style.PbColor}>[<INK c={style.PtColor}>{text}<INK c={style.PbColor}>]')
        else:
            if conn.QueryFeature(TT.INK) >= 0x80:																			# Update INK command
                tmp = pal.items()
                bc = [k for k,v in tmp if v == style.PbColor][0] if len([k for k,v in tmp if v == style.PbColor])>0 else ''
                tc = [k for k,v in tmp if v == style.PtColor][0] if len([k for k,v in tmp if v == style.PtColor])>0 else ''
            else:
                bc = chr(TT.CMDON)+chr(TT.INK)+chr(style.PbColor)
                tc = chr(TT.CMDON)+chr(TT.INK)+chr(style.PtColor)
            return(bc+'['+tc+conn.encoder.encode(text,False)+bc+']')
    else:
        return(f'[{text}]')

# Renders a menu option in the selected style  
def KeyLabel(conn:Connection, key:str, label:str, toggle:bool, style:bbsstyle=None):
    parms = {'key':key, 'label':label, 'toggle':toggle}
    if style != None:
        parms['st'] = style
    tml = conn.templates.GetTemplate('main/keylabel',**parms)
    conn.SendTML(tml)
    return not toggle

#####################################################
# Render 'file' dialog background
#####################################################
def RenderDialog(conn:Connection,height,title=None):
    if 'MSX' in conn.mode:
        grey1 = '<GREY>'
        grey3 = '<WHITE>'
    else:
        grey1 = '<GREY1>'
        grey3 = '<GREY3>'
    conn.SendTML(f'<CLR>{grey3}<RVSON>')
    scwidth = conn.encoder.txt_geo[0]
    if conn.QueryFeature(TT.LINE_FILL) < 0x80:
        if 'MSX' in conn.mode:
            cfill = 0x17
        else:
            cfill = 192
        conn.SendTML(f'<LFILL row=0 code={cfill}>')
        conn.Sendall(chr(TT.CMDON))
        if 'MSX' in conn.mode:
            cfill = 0x20
        else:
            cfill = 160
        for y in range(1,height):
            conn.Sendall(chr(TT.LINE_FILL)+chr(y)+chr(cfill))
        conn.Sendall(chr(TT.CMDOFF))
        if 'MSX' in conn.mode:
            conn.SendTML(f'{grey1}<LFILL row={height} code={0xdc}>{grey3}')
        else:
            conn.SendTML(f'{grey1}<LFILL row={height} code={226}>{grey3}')        
    else:
        conn.SendTML(f'<HLINE n={scwidth-1}><CRSRL><INS><HLINE><CRSRR>')
        conn.SendTML(f'<LET x=0><WHILE c="_I!={height-1}"><SPC n={scwidth-1}><CRSRL><INS> <CRSRR><INC></WHILE>{grey1}<B-HALF n={scwidth}><HOME>{grey3}')
        # conn.SendTML(f'<HLINE n={scwidth}><SPC n={scwidth*(height-1)}>{grey1}<B-HALF n={scwidth}><HOME>{grey3}')
    if title != None:
        ctt = H.crop(title,scwidth-2,conn.encoder.ellipsis)
        conn.SendTML(f'<AT x={1+((scwidth-2)-len(ctt))/2} y=0>{ctt}<BR>')

###########
# TML tags
###########
t_mono = {	'MTITLE':(lambda c,t:RenderMenuTitle(c,t),[('c','_C'),('t','')]),
              'KPROMPT':(KeyPrompt,[('_R','_C'),('c','_C'),('t','RETURN'),('style',None),('tml','False')]),
            'DIALOG':(lambda c,h,t:RenderDialog(c,h,t),[('c','_C'),('h',4),('t','')])}
