===============================================================================

            RRRR   EEEEE  TTTTT  RRRR    RRR   BBBB   BBBB    BBBB
            R   R  E        T    R   R  R   R  B   B  B   B  B
            RRRR   EEEE     T    RRRR   R   R  BBBB   BBBB    BBB
            R  R   E        T    R  R   R   R  B   B  B   B      B
            R   R  EEEEE    T    R   R   RRR   BBBB   BBBB   BBBB

                              VERSION 0.2x dev

      (C)2020-2022 By Pablo Roldán(Durandal) & Jorge Castillo(Pastbytes)
===============================================================================

------------------
Table of contents
------------------
1-1 Introduction
1-2 Release history
1-3 The Turbo56K protocol
1-4 Features
1-5 Requirements

2-1 Configuration file
2-2 Internal Functions

3-1 Plug-In System
3-2 Included Plug-Ins

4-1 Common modules

5-1 Installation/Usage
5-2  The intro/login sequence
5-3  SID SongLength
5-4  User accounts / Database management
5-5  Messaging system

6-1 TO-DO List
6-2 Known bugs

7-1 Acknowledgements

-----------------
1-1 Introduction
-----------------
RetroBBS is a bulletin board system specifically developed to work in
conjunction with Turbo56K protocol capable terminals, such as Retroterm for the
Commodore 64.

RetroBBS is written in Python3 and uses several 3rd party modules to provide a
rich, multimedia online experience for 8 bit computers.

Even though this is the third rewrite of this script, it is still in an early
development stage, expect to find many bugs and ugly/non-pythonic code inside. 


--------------------
1-2 Release history
--------------------

v0.10 (16/08/2021): Initial release

v0.20 (15/11/2022):
  New features:
  - Added Login/User functionality
  - Added userclass/userlevel settings for the config file, select which menu
    is accessible to admins/sysops, registered users and/or guests
  - Added a verbosity command line switch, see section 5-1
  - Added Turbo56K v0.6 support, terminal features are queried and displayed
    on connection.
  - Messaging system, supports public boards and private messages.
    Public boards can have independent Read/Post user class permissions.

  Changes/Bug fixes:
  - Improvements to c64cvt
  - Fixed problems retrieving YouTube videos metadata due to removal of
    dislikes count.
  - YouTube frame capture now is faster after the 1st frame.
  - Core PCM audio and SID file streaming functions moved to their own module.
  - All PCM audio decoding is done using FFmpeg
  - WebAudio plugin can share any given PCM stream between multiple clients.
  - Updated example config file with valid links to YouTube videos and
    RSS feeds.
  - Misc. code cleanup
  - AudioList now supports HVSC style path to songlength files
  - Now most text parameters other than in calls to the Connection class are
    expected to be ASCII, not PETSCII, this also counts for the config
    file

v0.2x (In development):
  New features:
  - ...

  Changes/Bug fixes:
  - Librosa module replaced by audioread and use of ffmpeg audio filters.
    PCM streaming no longers use mu-law compression.
  - Removed legacy raw audio streaming code.

--------------------------
1-3 The Turbo56K protocol
--------------------------
Turbo56K was created by Jorge Castillo as a simple protocol to provide high
speed file transfer functionality to his bitbanging 57600bps RS232 routine
for the C64.
Over time, the protocol has been extended to include 4-bit PCM audio streaming,
bitmap graphics transfer and display, SID music streaming and more.

RetroBBS will refuse incoming connections from non-Turbo56K compliant
terminals.


-------------
1-4 Features
-------------
RetroBBS is quite customizable and expandable already at this early stage. The
use of a configuration file (config.ini) and built-in file transfer, stream
and display functions permits building a custom set of menus and file
galleries.
In addition, the plug-in system allows the addition of extra functionality with
full support from the config file.

The BBS is multi-threaded and supports up to five simultaneous incoming 
connections.

