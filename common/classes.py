#########################################################
# Classes
# any generic classes here
#########################################################

from common.dbase import DBase
from common.bbsdebug import _LOG
import time
from enum import Enum
import os
import sys
import textwrap
from jinja2 import Environment, FileSystemLoader, TemplateError
import json

########### BBS Class ###########
class BBS:
    def __init__(self, name, ip, port):
        self.name = name
        self.ip = ip
        self.port = port
        self.lines = 5			#Number of simultaneous incoming connections
        self.lang = 'en'
        self.MenuList = None
        self.WMess = ''			#Welcome Message
        self.GBMess = ''		#Logoff Message
        self.BSYMess = ''		#Busy Message
        self.OSText = ''		#Host OS (Specific distro for Linux)
        self.TOut = 60*5		#Default Connection Timeout
        self.Paths = {'bbsfiles': 'bbsfiles/', 'audio': 'audio/', 'images': 'images/', 'downloads': 'programs/', 'temp': 'tmp/', 'plugins': 'plugins/', 'templates':'templates/'}
        self.PlugOptions = {}	#Plugins options from the config file
        self.BoardOptions = {}	#Message boards options from the config file
        self.Template = 'default/'   #Template in use
        # self.Paths = {}			#Preset paths WHY WAS THIS HERE???!!!
        self.dateformat = 0		#Date format
        self.database = None	#Database
        self.version = 0		#BBS version
        self.runtime = 0		#Timestamp this BBS session started
        self.visits = 0			#Number of visits in this session
        self.cfgmts = 0			#Config file modification timestamp
        self.plugins = {}		#Plugins
        self.encoders = {}		#Encoders
        self.clients = {}       #Client ID-> Encoder pairs

    def start(self):
        if self.database != None:
            self.stop()
        self.database = DBase(self.Paths['bbsfiles'])
        self.runtime = time.time()

    def stop(self):
        if self.database != None:
            self.database.uptime(time.time() - self.runtime)	#Update total uptime
            self.database.closeDB()

    def __del__(self):
        self.stop()

############# Encoder class #############
class Encoder:
    def __init__(self, name:str) -> None:
        self.name = name
        self.minT56Kver = 0.5   #   Minimum Turbo56K version this encoder requires. Use 0 for non-Turbo56K encoders
        self.clients = {}       #   Pair of client IDs:Platforms supported by this encoder
        self.tml_mono = {}		#	TML Tags for single characters/control codes
        self.tml_multi = {}		#	TML Tags for characters that can be printed multiple times
        self.encode = None		#	Function to encode from ASCII/Unicode
        self.decode = None		#	Function to decode to ASCII/Unicode
        self.palette = {}		#	Dictionary of palette control codes -> color index
        self.colors = {}		#	Dictionary of named colors -> color index
        self.non_printable = []	#	List of non printable characters
        self.nl	= '\n'			#	New line string/character (In)
        self.nl_out = '\n'      #   New line string/character (Out)
        self.bs = '\x08'		#	Backspace string/character
        self.back = '_'         #   Caracter used to go back in the BBS
        self.ellipsis = '...'   #   Ellipsis representation
        self.txt_geo = (40,25)  #   Text screen dimensions
        self.def_gfxmode = None	#	Default graphic mode (gfxmodes enum)
        self.gfxmodes = ()		#	List of valid graphic modes
        self.ctrlkeys = {}		#	Named control keys (cursors, function keys, etc)
        self.bbuffer = 0x0000	#	Bottom address of the client's buffer
        self.tbuffer = 0x0000	#	Top address/size of the client's buffer
        self.features = {'color':       False,  # Encoder supports color
                         'bgcolor':     0,      # Encoder supports background (paper) color:
                                                # 0 = No background color support
                                                # 1 = Global background support
                                                # 2 = Per character background support
                         'charsets':    1,      # Number of character sets supported
                         'reverse':     False,  # Encoder supports reverse video
                         'blink':       False,  # Encoder supports blink/flash text
                         'underline':   False,  # Encoder supports underlined text
                         'cursor':      False,  # Encoder supports cursor movement/set. Including home position and screen clear
                         'scrollback':  False,  # Encoder supports scrolling back (down) the screen
                         'windows':     0       # Encoder supports restricting text operations to a section of the screen
                                                # 0 = No window support
                                                # 1 = Full width screen slice
                                                # 2 = Arbitrary rectangular section
                         }

    # Given a color control code, returns it's index in the color palette
    # or -1 if not found
    def color_index(self, code):
        if type(code) == str:
            if len(code) == 1:
                code = ord(code)
        return self.palette.get(code,-1)

    # Given a palette index or color name, return the corresponding
    # control code string or an empty string
    def color_code(self, color):
        code = ''
        if self.colors != {} or self.palette != {}:
            if type(color) == str:
                code = self.colors.get(color,' ')
            if type(color) == int:
                v = self.palette.values()
                k = self.palette.keys()
                if color in v:
                    code = k[v.index(color)]
        return code

    # Function to check if a file will fit into the client's buffer 
    def check_fit(self, filename):
        stats = os.stat(filename)
        return stats.st_size <= (self.tbuffer-self.bbuffer)
    
    # Returns the load address, binary data from an executable file
    # Strip headers/metadata if needed for direct transfer into memory
    def get_exec(self, filename):
        return (0,None)
    
    # Wordwrap to the encoder/connection screen width
    # preserving control codes
    # text input must be already encoded
    # split: True to return a list of lines instead of
    # a string
    def wordwrap(self, text, split = False):
        lines = text.split(self.nl_out)
        if split:
            out = []
        else:
            out = ''
        for line in lines:
            # if not split:
            #     out = out +textwrap.fill(line,width=self.txt_geo[0])+self.nl_out
            # else:
            wlines = textwrap.wrap(line,width=self.txt_geo[0])
            for l in wlines:
                if len(l)<self.txt_geo[0]:
                    if not split:
                        out += l+self.nl_out
                    else:
                        out.append(l+self.nl_out)
                else:
                    if not split:
                        out += l
                    else:
                        out.append(l)
            if len(wlines)==0:
                if not split:
                    out += self.nl_out
                else:
                    out.append(self.nl_out)
        return(out)

    ### Encoder setup routine
    # Setup the required parameters for the given client id
    # Either automatically or by enquiring the user
    # Return None if no setup is necessary, or a customized
    # copy of the encoder object
    def setup(self, conn, id):
        return None

