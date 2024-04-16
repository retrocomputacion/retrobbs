########### Style ############
# Quite lean for now
from common.connection import Connection
from common import turbo56k as TT
from common import helpers as H
from common.classes import bbsstyle

default_style = bbsstyle()

def RenderMenuTitle(conn:Connection,title):
    if type(title) == tuple:
        title = title[0]
    st = conn.style
    # Clear screen
    tml = '<CLR><RVSOFF>'
    # Get screen width
    scwidth = conn.encoder.txt_geo[0]
    if 'MSX' in conn.mode:
        cfill = 0x17
        ucorner = '<B-HALF>'
        bcorner = '<RVSON><B-HALF><RVSOFF>'
    else:
        cfill = 64
        tml += '<LOWER>'
        ucorner = '<RVSON><U-NARROW><RVSOFF>'
        bcorner = '<RVSON><B-NARROW><RVSOFF>'
    # Send menu title
    if conn.QueryFeature(TT.LINE_FILL) < 0x80:
        tml += f'''<INK c={st.MenuTColor2}><LFILL row=0 code={cfill}><LFILL row=2 code={cfill}><INK c={st.MenuTColor1}>{ucorner}<LET _R=_I x=0><WHILE c='_I<{(scwidth//2)-1}'><CRSRR><HLINE><INC></WHILE><INK c={st.MenuTColor2}>{ucorner}'''
    else:
        tml += f'''<INK c={st.MenuTColor1}>{ucorner}<LET _R=_I x=0><WHILE c='_I<{(scwidth//2)-1}'><INK c={st.MenuTColor2}><HLINE><INK c={st.MenuTColor1}><HLINE><INC></WHILE><INK c={st.MenuTColor2}>{ucorner}'''
    tml += f'''<RVSON> <RVSOFF><INK c={st.HlColor}> {(conn.bbs.name[:(scwidth//2)-1]+" - "+ title+(" "*(scwidth-7))[:scwidth-3]+"  ")[:scwidth-4]} <INK c={st.MenuTColor1}><RVSON> <RVSOFF>'''
    if conn.QueryFeature(TT.LINE_FILL) < 0x80:
        tml += f'''<INK c={st.MenuTColor1}>{bcorner}<LET _R=_I x=0><WHILE c='_I<{(scwidth//2)-1}'><CRSRR><HLINE><INC></WHILE><INK c={st.MenuTColor2}>{bcorner}'''
    else:
        tml += f'''<INK c={st.MenuTColor1}>{bcorner}<LET _R=_I x=0><WHILE c='_I<{(scwidth//2)-1}'><INK c={st.MenuTColor2}><HLINE><INK c={st.MenuTColor1}><HLINE><INC></WHILE><INK c={st.MenuTColor2}>{bcorner}'''
    conn.SendTML(tml)

# Returns '[text]' prompt string in the selected style
# TML: True to return TML sequence
def KeyPrompt(conn:Connection, text, style=default_style, TML=False):
    if style != None:
        style = conn.style
    pal = conn.encoder.palette
    if TML:
        return(f'<INK c={style.PbColor}>[<INK c={style.PtColor}>{text}<INK c={style.PbColor}>]')
    else:
        if conn.QueryFeature(0xb7) >= 0x80:																			# Update INK command
            tmp = pal.items()
            bc = chr([k for k,v in tmp if v == style.PbColor][0] if len([k for k,v in tmp if v == style.PbColor])>0 else 0)
            tc = chr([k for k,v in tmp if v == style.PtColor][0] if len([k for k,v in tmp if v == style.PtColor])>0 else 0)
        else:
            bc = chr(TT.CMDON)+chr(TT.INK)+chr(style.PbColor)
            tc = chr(TT.CMDON)+chr(TT.INK)+chr(style.PtColor)
        return(bc+'['+tc+conn.encoder.encode(text,False)+bc+']')

# Renders a menu option in the selected style  
def KeyLabel(conn:Connection, key:str, label:str, toggle:bool, style:bbsstyle=None):
    if style == None:
        style = conn.style
    c1 = style.OevenColor if toggle else style.OoddColor
    c2 = style.TevenColor if toggle else style.ToddColor
    if (style.OevenBack != style.BgColor) or (style.OoddBack != style.BgColor):
        bg1 = f'<PAPER c={style.OevenBack if toggle else style.OoddBack}>'
        bg = f'<PAPER c={style.BgColor}>'
    else:
        bg = bg1 = ''
    if style == None:
        style = conn.style
    tml = ''
    if 'MSX' in conn.mode:
        lside = '<L-HALF>'
        rside = '<RVSOFF><TRI-LEFT>'
    else:
        lside = '<L-NARROW>'
        rside = '<R-NARROW><RVSOFF>'
    if key >= '\r':
        if key == '_':		# FIXME: Workaround for PETSCII left arrow character
            key = '<BACK>'
        tml += f'<INK c={c1}><RVSON>{lside}{bg1}{key.lower()}{bg}{rside}'
    tml += f'<INK c={c2}>{label}'
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
        conn.SendTML(f'<HLINE n={scwidth}><SPC n={scwidth*height-1}>{grey1}<B-HALF n={scwidth}><HOME>{grey3}')
    if title != None:
        ctt = H.crop(title,scwidth-2,conn.encoder.ellipsis)
        conn.SendTML(f'<AT x={1+((scwidth-2)-len(ctt))/2} y=0>{ctt}<BR>')

###########
# TML tags
###########
t_mono = {	'MTITLE':(lambda c,t:RenderMenuTitle(c,t),[('c','_C'),('t','')]),
              'KPROMPT':(KeyPrompt,[('_R','_C'),('c','_C'),('t','RETURN')]),
            'DIALOG':(lambda c,h,t:RenderDialog(c,h,t),[('c','_C'),('h',4),('t','')])}