Current built-in functions:

    - User signup and signin. Plain text JSON database, salted password storage

    - Public message boards and private messaging system
 
    - Program transfer: Send Commodore 64 .prg files to the computer memory at
      the correct memory address.

    - RAW file transfer: Send RAW file data directly to the computer, no
      processing is done to the input data.

    - Text file transfer: Process different text formats (ASCII or PETSCII) and
      send it to the computer in pages.

    - Image conversion and display: Supports conversion of GIF, PNG, JPG file
      formats to C64 HiRes or Multicolor, also supports Koala Painter, Advanced
      Art Studio and Art Studio native file formats.
      Images larger than 320x200 pixels are resized and cropped for best fit.
      This functionality can be used from plug-ins. 

    - PCM audio streaming: WAV and MP3 files are converted to 4-bit 11520Hz PCM
      audio streams on the fly. Metadata is supported and displayed.

    - SID music streaming: SID files are converted to a stream of SID register
      writes. Only SID tunes that play once per frame (1X speed) are supported.
      This function requires the existence of the SIDDump executable in the
      system path.

Current included plug-ins:

    - Astronomy Picture Of the Day (apod.py): Retrieves and display the text
      and picture from NASA's Astronomy Picture Of the Day.
    - IRC Client (irc_client.py): Basic and very experimental IRC client.
    - RSS feed reader (newsfeed.py): Retrieves the latest 10 entries from the
      specified RSS feed, upon user selection of the entry it scrapes the
      target web site for text and relevant picture.
    - Oneliner (oneliner.py): Permits for user generated messages of up to 39
      characters.
    - WebAudio streamer (webaudio.py): On the fly conversion and streaming of
      on-line audio sources (Shoutcast or YouTube)
    - Wikipedia (wiki.py): Search and display Wikipedia articles, displays
      relevant article image if found.
    - YouTube snapshot (youtube.py): Display a frame from the specified YouTube
      video. It grabs the latest frame if the video is a livestream, otherwise
      it grabs a random frame.


-----------------
1-5 Requirements
-----------------

Python version 3.7 or above

