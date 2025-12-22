########### Style ############
# Quite lean for now
from common.connection import Connection
from common import turbo56k as TT
from common import helpers as H
from common.classes import bbsstyle,SCOLOR


########################
# Render a title bar
########################
def RenderMenuTitle(conn:Connection, title, style:bbsstyle=None):
    if type(title) == tuple:
        title = title[0]
    parms = {'title':title}
    if style != None:
        parms['st':style]
    tml = conn.templates.GetTemplate('main/menutitle',**parms)
    conn.SendTML(tml)

##########################################################
# Returns '[text]' prompt string in the selected style
# TML: True to return TML sequence
##########################################################
def KeyPrompt(conn:Connection, text, style:bbsstyle=None, TML=False):
    if style == None:
        style = conn.style
    pal = conn.encoder.palette
    if pal != {}:
        if TML:
            return(f'<INK c={style.PbColor}>[<INK c={style.PtColor}>{text}<INK c={style.PbColor}>]')
        else:
            tmp = pal.items()
            bc = [k for k,v in tmp if v == style.PbColor][0] if len([k for k,v in tmp if v == style.PbColor])>0 else ''
            tc = [k for k,v in tmp if v == style.PtColor][0] if len([k for k,v in tmp if v == style.PtColor])>0 else ''
            if (bc == '' or tc == '') and conn.QueryFeature(TT.INK) < 0x80:
                bc = chr(TT.CMDON)+chr(TT.INK)+chr(style.PbColor)
                tc = chr(TT.CMDON)+chr(TT.INK)+chr(style.PtColor)
            return(bc+'['+tc+conn.encoder.encode(str(text),True)+bc+']')
    else:
        return(f'[{text}]')

#################################################
# Renders a menu option in the selected style  
#################################################
def KeyLabel(conn:Connection, key:str, label:str, toggle:bool, style:bbsstyle=None):
    parms = {'key':key, 'label':label, 'toggle':toggle}
    if style != None:
        parms['st'] = style
    tml = conn.templates.GetTemplate('main/keylabel',**parms)
    conn.SendTML(tml)
    return not toggle

#####################################
# Render 'file dialog' background
#####################################
def RenderDialog(conn:Connection,height,title=None):
    tml = conn.templates.GetTemplate('main/dialog',**{'title':title,'height':height,'crop':H.crop})
    conn.SendTML(tml)


####################
# Style TML tags
####################
def StyleTag(conn:Connection, color:SCOLOR, style:bbsstyle=None):
    if color == SCOLOR.TxtColor:
        ink = conn.style.TxtColor
    elif color == SCOLOR.HlColor:
        ink = conn.style.HlColor
    elif color == SCOLOR.RvsColor:
        ink = conn.style.RvsColor
    elif color == SCOLOR.OKTxtColor:
        ink = conn.style.OKTxtColor
    elif color == SCOLOR.WRNTxtColor:
        ink = conn.style.WRNTxtColor
    elif color == SCOLOR.BADTxtColor:
        ink = conn.style.BADTxtColor
    else:
        ink = conn.style.TxtColor
        ...
    conn.SendTML(f'<INK c={ink}>')


##############
# TML tags
##############
t_mono = {	'MTITLE':(lambda c,t:RenderMenuTitle(c,t),[('c','_C'),('t','')]),
            'KPROMPT':(KeyPrompt,[('_R','_C'),('c','_C'),('t','RETURN'),('style',None),('tml','False')]),
            'DIALOG':(lambda c,h,t:RenderDialog(c,h,t),[('c','_C'),('h',4),('t','')]),
            'TXTCOLOR':(lambda c:StyleTag(c,SCOLOR.TxtColor),[('c','_C')]),
            'HLCOLOR':(lambda c:StyleTag(c,SCOLOR.HlColor),[('c','_C')]),
            'RVSCOLOR':(lambda c:StyleTag(c,SCOLOR.RvsColor),[('c','_C')]),
            'OKCOLOR':(lambda c:StyleTag(c,SCOLOR.OKTxtColor),[('c','_C')]),
            'BADCOLOR':(lambda c:StyleTag(c,SCOLOR.BADTxtColor),[('c','_C')]),
            'WRNCOLOR':(lambda c:StyleTag(c,SCOLOR.WRNTxtColor),[('c','_C')])}