############ Style color enum ############
SCOLOR = Enum('style_colors',
          [ 'BgColor','BoColor','TxtColor','HlColor','RvsColor',
            'OoddColor','ToddColor','OevenColor','TevenColor',
            'MenuTColor1','MenuTColor2','SBorderColor1','SBorderColor2',
            'PbColor','PtColor',
            'NBarBG','NBarMove','NBarExit','NBarKeys',
            'OKTxtColor','WRNTxtColor','BADTxtColor'])

############# bbstyle class #############
# Set default color set
class bbsstyle:
    def __init__(self, colors:dict=None):
        if colors != None:
            # Default colors (in palette index)
            self.BgColor		= colors.get('BLACK',0)		#Background color
            self.BoColor		= colors.get('BLACK',0)		#Border color
            self.TxtColor		= colors.get('LIGHT_GREY',colors.get('GREY',colors.get('WHITE',0)))	#Main text color
            self.HlColor		= colors.get('WHITE',0)		#Highlight text color
            if (self.TxtColor == self.HlColor) and 'YELLOW' in colors:
                self.HlColor = colors['YELLOW']
            self.RvsColor		= colors.get('LIGHT_GREEN',0)	#Reverse text color
            ### Menu specific colors ###
            self.OoddColor		= colors.get('LIGHT_BLUE',0)	#Odd option key color
            self.OoddBack       = self.BgColor          #Odd option key bg color if applicable
            self.ToddColor		= colors.get('LIGHT_GREY',colors.get('GREY',colors.get('WHITE',0)))	#Odd option text color
            self.OevenColor		= colors.get('CYAN',0)		#Even option key color
            self.OevenBack      = self.BgColor              #Even option key bg color if applicable
            self.TevenColor		= colors.get('YELLOW',0)    #Even option text color
            self.MenuTColor1	= colors.get('CYAN',0)		#Menu title border color 1
            self.MenuTColor2	= colors.get('LIGHT_GREEN',0)	#Menu title border color 2
            self.SBorderColor1	= colors.get('LIGHT_GREEN',0)	#Section border color 1
            self.SBorderColor2	= colors.get('GREEN',0)		#Section border color 2
            ### [Prompt] ###
            self.PbColor		= colors.get('YELLOW',0)		#Key prompt brackets color
            self.PtColor		= colors.get('LIGHT_BLUE',colors.get('CYAN',0))	#Key prompt text color
            ### Nav Bar ###
            self.NBarBG         = colors.get('LIGHT_BLUE',colors.get('CYAN',0)) #Nav bar main background color
            self.NBarMove       = colors.get('LIGHT_BLUE',colors.get('BLUE',0)) #Nav bar move keys background color
            self.NBarExit       = colors.get('YELLOW',colors.get('ORANGE',0))   #Nav bar exit section background color
            self.NBarKeys       = colors.get('GREEN',colors.get('LIGHT_GREEN',0)) #Nav bar keys section background color
            ### Status colors ###
            self.OKTxtColor     = colors.get('GREEN',0)     # OK/Good text
            self.WRNTxtColor    = colors.get('YELLOW',0)    # Warning text
            self.BADTxtColor    = colors.get('RED',0)       # Bad/Error text
        else:
            # Default colors (in palette index)
            self.BgColor		= 0		#Background color
            self.BoColor		= 0		#Border color
            self.TxtColor		= 0	    #Main text color
            self.HlColor		= 0		#Highlight text color
            self.RvsColor		= 0	    #Reverse text color
            ### Menu specific colors ###
            self.OoddColor		= 0	    #Odd option key color
            self.OoddBack       = 0     #Odd option key bg color if applicable
            self.ToddColor		= 0	    #Odd option text color
            self.OevenColor		= 0		#Even option key color
            self.OevenBack      = 0     #Even option key bg color if applicable
            self.TevenColor		= 0     #Even option text color
            self.MenuTColor1	= 0		#Menu title border color 1
            self.MenuTColor2	= 0	    #Menu title border color 2
            self.SBorderColor1	= 0 	#Section border color 1
            self.SBorderColor2	= 0		#Section border color 2
            ### [Prompt] ###
            self.PbColor		= 0		#Key prompt brackets color
            self.PtColor		= 0 	#Key prompt text color
            ### Nav Bar ###
            self.NBarBG         = 0     #Nav bar main background color
            self.NBarMove       = 0     #Nav bar main background color
            self.NBarExit       = 0     #Nav bar exit section background color
            self.NBarKeys       = 0     #Nav bar keys section background color
            ### Status colors ###
            self.OKTxtColor     = 0     # OK/Good text
            self.WRNTxtColor    = 0     # Warning text
            self.BADTxtColor    = 0     # Bad/Error text

    # Set an style color, a section or the whole style
    # color : SCOLOR and index != None to set a single style color
    # color : dictionary with SCOLOR:int pairs to set the whole or part of the theme 
    def set(self, color:SCOLOR, index: int = None):
        if type(color) != dict:
            if index != None:
                color = {color:index}
            else:
                return
        for xi in color:
            index = color[xi]
            if color == SCOLOR.BgColor:
                self.BgColor		= index
            elif color == SCOLOR.BoColor:
                self.BoColor		= index
            elif color == SCOLOR.TxtColor:
                self.TxtColor		= index
            elif color == SCOLOR.HlColor:
                self.HlColor		= index
            elif color == SCOLOR.RvsColor:
                self.RvsColor
            elif color == SCOLOR.OoddColor:
                self.OoddColor		= index
            elif color == SCOLOR.ToddColor:
                self.ToddColor		= index
            elif color == SCOLOR.OevenColor:
                self.OevenColor		= index
            elif color == SCOLOR.TevenColor:
                self.TevenColor		= index
            elif color == SCOLOR.MenuTColor1:
                self.MenuTColor1	= index
            elif color == SCOLOR.MenuTColor2:
                self.MenuTColor2	= index
            elif color == SCOLOR.SBorderColor1:
                self.SBorderColor1	= index
            elif color == SCOLOR.SBorderColor2:
                self.SBorderColor2	= index
            elif color == SCOLOR.PbColor:
                self.PbColor		= index
            elif color == SCOLOR.PtColor:
                self.PtColor		= index
            elif color == SCOLOR.NBarBG:
                self.NBarBG		    = index
            elif color == SCOLOR.NBarMove:
                self.NBarMove		= index
            elif color == SCOLOR.NBarExit:
                self.NBarExit		= index
            elif color == SCOLOR.NBarKeys:
                self.NBarKeys		= index
            elif color == SCOLOR.OKTxtColor:
                self.OKTxtColor		= index
            elif color == SCOLOR.WRNTxtColor:
                self.WRNTxtColor		= index
            elif color == SCOLOR.BADTxtColor:
                self.NBarKeys		= index


