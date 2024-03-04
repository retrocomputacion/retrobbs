#########################################################
# Classes
# any generic classes here
#########################################################

from common.dbase import DBase
import time
from enum import Enum
import os

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
        self.tml_mono = {}		#	TML Tags for single characters/control codes
        self.tml_multi = {}		#	TML Tags for characters that can be printed multiple times
        self.encode = None		#	Function to encode from ASCII/Unicode
        self.decode = None		#	Function to decode to ASCII/Unicode
        self.palette = {}		#	Dictionary of palette control codes -> color index
        self.colors = {}		#	Dictionary of named colors -> color index
        self.non_printable = []	#	List of non printable characters
        self.nl	= '\n'			#	New line string/character
        self.bs = '\x08'		#	Backspace string/character
        self.back = '_'         #   Caracter used to go back in the BBS
        self.ellipsis = '...'   #   Ellipsis representation
        self.txt_geo = (40,25)  #   Text screen dimensions
        self.def_gfxmode = None	#	Default graphic mode (gfxmodes enum)
        self.gfxmodes = ()		#	List of valid graphic modes
        self.ctrlkeys = {}		#	Named control keys (cursors, function keys, etc)
        self.bbuffer = 0x0000	#	Bottom address of the client's buffer
        self.tbuffer = 0x0000	#	Top address/size of the client's buffer

    def color_index(self, code):
        if type(code) == str:
            if len(code) == 1:
                code = ord(code)
        return self.palette.get(code,-1)

    # Function to check if a file will fit into the client's buffer 
    def check_fit(self, filename):
        stats = os.stat(filename)
        return stats.st_size <= (self.tbuffer-self.bbuffer)
    
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
            self.BgColor		= colors['BLACK']		#Background color
            self.BoColor		= colors['BLACK']		#Border color
            self.TxtColor		= colors.get('LIGHT_GREY',colors.get('GREY'))	#Main text color
            self.HlColor		= colors['WHITE']		#Highlight text color
            self.RvsColor		= colors['LIGHT_GREEN']	#Reverse text color
            ### Menu specific colors ###
            self.OoddColor		= colors['LIGHT_BLUE']	#Odd option key color
            self.OoddBack       = self.BgColor          #Odd option key bg color if applicable
            self.ToddColor		= colors.get('LIGHT_GREY',colors.get('GREY'))	#Odd option text color
            self.OevenColor		= colors['CYAN']		#Even option key color
            self.OevenBack      = self.BgColor          #Even option key bg color if applicable
            self.TevenColor		= colors['YELLOW']		#Even option text color
            self.MenuTColor1	= colors['CYAN']		#Menu title border color 1
            self.MenuTColor2	= colors['LIGHT_GREEN']	#Menu title border color 2
            self.SBorderColor1	= colors['LIGHT_GREEN']	#Section border color 1
            self.SBorderColor2	= colors['GREEN']		#Section border color 2
            ### [Prompt] ###
            self.PbColor		= colors['YELLOW']		#Key prompt brackets color
            self.PtColor		= colors.get('LIGHT_BLUE',colors.get('CYAN'))	#Key prompt text color

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
