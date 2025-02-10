#########################################################
# Classes
# any generic classes here
#########################################################

from common.dbase import DBase
import time
from enum import Enum
import os
import textwrap

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
        self.Paths = {'bbsfiles': 'bbsfiles/', 'plugins': 'plugins/', }
        self.PlugOptions = {}	#Plugins options from the config file
        self.BoardOptions = {}	#Message boards options from the config file
        self.Paths = {}			#Preset paths
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

SCOLOR = Enum('style_colors',
          [ 'BgColor','BoColor','TxtColor','HlColor','RvsColor',
            'OoddColor','ToddColor','OevenColor','TevenColor',
            'MenuTColor1','MenuTColor2','SBorderColor1','SBorderColor2',
            'PbColor','PtColor'])

############# bbstyle class #############
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

    # Set an style color, a section or the whole style
    # color : SCOLOR and index != None to set a single style color
    # color : dictionary with SCOLOR:int pairs to set the whole or part of the theme 
    def set(self, color, index: int = None):
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
