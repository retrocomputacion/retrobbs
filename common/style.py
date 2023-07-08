########### Style ############
# Quite lean for now
from common.connection import Connection
from common import turbo56k as TT
from common import helpers as H
from common.classes import bbsstyle

default_style = bbsstyle()

# # Default colors (in c64 palette index)
# default_style.BgColor		= P.PALETTE[P.BLACK]		#Background color
# default_style.BoColor		= P.PALETTE[P.BLACK]		#Border color
# default_style.TxtColor		= P.PALETTE[P.GREY3]		#Main text color
# default_style.HlColor		= P.PALETTE[P.WHITE]		#Highlight text color
# default_style.RvsColor		= P.PALETTE[P.LT_GREEN]		#Reverse text color
# ### Menu specific colors ###
# default_style.OoddColor		= P.PALETTE[P.LT_BLUE]		#Odd option key color
# default_style.ToddColor		= P.PALETTE[P.GREY3]		#Odd option text color
# default_style.OevenColor	= P.PALETTE[P.CYAN]			#Even option key color
# default_style.TevenColor	= P.PALETTE[P.YELLOW]		#Even option text color
# default_style.MenuTColor1	= P.PALETTE[P.CYAN]			#Menu title border color 1
# default_style.MenuTColor2	= P.PALETTE[P.LT_GREEN]		#Menu title border color 2
# default_style.SBorderColor1	= P.PALETTE[P.LT_GREEN]		#Section border color 1
# default_style.SBorderColor2	= P.PALETTE[P.GREEN]		#Section border color 1
# ### [Prompt] ###
# default_style.PbColor		= P.PALETTE[P.YELLOW]		#Key prompt brackets color
# default_style.PtColor		= P.PALETTE[P.LT_BLUE]		#Key prompt text color

def RenderMenuTitle(conn:Connection,title):
    if type(title) == tuple:
        title = title[0]
    st = conn.style
    # Clear screen
    tml = '<CLR><LOWER>'
    # Send menu title
    if conn.QueryFeature(TT.LINE_FILL) < 0x80:
        tml += f'''<INK c={st.MenuTColor2}><LFILL row=0 code=64><LFILL row=2 code=64><RVSON><INK c={st.MenuTColor1}><CBM-U><RVSOFF><LET _R=_I x=0><WHILE c='_I<19'><CRSRR><HLINE><INC></WHILE><INK c={st.MenuTColor2}><RVSON><CBM-U>'''
    else:
        tml += f'''<RVSON><INK c={st.MenuTColor1}><CBM-U><RVSOFF><LET _R=_I x=0><WHILE c='_I<19'><INK c={st.MenuTColor2}><HLINE><INK c={st.MenuTColor1}><HLINE><INC></WHILE><INK c={st.MenuTColor2}><RVSON><CBM-U>'''
    tml += f''' <RVSOFF><INK c={st.HlColor}> {(conn.bbs.name[:19]+" - "+ title+(" "*33)[:37]+"  ")[:36]} <RVSON><INK c={st.MenuTColor1}> '''
    if conn.QueryFeature(TT.LINE_FILL) < 0x80:
        tml += f'''<RVSON><INK c={st.MenuTColor1}><CBM-O><RVSOFF><LET _R=_I x=0><WHILE c='_I<19'><CRSRR><HLINE><INC></WHILE><INK c={st.MenuTColor2}><RVSON><CBM-O><RVSOFF>'''
    else:
        tml += f'''<RVSON><INK c={st.MenuTColor1}><CBM-O><RVSOFF><LET _R=_I x=0><WHILE c='_I<19'><INK c={st.MenuTColor2}><HLINE><INK c={st.MenuTColor1}><HLINE><INC></WHILE><INK c={st.MenuTColor2}><RVSON><CBM-O><RVSOFF>'''
    conn.SendTML(tml)

# Returns '[text]' prompt string in the selected style
# TML: True to return TML sequence
# Usage:
# def KeyPrompt(text, style=default_style, TML=False):
#
# or
#
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
    if style == None:
        style = conn.style
    tml = ''
    if key >= '\r':
        if key == '_':		# FIXME: Workaround for PETSCII left arrow character
            key = '<LARROW>'
        tml += f'<INK c={c1}><RVSON><CHR c=181>{key.lower()}<CHR c=182><RVSOFF>'
    tml += f'<INK c={c2}>{label}'
    conn.SendTML(tml)
    return not toggle

# Render 'file' dialog background
def RenderDialog(conn:Connection,height,title=None):
    conn.SendTML('<CLR><GREY3><RVSON>')
    if conn.QueryFeature(TT.LINE_FILL) < 0x80:
        conn.SendTML('<LFILL row=0 code=192>')
        conn.Sendall(chr(TT.CMDON))
        for y in range(1,height):
            conn.Sendall(chr(TT.LINE_FILL)+chr(y)+chr(160))
        conn.Sendall(chr(TT.CMDOFF))
        conn.SendTML(f'<GREY1><LFILL row={height} code=226><GREY3>')
    else:
        conn.SendTML(f'<HLINE n=40><SPC n={40*height-1}><GREY1>{chr(162)*40}<HOME><GREY3>')
    if title != None:
        ctt = H.crop(title,38)
        conn.SendTML(f'<AT x={1+(38-len(ctt))/2} y=0>{ctt}<BR>')

################################################################
# TML tags
t_mono = {	'MTITLE':(lambda c,t:RenderMenuTitle(c,t),[('c','_C'),('t','')]),
              'KPROMPT':(KeyPrompt,[('_R','_C'),('c','_C'),('t','RETURN')]),
            'DIALOG':(lambda c,h,t:RenderDialog(c,h,t),[('c','_C'),('h',4),('t','')])}