######## Template class ########
class template:
    def __init__(self, conn, mytemplate:str='default/'):
        self.connection = conn
        tpath = conn.bbs.Paths['templates']
        self.path = mytemplate
        self.j2env = Environment(loader=FileSystemLoader([tpath+mytemplate,tpath+'default/','templates/default/']))
        self.j2env.globals.update({'conn':conn,'st':conn.style,'mode':conn.mode,'scwidth':conn.encoder.txt_geo[0],'scheight':conn.encoder.txt_geo[1]})

    # Return a parsed template
    # Parameters:
    #
    # name: Slash separated template name:
    #       '<section>/<template>'
    #       ie: 'main/title'
    # conn: Connection object
    # **kwargs: Dictionary of parameters
    def GetTemplate(self, name:str, **kwargs):
        try:
            template = self.j2env.get_template(name+'.j2')
            return (template.render(kwargs))
        except TemplateError as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            _LOG(e,id=self.connection.id,v=1)
            _LOG(fname+'|'+str(exc_tb.tb_lineno),id=self.connection.id,v=1)
        return ''
    
    # Get a bbsstyle color set from the templates directory
    # if no style file is found, the connection default bbsstyle object is returned
    def GetStyle(self,name:str=''):
        tpath = self.connection.bbs.Paths['templates']
        paths = [tpath+self.path,tpath+'default/','temnplates/default/']
        for p in paths:
            if os.path.exists(p+name+'.json'):  # Look for the file in the valid paths
                with open(p+name+'.json','r') as sf:
                    jstyle = json.load(sf)
                break
        else:   # File not found
            return(self.connection.style)
        # Create style object
        if self.connection.mode in jstyle:
            default:bbsstyle = self.connection.style #<<<
            style = bbsstyle()
            colors = self.connection.encoder.colors
            st = jstyle[self.connection.mode]
            style.BgColor		= colors.get(st.get('BgColor'),default.BgColor) if 'BgColor' in st else default.BgColor
            style.BoColor		= colors.get(st.get('BoColor'),default.BoColor) if 'BoColor' in st else default.BoColor
            style.TxtColor		= colors.get(st.get('TxtColor'),default.TxtColor) if 'TxtColor' in st else default.TxtColor
            style.HlColor		= colors.get(st.get('HlColor'),default.HlColor) if 'HlColor' in st else default.HlColor
            style.RvsColor		= colors.get(st.get('RvsColor'),default.RvsColor) if 'RvsColor' in st else default.RvsColor
            style.OoddColor		= colors.get(st.get('OoddColor'),default.OoddColor) if 'OoddColor' in st else default.OoddColor
            style.OoddBack      = colors.get(st.get('OoddBack'),default.OoddBack) if 'OoddBack' in st else default.OoddBack
            style.ToddColor		= colors.get(st.get('ToddColor'),default.ToddColor) if 'ToddColor' in st else default.ToddColor
            style.OevenColor	= colors.get(st.get('OevenColor'),default.OevenColor) if 'OevenColor' in st else default.OevenColor
            style.OevenBack     = colors.get(st.get('OevenBack'),default.OevenBack) if 'OevenBack' in st else default.OevenBack
            style.TevenColor	= colors.get(st.get('TevenColor'),default.TevenColor) if 'TevenColor' in st else default.TevenColor
            style.MenuTColor1	= colors.get(st.get('MenuTColor1'),default.MenuTColor1) if 'MenuTColor1' in st else default.MenuTColor1
            style.MenuTColor2	= colors.get(st.get('MenuTColor2'),default.MenuTColor2) if 'MenuTColor2' in st else default.MenuTColor2
            style.SBorderColor1	= colors.get(st.get('SBorderColor1'),default.SBorderColor1) if 'SBorderColor1' in st else default.SBorderColor1
            style.SBorderColor2	= colors.get(st.get('SBorderColor2'),default.SBorderColor2) if 'SBorderColor2' in st else default.SBorderColor2
            style.PbColor		= colors.get(st.get('PbColor'),default.PbColor) if 'PbColor' in st else default.PbColor
            style.PtColor		= colors.get(st.get('PtColor'),default.PtColor) if 'PtColor' in st else default.PtColor
            style.NBarBG        = colors.get(st.get('NBarBG'),default.NBarBG) if 'NBarBG' in st else default.NBarBG
            style.NBarMove      = colors.get(st.get('NBarMove'),default.NBarMove) if 'NBarMove' in st else default.NBarMove
            style.NBarExit      = colors.get(st.get('NBarExit'),default.NBarExit) if 'NBarExit' in st else default.NBarExit
            style.NBarKeys      = colors.get(st.get('NBarKeys'),default.NBarKeys) if 'NBarKeys' in st else default.NBarKeys
            style.OKTxtColor    = colors.get(st.get('OKTxtColor'),default.OKTxtColor) if 'OKTxtColor' in st else default.OKTxtColor
            style.WRNTxtColor   = colors.get(st.get('WRNTxtColor'),default.WRNTxtColor) if 'WRNTxtColor' in st else default.WRNTxtColor
            style.BADTxtColor   = colors.get(st.get('BADTxtColor'),default.BADTxtColor) if 'BADTxtColor' in st else default.BADTxtColor
            return style
        else:   # Style file doesn't define color for the current mode
            return(self.connection.style)