Python modules:

  * audioread
  * soundfile
  * mutagen
  * numpy
  * opencv-python
  * pafy (For the YouTube plug-in) (use this version: https://github.com/Cupcakus/pafy)
  * streamlink (Will catch YouTube links if pafy fails, it also supports other
    stream services such as Twitch)
  * wikipedia and wikipedia-api (For the Wikipedia plug-in)
  * hitherdither (https://www.github.com/hbldh/hitherdither)
  * beautifulsoup4
  * feedparser (For the RSS feeds plug-in)
  * irc (For IRC client plug-in)
  * tinydb

  A basic requirements.txt file is available for quick installation of the
  required modules. Use:
  
    pip install -r requirements.txt

  If you already have pafy installed, you'll need to uninstall it beforehand:

    pip uninstall -y pafy


External software:

  * FFmpeg (for PCM audio streaming)
  * SIDDump (for SID streaming): https://github.com/cadaver/siddump replace the
    makefile with the one included in /siddump and compile. If you're using
    Linux, remove the .exe extension and copy the executable to usr/bin. 


-----------------------
2-1 Configuration file
-----------------------

RetroBBS uses a file named config.ini located in the root install directory,
this file follows the standard INI format (accepts the extended value
interpolation method as used by the configparse Python module):

[SECTION]
key = value

Please study the example config.ini file included in this package for
more information.

Sections:
---------

[MAIN] > Global BBS settings
  keys:
    bbsname     > Name of the BBS.
    menues      > Total number of menu pages, not counting the main menu page.
    ip          > IP V4 address on which the BBS will be accessible, default is
                  0.0.0.0
    port        > port number on which the BBS will be accessible.
    language    > language for remote texts, only partialy implemented as of 0.10
    welcome     > Welcome message on connection.
    goodbye     > Log off message.
    dateformat  > Format in which dates will be printed out, client side:
                 0 = dd/mm/yyyy
                 1 = mm/dd/yyyy
                 2 = yyyy/mm/dd

[BOARDS] > Settings for the available messaging boards
  keys:
    boardX      > (Where X > 0) Board name
    boardXview  > Minimum userclass that can read messages in this board (0 = public)
    boardXpost  > Minimum userclass that can post messages in this board (No less than 1)

[PATHS] > Directory paths to different BBS files, some are referenced in menu
          entry definitions. All paths must end with '/'.
  keys:
    bbsfiles  > Path to files used for login sequences and other general BBS
               information.
    audio     > Path to files for the audio library
    images    > Path to pictures for the Image gallery
    downloads > Path to files for the program library

  Custom paths can be added here as needed

[PLUGINS] > Any configuration options for installed plug-ins must be added under
            this section.

[MAINMENU] > Defines the name and number of sections of the main menu.
  keys:
    title    > Title for the main menu.
    sections > Number of sections on the main menu.
    prompt   > Prompt message to print at the bottom of the menu page.

[MAINMENUSECTIONy] > (Where 1 <= y <= {MAINMENU:sections}) Defines section 'y'
                     of the main menu.
  keys:
    title   > Title for this section (optional).
    entries > Number of entries in this section.
    columns > Number of columns per line, valid values are 1 or 2, default is 2

  common menu entry keys:
    entryZtitle > (Where 1 <= Z <= {entries}) Entry title.
    entryZkey   > Keypress associated with this entry (UPPERCASE only).
    entryZdesc  > Entry description text, optional, only when the section is
                  configured for 1 column. Text in ASCII format.
    entryZfunc  > Internal function or plug-in associated to this entry.
                  Depending on the function specific entry keys may be needed.
                  (See next chapter)
    entryZlevel > (Optional) Minimum useclass needed to access this entry,
                  default 0 (public)

  function/plug-in specific entry keys:
    entryZpath > A filesystem path.
    entryZext  > File extensions to match, comma separated list.
    entryZid   > Menu ID number.
    entryZurl  > An URL address.

[MENUx] > (Where 1 <= x <= {MAIN:menues}) Defines the name and number of
          sections in menu 'x'.
  keys: Same as in MAINMENU.

[MENUxSECTIONy] > (Where 1 <= x <= {MAIN:menues} and
                  1 <= y <= {MAINMENU:sections}) Defines section 'y' of menu
                  'x'.
  keys: Same as MAINMENUSECTIONy.


-----------------------
2-2 Internal Functions
-----------------------

The following are the function names providing access to internal BBS
functionality from the config file.

- Function PCMPLAY: Enters PCM streaming mode and streams the audio file
                    specified in the parameters.
      config.ini parameter keys:
          entryZpath > Path to the audio file to stream (must be one of the
                       supported formats).

- Function SWITCHMENU: Switches the BBS to a different menu.
      config.ini parameter keys:
          entryZid   > ID number of the menu to switch to.

- Function BACK: Switches the BBS back to the previous menu.
      config.ini parameter keys: NONE

- Function EXIT: Shows the logoff prompt, and terminates the connection if the
                 users decides to do so.
      config.ini parameter keys: NONE

- Function SLIDESHOW: Display/streams all the supported files in the specified
                      directory in sequential (alphabetical) order, user must
                      press [RETURN] to skip to the next file.
                      Supported filetypes are:
                      - ArtStudio, Advanced Art Studio, Koala Paint, GIF, PNG
                      and JPEG images
                      - MP3 and WAV audio files
                      - BIN and RAW byte streams
                      - ASCII and PETSCII text files
                      - PETMate and C syntax PETSCII screens
      config.ini paramater keys:
          entryZpath > Path to the slideshow files.

- Function FILES: Display the list of program files in a directory, the user
                  selected file will be transferred to memory.
      config.ini parameter keys:
          entryZpath > Path to the program files, default is '/programs'.

- Function IMAGEGALLERY: Display the list of images in a directory, the user
                  selected file will be transferred and displayed.
      config.ini parameter keys:
          entryZpath > Path to the image directory, default is '/images'.

- Function AUDIOLIBRARY: Display the list of audio files in a directory, the
                  user selected file will be streamed.
      config.ini parameter keys:
          entryZpath > Path to the audio files, default is '/sound'.

- Function USEREDIT:  Display the user profile editor

- Function USERLIST:  Display the list of registered users

- Function INBOX: Display the user's personal message inbox

- Function BOARD: Display the message list for the specified board
      config.ini parameter keys:
          entryZid > Board ID (>0)
      See the example config.ini for recommended usage.

(*)Replace Z in the config.ini parameters with the entry ID number.


-------------------
3-1 Plug-In system
-------------------

RetroBBS implements a simple plug-in system, on startup the BBS will import all
python modules found in the <plugins> directory.

All plug-in modules should implement at least two functions:

  setup() : Calling this function returns a tuple consisting of the plug-in
            name in uppercase, which will be used as the callable function on
            the config file. And a list of parameters, each element being a
            tuple itself. This tuple is made of the parameter name to use in
            the config file and the corresponding default value in case the
            parameter is not found.
  
  plugfunction(conn, <extra parameters>) : This is the function that is called
            by the BBS to perform the plug-in's task.
            The first parameter <conn> is a Connection object (see Chapter 4)
            to which the plug-in should direct its output.
            Any extra parameters will follow, with the same names as returned
            by setup().

----------------------
3-2 Included Plug-Ins
----------------------

- Astronomy Picture Of the Day (apod.py): 
      Retrieves and displays the text and picture from NASA's Astronomy Picture
      Of the Day.
      config.ini function: APOD
      config.ini parameters: none
      config.ini [PLUGINS] options: nasakey = Your NASA API key, obtained from
                  https://api.nasa.gov/. Default is DEMO_KEY

- IRC Client (irc_client.py):
      Basic and very experimental IRC client.
      config.ini function: IRC
      config.ini parameters:
        entryZserver = IRC server URL. Default is irc.libera.chat
        entryZport = IRC server port. Default is 6667
        entryZchannel = IRC channel to enter upon connection. Default is none.
      config.ini [PLUGINS] options: none

- RSS feed reader (newsfeed.py): Retrieves the latest 10 entries from the
      specified RSS feed, upon user selection of the entry it scrapes the
      target web site for text and relevant picture. The plug-in is mostly
      targeted at Wordpress sites, if it can't find the content it expects in
      the linked URL then the article text from the RSS feed itself will be
      displayed.
      config.ini function: NEWSFEED
      config.ini parameters:
        entryZurl = URL to the RSS feed
      config.ini [PLUGINS] options: none

- Oneliner (oneliner.py):
      Permits for user generated messages of up to 39 characters. The last 10
      messages are stored in a JSON file located in the <plugins> directory.
      config.ini function: ONELINER
      config.ini parameters: none
      config.ini [PLUGINS] options: none

- WebAudio streamer (webaudio.py):
      On the fly conversion and streaming of on-line audio sources (Shoutcast,
      YouTube or other sources).
      config.ini function: WEBAUDIO
      config.ini parameters:
        entryZurl = full URL to the audio stream
      config.ini [PLUGINS] options: none

- Wikipedia (wiki.py):
      Search and display Wikipedia articles, displays relevant article image if
      found.
      config.ini function: WIKI
      config.ini parameters: none
      config.ini [PLUGINS] options: none

- YouTube snapshot (youtube.py):
      Display a frame from the specified YouTube video. It will grab the latest
      frame if the video is a livestream, otherwise it grabs a random frame.
      config.ini function: GRABYT
      config.ini parameters: 
        entryZurl = full URL to the YouTube video
        entryZcrop = comma separated list of image coordinates for cropping the
                     video frame
      config.ini [PLUGINS] options: none


(*)Replace Z in the config.ini parameters with the entry ID number.

-------------------
4-1 Common modules
-------------------
Located inside the <common> directory you'll find modules which integrate what
could be called the BBS' API. The use of some of these modules is mandatory
when writing a new plug-in.

- common.audio: Audio/SID streaming:
    AudioList(conn,title,speech,logtext,path):
        Creates and manages an PCM audio/SID file browser.
        <conn>: Connection object
        <title>: String to be used as title for the file browser
        <speech>: Optional string for the voice synthesizer
        <logtext>: String to output in the log
        <path>: Path to the directory to browse
    PlayAudio(conn,filename, length = 60.0, dialog=False):
        Converts and streams a PCM audio file to <conn>.
        <filename>: Path to the file to stream, file can be either 4-bit .RAW,
        or any audio fileformat supported by librosa
        <length>: Length of the audio to stream in seconds, RAW files are
        streamed in they interity
        <dialog>: Boolean, display audio metadata and instructions before
        starting streaming
    SIDStream(conn, filename,ptime, dialog=True):
        Stream a SID file to <conn>
        <filename>: Path to the SID file
        <ptime>: Playtime in seconds
        <dialog>: Display SID file metadata and instructions before startings
        streaming

- common.bbsdebug: Log output to stdout:
    _LOG(message, _end='\n', date=True, id=0, v=1):
        Prints <message> on stdout. <message> can be any expression valid for
        the print function.
        The message will end in a newline by default, you change this by
        passing a different end string in the <_end> parameter.
        By default the message will be preceded by the current date and time,
        disable this by passing False in the <date> parameter.
        <id> Should be the connection id corresponding to this message.
        Defaults to 0 -> general message.
        <v> Verbosity level for this message. If greater than the level
        selected on startup the log message will not be printed.

    Also defined in this module is the <bcolors> class, which enumerates a few
    ANSI codes for use in the log messages.

- common.c64cvt: Image conversion to raw C64 formats.
    c64imconvert(Source, gfxmode=1, dmode = 0):
        Converts PIL image object <Source> into C64 graphic data.
        <gfxmode> selects the C64 graphic mode to use:
                  0 = HiRes
                  1 = MultiColor (default)
        Returns a tuple (e_img,cells,screen,color,bg_color) where:
            <e_img>:  PIL image object, rendering of the converted image
            <cells>:  c64 bitmap data (8000 bytes)
            <screen>: c64 screen matrix color data (1000 bytes)
            <color>:  c64 color ram data (1000 bytes), used only in multicolor
                      mode
            <bg_color>: c64 background color (1 byte), used only in multicolor
                      mode

- common.classes: Internal use only

- common.connection: Implements the Connection class, this is the class used to
                     communicate with clients, all plug-ins must include this
                     module. Only properties and methods to be used by plug-ins
                     are described below.
    Connection class properties:
        <socket>: Socket object for this connection. Socket is set to blocking
                  mode by default, with a timeout of 5 minutes.
        <addr>: IP address of the client  -READ ONLY-
        <id>: ID of this connection  -READ ONLY-
        <outbytes>: Total number of bytes sent to this client  -READ ONLY-
        <inbytes>: Total number of bytes received from this client  -READ ONLY-
    Connection class methods:
        Sendall(cadena): Converts string <cadena> to a binary string and sends
                         it to the client.
        Sendallbin(cadena): Sends binary string <cadena> to the client.
        Receive(count): Receives <count> binary chars from the client.
                        Returns: binary string.
        ReceiveKey(keys=b'\r'): Wait for a received character from the client
                        matching any of the characters in the <lista> binary
                        string.
                        Returns: The received matching char as a binary string.
        ReceiveKeyQuiet(keys=b'\r'): Same as ReceiveKey but no logging is ever
                        performed, disregarding logging level. Use it when
                        password or other sensitive user data must be received.
        ReceiveStr(keys, maxlen = 20, pw = False): Interactive reception
                        with echo. Call is completed on reception of a carriage
                        return.
                        <keys> is a binary string with the valid input
                        characters
                        <maxlen> is the maximun input string lenght
                        Set <pw> to True to echo '*' for each character
                        received, ie. for password entry.
                        Returns: ascii string received.
        ReceiveInt(minv, maxv, defv, auto = False): Interactive reception of
                        a positive integer with echo. The user will be
                        restricted to enter a number between minv and maxv,
                        if the user presses RETURN instead, the function will
                        return defv.
                        If auto is True, the function will return automatically
                        if the user enters the maximun number of digits
                        possible within the limits, or by pressing DEL when
                        there's no digit entered. In which case this function
                        will return None.

- common.filetools: Functions related to file transfer, only bitmap transfer
                    has been moved to this module so far.
    SendBitmap(conn, filename, lines = 25, display = True, dialog = False,
               multi = True): Convert image to C64 mode and sends it to the 
                              client.
            <conn>: Connection object
            <filename>: Path to image file/bytes object/PIL image object
            <lines>: Total number of lines (1 line = 8 pixels) to transfer
                     starting from the top of the screen, max/default = 25
            <display>: Set to True to send Turbo56K commands to display the
                       image after the transfer is completed
            <dialog>: Set to True to send a dialog asking for graphics mode
                      selection before converting and transfering the image
            <multi>: Set to True for multicolor mode. Overridden by user
                     selection if <dialog> = True

- common.helpers: Misc functions that do not fit anywhere else at this point,
                  functions might get deprecated and moved to other modules in
                  the future.
    valid_keys: A string containing the valid characters to be used as user
                input
    menu_colors: List containing the odd/even color pairs for menu entries.
    formatX(text, columns = 40, convert = True): Formats the <text> into
            <columns> columns with wordwrapping, <convert> selects if
            PETSCII conversion is performed or not.
    More(conn, text, lines, colors=default_style): Paginates <text>, sends it
            to <conn>, user must press RETURN to get next page(s). Supports 
            most PETSCII control codes, including color and cursor movement.
            <lines>: how many lines per page to transfer. Useful when using the
                    windowing commands of Turbo56K.
            <colors>: a bbsstyle object defining the color set to use.
  
- common.petscii: PETSCII <-> ASCII tools and constants. Many control codes and
                  graphic characters are defined as constants in this module,
                  is recommended to inspect it to learn more.
    PALETTE: A tuple containing the C64 palette control codes in the correct
             order
    NONPRINTABLE: A list of all the non-printable PETSCII characters
    toPETSCII(text,full = True): Converts <text> from UTF-8 to PETSCII, if
             <full> is TRUE, some characters are replaced with a visually
             similar PETSCII equivalent.
    toASCII(text): Converts <text> from PETSCII to plain ASCII, no extra care
             is taken to convert PETSCII graphic characters to their ASCII
             equivalents

- common.style: Defines the BBS style, this module is in a very early stage.
                The bbsstyle class is defined here, and the default_style
                instance of this class is initialized. Read the module source
                to find about the different class properties.
    RenderMenuTitle(conn,title): Sends the menu title header with text <title>
                to <conn>, using the default style. Client screen is cleared
                and charset is switched to lowercase. Text mode is not
                enforced, the caller must ensure that text mode or a text
                window is active on the client.
    KeyPrompt(text,style=default_style): Returns the key prompt string for
                <text>. The prompt takes the form [<text>] using the colors
                defined by <style>
    KeyLabel(conn,key,label,toggle,style=default_style): Renders menu option
                <label> for assigned <key> in the selected <style>, boolean
                <toggle> switch between odd/even styles.
                The result is sent to <conn> 

- common.turbo56k: Defines the Turbo56K protocol constants and helper functions
                See turbo56k.txt for more information.
      The following functions all return either a string or a binary string for
      use with the Connection.Sendall() or Connection.Sendallbin() methods.
      to_Text(page, border, background, bin = False): Switch the client screen
                to text mode.
                <page> is the text memory page to use
                <border> and <background> set the corresponding client screen
                colors
                <bin> selects the return string type
      to_Hires(page,border, bin = False): Switch the client screen to HiRes
                graphic mode.
                <page> is the bitmap memory page to use
                <border> is the client screen border color
                <bin> selects the return string type
      to_Multi(page, border, background, bin = False): Switch the client screen
                to multicolor graphic mode.
                <page> is the bitmap memory page to use
                <border> and <background> set the corresponding client screen
                colors
                <bin> selects the return string type
      customTransfer(address, bin = False): Sets the destination address for
                the next block transfer command.
                <address> a valid 16-bit integer value
                <bin> selects the return string type
      presetTransfer(preset, bin= False): Set the destination address for the
                next block transfer to the one defined by <preset>
                <bin> selects the return string type
      blockTransfer(data): Transfer the binary string <data> to the client.
                This function returns the complete command sequence to complete
                the transfer, including <data>. Normal usage is calling
                SendAllbin with the result of this function as the parameter
      to_Screen(bin = False): Selects the client screen as the output.
                <bin> selects the return string type
      to_Speech(bin = False): Selects the optional hardware speech synthesizer
                as text output.
                <bin> selects the return string type
      reset_Turbo56K(bin = False): Return a command sequence that enables the
                cursor, disables split screen and resets text window limits.
                <bin> selects the return string type
      set_CRSR(column, row, bin= False): Sets the client text cursor position
                to <column>, <row> coordinates
                <bin> selects the return string type
      Fill_Line(row, char, bin= False): Fill the client screen <row> with
                <char> (in C64 screencode), fill color is the last used.
                <bin> selects the return string type
      enable_CRSR(bin = False): Enables the client text cursor.
                <bin> selects the return string type
      disable_CRSR(bin = False): Disables the client text cursor.
                <bin> selects the return string type
      split_Screen(line, multi, bgtop, bgbottom, bin = False): Splits the
                client screen into a bitmap top and a text bottom parts.
                <line> the text screen row on which the split occurs
                <multi> boolean, True for Multicolor mode on the top part,
                        False for HiRes
                <bgtop> Background color for the top part, only used when
                        Multicolor mode is selected
                <bgbottom> Background color for the bottom part
                <bin> selects the return string type
      set_Window(top, bottom,bin = False): Set the <top> and <bottom> limits
                for the client text output, this includes scrolling and screen
                clearing.
                <bin> selects the return string type

-----------------------
5-1 Installation/Usage
-----------------------
After making sure you have installed all the required python modules, and extra
software, just unpack this archive into a directory of your choice.
If you're upgrading a previous installation, make sure to not overwrite your
configuration files with the ones included as example.

  NOTICE: Starting at v0.20 all text parameters in the config file are expected
  to be encoded in ASCII, if you're updating from v0.10 remember to convert
  your PETSCII parameters.


You can run this script from a command line by navigating to the Installation
directory and then issuing:

    python retrobbs.py

or

    python3 retrobbs.py

depending of your python install.

The only available command line option right now is -v[1-4], which sets the
verbosity of the log messages, a value of 1 will only output error messages,
while a value of 4 will output every log line.

-----------------------------
5-2 The intro/login sequence
-----------------------------
Once a connection with a client is established, and a supported version of
retroterm is detected, the client will enter into split screen mode and display
the splash.art bitmap file found in the <bbsfiles> subdirectory.
The user will then be asked if he wants to view the intro sequence or skip it.
If the user choses to view the intro sequence then the files in the
subdirectory <bbsfiles/intro> will be shown/played in alphabetical order.

-------------------
5-3 SID SongLength
-------------------
Currently the SID streaming routines are only accessed from the AUDIOLIBRARY
internal function. This function will set the songlength by searching for the
.ssl files corresponding the the .sid files found, defaulting to 3 minutes if
not found.
The .ssl format is used by the songlength files part of the High Voltage SID
Collection (http//:hvsc.c64.com). HVSC uses a 'SONGLENGTHS' subdirectory to 
store the .ssl files, RetroBBS can also read these files in the same directory
where the .sid files are located.

----------------------------------------
5-4 User accounts / Database management
----------------------------------------
RetroBBS now supports the creation of user accounts, this allows for the
restriction of BBS areas according to user classes and the incorporation of the
messaging system.

TinyDB is used as the database backend. The database is a JSON file located in
the "bbsfiles" directory.

Upon registering the user will be shown the file rules.txt located in
"bbsfiles/terms", you should edit this file according to your needs.
When registering the user will be asked the following data:

  - Password (stored as a salted hash in the database)
  - First and last names
  - Country of origin
  - Date of birth (Date format is defined by the "dateformat" parameter in the
                   config file)

A registered user will have a userclass=1 by default. Unregistered users
(guests) have a userclass=0.
Admins/Sysops are those with a userclass=10.

You can use userclasses 2 to 9 for more access granurality as you see fit.

A separate script for database management is included in the form of
dbmaintenance.py
Run it by issuing the following command (while the BBS is not running):

  python dbmaintenance.py

With this script you can:

  * Edit user data, and change their userclass.
  * Delete users
  * Add users

The script will also do a quick integrity check on the database file.

IMPORTANT: When setting up a new BBS (or upgrading from v0.10) use
dbmaintenance.py to create your account and set your class as 10 to assign
yourself as admin/sysop.

---------------------
5-5 Messaging system
---------------------
The messaging system permits unlimited public or semipublic boards plus a
personal messages board for each registered user.

At the time of writing, this early implementation supports messages of up to
720 characters in length, organized in 18 rows of 40 columns each.
The message editor works on per line basis, a line being completed by pressing
<RETURN>, passing the 40 characters limit, or selecting another line to edit
(by pressing <F3>).
On entering the editor, if the user is starting a new message thread they will
be asked to first enter a topic for the thread.
Once done with the editing the user should press <F8> and will be prompted if
they want to continue editing, send the message, or cancel the message.

An user with admin/sysop userclass (10) can delete threads or individual
messages (deleting the first message in a thread will delete the whole thread).

---------------
6-1 TO-DO List
---------------

 * Further code cleanup, move more functions out of the main script and into
   their corresponding modules.
 * Work towards user style customization
 * Subtune selection for SID Streaming
 * Localization

----------------------
6-2 Known bugs/issues
----------------------

  * Config file parser doesnt check for errors, a badly built config.ini will
    cause a crash on startup.
  * If updating from v0.10, the messages already existing in the oneliners.json
    file will have the wrong encoding. New messages will display correctly.


---------------------
7-1 Acknowledgements
---------------------

Development team
-----------------

  * Jorge Castillo (Pastbytes) - Original idea, creator and developer of
                                 Turbo56K, Retroterm and RetroBBS
  * Pablo Roldan (Durandal) - Developer of RetroBBS, extension of Turbo56K
                              protocol

Thanks
------

Thanks go to the following persons who helped in the testing of RetroBBS

  * Thierry Kurt
  * Ezequiel Filgueiras
  * Juan Musso
  * Vaporatorius
  * Gabriel Garcia
  * Roberto Mandracchia