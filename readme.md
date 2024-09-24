
<div align = center>

![logo](docs/retrobbs.png)

# RetroBBS

VERSION 0.60 dev

(c)2020-2024 By Pablo Roldán(Durandal) & Jorge Castillo(Pastbytes)
</div>


---
# Table of contents

1. [Introduction](#1-introduction)
   1. [Release history](#11-release-history)
   2. [The *Turbo56K* protocol](#12-the-turbo56k-protocol)
   3. [The *TML* language](#13-the-tml-language)
   4. [Features](#14-features)
   5. [Requirements](#15-requirements)
2. [Configuration file](#2-configuration-file)
   1. [Internal Functions](#21-internal-functions)
3. [Plug-in System](#3-plug-in-system)
   1. [Included Plug-Ins](#31-included-plug-ins)
   2. [More Plug-ins](#32-more-plug-ins)
4. [Common modules](#4-common-modules)
5. [Encoders](#5-encoders)
6. [Installation/Usage](#6-installationusage)
   1. [The intro/login sequence](#61-the-intrologin-sequence)
   2. [SID SongLength](#62-sid-songlength)
   3. [User accounts / Database management](#63-user-accounts--database-management)
   4. [Messaging system](#64-messaging-system)
   5. [Temporal directory](#65-temporal-directory)
7. [TO-DO List](#7-to-do-list)
   1. [Known bugs](#71-known-bugsissues)
8. [Acknowledgements](#8-acknowledgements)


# 1 Introduction

*RetroBBS* is a bulletin board system specifically developed to work in conjunction with *[Turbo56k](docs/turbo56k.md)* protocol-capable terminals, such as *[Retroterm](https://github.com/retrocomputacion/retroterm)* for the Commodore 64, Commodore Plus/4 or MSX computers.

*RetroBBS* is written in *Python3* and uses several 3rd party modules to provide a rich, multimedia online experience for 8-bit computers.

Even though this is the third rewrite of this script, it is still in an early development stage, expect to find many bugs and ugly/non-pythonic code inside.</br>
Starting from v0.50 the BBS is transitioning to neutral encoding, slowly removing hard-coded PETSCII strings and C64 format images. With the goal of supporting other retro platforms.


---
# 1.1 Release history

### **v0.10** (16/08/2021):
  Initial release

### **v0.20** (15/11/2022):
  __New features__:
  - Added Login/User functionality
  - Added userclass/userlevel settings for the config file, select which menu is accessible to admins/sysops, registered users and/or guests.
  - Added a verbosity command line switch, see section 5
  - Added *[Turbo56k](docs/turbo56k.md)* v0.6 support, terminal features are queried and displayed on connection.
  - Messaging system, supports public boards and private messages.
    Public boards can have independent Read/Post user class permissions.

  __Changes/Bug fixes__:
  - Improvements to c64cvt
  - Fixed problems retrieving *YouTube* videos metadata due to the removal of the dislikes count.
  - *YouTube* frame capture is now faster after the 1st frame.
  - Core PCM audio and SID file streaming functions moved to their own module.
  - All PCM audio decoding is done using *FFmpeg*
  - WebAudio plugin can share any given PCM stream between multiple clients.
  - Updated example config file with valid links to *YouTube* videos and RSS feeds.
  - Miscellaneous code cleanup
  - AudioList now supports *HVSC* style path to songlength files
  - Now most text parameters other than in calls to the Connection class are expected to be *ASCII*, not *PETSCII*, this also counts for the config file.

### **v0.25** (14/11/2022):
  __New features__:
  - **SLIDESHOW** now supports SID files
  - **WEATHER** plugin, display the current weather and forecast for the next 2-3 days.
  - BBS version and host OS are shown after the welcome message.
  - Total BBS uptime is stored in the database. Session uptime is available as an attribute of the BBS class.
  - Total data transferred for each user account is stored in the database.

  __Changes/Bug fixes__:
  - *Librosa* module replaced by *audioread* and use of *FFmpeg* audio filters, PCM streaming no longer uses mu-law compression.
  - Removed legacy RAW audio streaming code.
  - Fixed broken **AUDIOLIBRARY** formatting when a filename contains non-Latin characters.
  - Fixed broken Streamlink support. Added Twitch stream example to configuration file
  - **SLIDESHOW** now plays PCM audio for the correct amount of time.
  - SIDStreaming flushes the input buffer when the stream is canceled.
  - Fixed board/inbox message list order, changed from newest thread first to thread with the newest message first.
  - Board/Inbox message list now displays the author of the latest message in each thread.
  - When reading a public board message thread, the date for the current message is displayed in the header next to the author.
  - **SendProgram** and **SendRAWFile** moved from the main script to the common.filetools module.
  - Documentation rewritten in Markdown format

### **v0.50** (02/01/2024):

__New features__:
 - Idle BBS will reload the configuration file if it has been modified during runtime.
 - New LABEL internal function for displaying non-interactive text in menus.
 - New command line parameter `-c`, select configuration file.
 - SID streaming now supports Compute's Sidplayer .mus files.
 - SID streaming now supports selection of the subtune to play.
 - SID streaming supports tunes using hardrestart, if _SIDDumpHR_ is available. 
 - New `CHIPPLAY` and `SIDPLAY` functions for the configuration file.
 - Added *[Turbo56k](docs/turbo56k.md)* v0.7 support.
 - New text viewer with support for bidirectional scroll.
 - New Maps plugin.
 - Added support for .YM, .VTX and .VGM music files. YM2149/AY-3-8910 data streams are converted to SID data streams.
 - Added Python based internal SIDdump implementation used as fallback if neither _SIDdump_ nor _SIDdumpHR_ are present.
 - Added GRABFRAME internal function.
 - Added `lines` and `busy` parameters to the configuration file 
 - Added `encoders` directory. Encoder modules provide encoding/decoding functions for different platforms. 
 - Added Plus/4 support.
 - Introducing TML markup/scripting language, moving towards an encoding agnostic BBS. Some functions now expect parameters in this format.
 - New STAT internal function for displaying some basic BBS and user statistics
 - Added `SENDFILE` function for the configuration file.
 - Show album art if embedded in MP3 files (and dialog is enabled)
 - New `mode` config file parameter allows for platform specific versions of menu entries
 - Added user preferences, both global and plugin specific
 - New plugin game *Mindle*, a Wordle clone, guess the computer science/video game/tech term. Supports high scores for registered users

__Changes/Bug fixes__:
 - Simplified initial terminal feature check, now is more reliable.
 - Fixed bug where an unsupported weather type would crash the *python_weather* module, in turn crashing the weather plugin and dropping the connection. 
 - Added 'wait cursor' to the audio module and webaudio plugin
 - Fixed bugs when adding and editing users in both *dbmaintenance.py* and the main script
 - Fixed display of .c and .pet files
 - Fixed playtime for audio files played through the PCMPLAY function
 - Improved *dbmaintenance.py* UI, now it is possible to cancel options 'Update user data' and 'Add user'
 - Username is now case-insensitive (username is still stored and displayed as case-sensitive); *dbmaintenance.py* will warn of existing clashing usernames, but will take no action. Is up to the admin to edit or delete the offending user accounts.
 - Removed extra empty line if the first section of a menu doesn't have a title.
 - Custom paths are now read from the configuration file, currently only 'temp' and 'bbsfiles' presets are used internally.
 - Fixed search for .ssl files in the `SONGLENGTH` subdirectory
 - Fixed playlength of NTSC .sid files.
 - Slideshow doesn't wait for `RETURN` when there's an unsupported file present in the sequence.
 - Fixed high CPU usage when streaming local audio files 
 - Improved Wikipedia article parsing
 - **FILES** function will show file extensions if no file extension parameter is given
 - Main video frame grabbing routine moved to new `common/video.py`, YouTube plugin now calls this internal routine.
 - *YouTube* plugin now uses *Streamlink* instead of the now obsolete/no longer under development *pafy*.
 - When all the slots are in use will now correctly close any further incoming connections.
 - *Weather* and *Maps* plugins can now use either Photon or Nominatim as geocoder, selected from the configuration file.
 - Fixed crash when the geocoder didn't respond in time in the *Weather* plugin
 - Extensive rewrite and cleanup, TML scripting integration.
 - Option to logout after transferring a program to memory
 - Weather plugin adapted to support `python-weather` v1.0.0+. Older versions of the module still work.
 - Revamped graphic conversion module(s)
 - ~~Webaudio fix: Take samplerate into account when more than one client is streaming from the same source.~~
 - Webaudio multiclient queuing disabled, falling back to one ffmpeg instance per audio stream.
 - Fixed missing timeout parameter in APOD plugin.
 - Both *APOD* and *Newsfeed* plugins now use *text_displayer* instead or *More*
 - *Sendfile* checks if executable file fits in the client's available memory size and range and disables transfer to memory if the file is too large or resides outside the valid memory range.
 - Added `←` glyph to BetterPixels font

### **v0.60**:
__New features__:
 - MSX support
 - *Radio* and *Podcast* plugins by __Emanuele Laface__
 - SID to AY music conversion.

__Changes/Bug fixes__:
 - Fixed filter cutoff low nibble in SID chiptune streaming
 - Fixed PCMPLAY support for non-local files
 - Webaudio plugin now supports non-live sources
 - Send the correct number of delete characters for the LogOff confirmation message
 
---
# 1.2 The *Turbo56K* protocol

*[Turbo56k](docs/turbo56k.md)* was created by Jorge Castillo as a simple protocol to provide high-speed file transfer functionality to his bit-banging 57600bps RS232 routine for the C64.
Over time, the protocol has been extended to include 4-bit PCM audio streaming, bitmap graphics transfer and display, SID music streaming and more.

*RetroBBS* will refuse incoming connections from non-*Turbo56K* compliant terminals.

---
# 1.3 The *TML* language

Introduced in v0.50, *TML*, standing for *Turbo Markup Language* is a markup and scripting language inspired by the type-in program listings in magazines from the 1980s.
The language's goal is to allow the description of control codes and other platform specific characteristics in plain text. With the added power of allowing the access of internal BBS functions and plugins.
Read the [dedicated documentation](docs/tml.md) for more info. 

---
# 1.4 Features

*RetroBBS* is quite customizable and expandable. The use of a configuration file (`config.ini` by default) and built-in file transfer, stream and display functions permits building a custom set of menus and file galleries.
In addition, the plug-in system allows adding extra functionality with full support from the configuration file.

The BBS is multithreaded and the number of simultaneous incoming connections can be customized in the configuration file.

Current built-in functions:

- User signup and sign in. Plain text JSON database, salted password storage

- Public message boards and private messaging system

- Program transfer: Send Commodore 64 and Plus/4 .prg files to the computer memory at the correct memory address.

- RAW file transfer: Send RAW file data directly to the computer, no processing is done to the input data.

- Text file transfer: Process different text formats (*ASCII* or *PETSCII*) and send it to the client computer either paginated or with interactive scrolling.

- Image conversion and display: Supports conversion of *GIF*, *PNG*, *JPG* file formats to C64 and Plus/4 Hires or Multicolor, also supports Koala Painter, Advanced Art Studio, Doodle!, Art Studio C64 native file formats and Botticelli Plus/4 native file format. Images larger than 320x200 pixels are resized and cropped for best fit. This functionality can be used from plug-ins. 

- PCM audio streaming: *WAV* and *MP3* files are converted to 4-bit 11520Hz PCM audio streams on the fly. Metadata is supported and displayed.

- SID music streaming: .SID and .MUS files are converted to a stream of SID register writes. Only SID tunes that play once per frame (1X speed) are supported. This function requires the existence of the *SIDDumpHR* or *SIDDump* executables in the system path, if neither is found a slower Python implementation will be used instead.

- YM2149/AY-3-8910 music streaming: .AY, .VTX and .VGZ files are decoded and converted to a stream of register writes. Samples and some other special effects are not supported.

- Conversion of AY-3-8910 register streams into SID streams for C64 clients, cyclic envelope simulation is limited.

- Conversion of SID register streams into AY-3-8910 streams for MSX clients, all SID waveforms are played as either pulse or noise. Filter attenuation is not simulated.

- Video frame grabbing: Any file format supported by OpenCV2/ffmpeg, files can be local or from an external URL.

- File transfer to the client's (disk) storage device.

Included plug-ins:

- Astronomy Picture Of the Day (apod.py): Retrieves and displays the text and picture from NASA's Astronomy Picture Of the Day.
- IRC Client (irc_client.py): Basic and very experimental IRC client.
- RSS feed reader (newsfeed.py): Retrieves the latest 10 entries from the specified RSS feed, upon user selection of the entry, it scrapes the target website for text and relevant picture.
- Oneliner (oneliner.py): User-generated messages of up to 39 characters.
- WebAudio streamer (webaudio.py): On-the-fly conversion and streaming of online audio sources (*Shoutcast*, *YouTube* or other sources)
- Wikipedia (wiki.py): Search and display *Wikipedia* articles, displaying relevant article image if found.
- YouTube snapshot (youtube.py): Display a frame from the specified *YouTube* video. It grabs the latest frame if the video is a live stream, otherwise it grabs a random frame.
- Weather (weather.py): Query the weather forecast for any part of the world.
- Maps (maps.py): Display and navigate the map of the world. 
- Mindle (mindle.py): A Wordle clone, with variable word length.


---
# 1.5 Requirements

Python version 3.7 or above

Python modules:

  * audioread
  * beautifulsoup4
  * crc
  * feedparser (For the RSS feeds plug-in)
  * geopy (For the weather plugin)
  * hitherdither (https://www.github.com/hbldh/hitherdither)
  * irc (For IRC client plug-in)
  * lhafile (For .YM and .VTX file support)
  * mutagen
  * numpy
  * opencv-python
  * ~~pafy (For the YouTube plug-in) (use this version: https://github.com/Cupcakus/pafy)~~
  * python_weather (For the weather plugin)
  * pyradios (For *Radio* plugin)
  * scikit-image
  * soundfile
  * streamlink (Replaces pafy for *YouTube* links, it also supports other stream services such as *Twitch*)
  * tinydb
  * wikipedia and wikipedia-api (For the Wikipedia plug-in)

  A basic `requirements.txt` file is available for quick installation of the required modules. Use:
  
    pip install -r requirements.txt



### External software:

  * *FFmpeg* >= 4.0 (for PCM audio streaming)

- Optional but recommended:

  * *[SIDDumpHR](https://github.com/retrocomputacion/SIDDumpHR)* (for SID streaming): After compiling, copy the executable to /usr/bin
  * Alternatively *[SIDDump](https://github.com/cadaver/siddump)* (doesn't support hardrestart): After compiling, if you're using *Linux*, remove the .exe extension from the executable and copy it to /usr/bin.


---
# 2 Configuration file

*RetroBBS* uses the standard INI format for its configuration file (accepts the extended value interpolation method as used by the _configparse_ Python module), the default file is `config.ini`, located in the root install directory:

```ini 
[SECTION]
key = value
```
Please study the example `config.ini` file included in this package for
more information.

When the BBS is idle (no visitors connected), it will reload the config file if it detects it has been modified.
All settings will be updated, but network settings will only take place upon restart.

## Sections:

### **\[MAIN\]**
Global BBS settings

| key | description
|:---:|:---
| `bbsname` | Name of the BBS
| `menues` | Total number of menu pages, not counting the main menu page
| `ip` | IP V4 address on which the BBS will be accessible, default is `127.0.0.1`
| `port` | port number on which the BBS will be accessible
| `lines` | Number of connection slots
| `language` | language for transmitted texts, only partially implemented as of 0.25
| `welcome` | Welcome message on connection
| `goodbye` | Log off message
| `busy` | Message shown when all the connection slots are in use
| `dateformat` | Format in which dates will be printed out, client-side:<br>0 = dd/mm/yyyy<br>1 = mm/dd/yyyy<br>2 = yyyy/mm/dd

### **\[BOARDS\]**
Settings for the available messaging boards

| key | description
|:---:|:---
| `boardX` | (Where X > 0) Board name
| `boardXview` | Minimum userclass that can read messages on this board (0 = public)
| `boardXpost` | Minimum userclass that can post messages on this board (No less than 1)

### **\[PATHS\]**
Directory paths to different BBS files, some are used internally, others are referenced in menu entry definitions. All paths must end with '/'.

| key | description
|:---:|:---
| `bbsfiles` | Path to files used for login sequences and other general BBS information.
| `audio` | Path to files for the audio library
| `images` | Path to pictures for the Image gallery
| `downloads` | Path to files for the program library
| `temp` | Path to temporary files created by the BBS or it's plugins

Custom paths can be added here as needed

### **\[PLUGINS\]**
Any configuration options for installed plug-ins must be added under this section.

### **\[MAINMENU\]**
Defines the name and number of sections of the main menu.
| key | description
|:---:|:---
| `title` | Title for the main menu
| `sections` | Number of sections on the main menu
| `prompt` | Prompt message to print at the bottom of the menu page

### **\[MAINMENUSECTIONy\]**
(Where 1 <= y <= {MAINMENU:sections}) Defines section 'y' of the main menu.
| key | description
|:---:|:---
| `title` | Title for this section (optional)
| `entries` | Number of entries in this section
| `columns` | Number of columns per line, valid values are 1 or 2, default is 2

Common menu entry keys:
| key | description
|:---:|:---
| `entryZtitle` | (Where 1 <= Z <= {entries}) Entry title
| `entryZkey` | Key press associated with this entry (UPPERCASE only)
| `entryZdesc` | Entry description text, optional, only when the section is configured for 1 column
| `entryZfunc` | Internal function or plug-in associated with this entry.<br>Depending on the function, specific entry keys may be needed (See next chapter)<br>Defaults to `LABEL` if omitted.
| `entryZlevel` | (Optional) Minimum userclass required to access this entry, default 0 (public)
| `entryZmode` | (Optional) Only display this entry if the client's platform matches.<br>Multiple entries with same `entryZkey` but different `entryZmode` are allowed.

Function/plug-in specific entry keys:
| key | description
|:---:|:---
| `entryZpath` | A file system path
| `entryZext` | File extensions to match, comma-separated list
| `entryZid` | Menu ID number
| `entryZurl` | An URL address

### **\[MENUx\]**
(Where 1 <= x <= {MAIN:menues}) Defines the name and number of sections in menu 'x'

Keys: Same as in MAINMENU.

### **\[MENUxSECTIONy\]**
(Where 1 <= x <= {MAIN:menues} and 1 <= y <= {MAINMENU:sections}) Defines section 'y' of menu 'x'

Keys: Same as MAINMENUSECTIONy.


---
# 2.1 Internal Functions

The following are the function names providing access to internal BBS functionality from the config file.

### Function PCMPLAY:
Enters PCM streaming mode and streams the audio file specified in the parameters.

Configuration file parameter keys:

| key | description
|:---:|:---
| `entryZpath`[^1] | Path to the audio file to stream (must be one of the supported formats)

### Function CHIPPLAY:
Streams the specified chiptune music file.

Configuration file parameter keys:

| key | description
|:---:|:---
| `entryZpath` | Path to the music file to stream (must be one of the supported formats)
| `entryZplayt` | Playtime in seconds
| `entryZsubt` | Subtune to play


### Function SIDPLAY: __-DEPRECATED-!__ use CHIPPLAY instead
Streams the specified .SID or .MUS music file.

Configuration file parameter keys:

| key | description
|:---:|:---
| `entryZpath` | Path to the music file to stream (must be one of the supported formats)
| `entryZplayt` | Playtime in seconds
| `entryZsubt` | Subtune to play

### Function SWITCHMENU:
Switches the BBS to a different menu.

Configuration file parameter keys:

| key | description
|:---:|:---
| `entryZid` | ID number of the menu to switch to

### Function BACK:
Switches the BBS back to the previous menu.

Configuration file parameter keys: NONE

### Function EXIT:
Shows the logoff prompt and terminates the connection if the user confirms to do so.

Configuration file parameter keys: NONE

### Function SLIDESHOW:
Display/streams all the supported files in the specified directory in sequential (alphabetical) order, the user must press `RETURN` to skip to the next file.

Supported file types are:
- *Doodle!*, *ArtStudio*, *Advanced Art Studio*, *Koala Paint*, *GIF*, *PNG* and *JPEG* images
- *MP3* and *WAV* audio files
- BIN and RAW byte streams
- *ASCII* and *PETSCII* text files
- *PETMate* and C syntax *PETSCII* screens

Configuration file parameter keys:

| key | description
|:---:|:---
| `entryZpath` | Path to the slideshow files

### Function FILES:
Display the list of program files in a directory, the user-selected file will be transferred to memory/viewed/saved to disk, depending on the file type and the user choice.

Configuration file parameter keys:

| key | description
|:---:|:---
| `entryZpath` | Path to the program files, default is '/programs'
| `entryZsave` | Set to `True` to allow saving the files to disk.
| `entryZext` | Optional comma separated list of file extensions to display. If omitted the file extensions will be shown on the file browser.

### Function IMAGEGALLERY:
Display the list of images in a directory, the user-selected file will be transferred and displayed.

Configuration file parameter keys:

| key | description
|:---:|:---
| `entryZpath` | Path to the image directory, default is '/images'
| `entryZsave` | Set to `True` to allow saving the files to disk.

### Function AUDIOLIBRARY:
Display the list of audio files in a directory, the user-selected file will be streamed.

Configuration file parameter keys:

| key | description
|:---:|:---
| `entryZpath` | Path to the audio files, default is '/sound'

### Function GRABFRAME:
Grab and display a video frame. File can be in any video format supported by OpenCV

Configuration file parameter keys:

| key | description
|:---:|:---
| `entryZpath` | Path to the video file, can be a local path or a URL

### Function USEREDIT:
Display the user profile editor.

Configuration file parameter keys: NONE

### Function USERLIST:
Display the list of registered users.

Configuration file parameter keys: NONE

### Function INBOX:
Display the user's personal message inbox

Configuration file parameter keys: NONE

### Function BOARD:
Display the message list for the specified board.

Configuration file parameter keys:
| key | description
|:---:|:---
| `entryZid` | Board ID (>0)

See the example `config.ini` for recommended usage.

### Function LABEL:
Display non-interactive text in a menu.
Combine it with an entry description text in 1 column mode for a menu description that doesn't have an associated key.

[^1]: Replace Z in the configuration file parameters with the entry ID number.

### Function SENDFILE:
Send a file to the client, call the appropriate transfer routine. Optionally, show a file dialog or download to disk.<br>
Supported file types include: `JPG, GIF, PNG, ART, OCP, KOA, KLA, DD, DDL, BOTI, MP3, WAV, TXT, SEQ, TML and PRG`
If the save option is enabled, any unsupported file will be transferred to disk

Configuration file parameter keys:
| key | description
|:---:|:---
| `entryZpath` | File path
| `entryZdialog` | Set to True to display a file dialog if available
| `entryZsave` | Set to True to save the file to disk

---
# 3 Plug-In system
*RetroBBS* implements a simple plug-in system, on startup the BBS will import all python modules found in the **\<plugins\>** directory.

All plug-in modules should implement at least two functions:

__setup()__ : This function must returns a tuple consisting of the plug-in name in uppercase, which will be used as the callable function on the config file. And a list of parameters, each element being a tuple itself. This tuple is made of the parameter name to use in the config file, and the corresponding default value in case the parameter is not found.

Example of the returned tuple for a plugin that will use the name 'CHAT' with parameters 'channel' and 'nick', which default to 'offtopic' and 'John' respectively:
```python
('CHAT',[('channel','offtopic'),('nick','John')])
```

__plugfunction(conn, \<extra parameters\>)__ : The BBS will call this function to perform the plug-in's task.<br>The first parameter **\<conn\>** is a Connection object (see Chapter 4) to which the plug-in should direct its output.<br>Any extra parameters will follow, with the same names as returned by setup().

---
# 3.1 Included Plug-Ins

### Astronomy Picture Of the Day (apod.py): 
Retrieves and displays the text and picture from NASA's Astronomy Picture Of the Day.

- Configuration file function: APOD
- Configuration file parameters: NONE
- Configuration file \[PLUGINS\] options: `nasakey` = Your NASA API key, obtained from https://api.nasa.gov/. Default is `DEMO_KEY`

### IRC Client (irc_client.py):
Basic and very experimental IRC client.

- Configuration file function: IRC
- Configuration file parameters:

| key | description
|:---:|:---
| `entryZserver`[^1] | IRC server URL. Default is irc.libera.chat
| `entryZport` | IRC server port. Default is 6667
| `entryZchannel` | IRC channel to enter upon connection. Default is NONE

- Configuration file \[PLUGINS\] options: NONE

### Maps (maps.py) (new 0.50):
Explore the world through maps based on *Openstreetmaps*. Maps are rendered using the _Stamen Design's_ **Toner** tiles.
The map tiles are served by _Stadia Maps_, an API key is required for the plugin to work. To get the API key a free _[Stadia Maps](https://stadiamaps.com/stamen/onboarding/create-account/)_  account is required.

- Configuration file function: MAPS
- Configuration file parameters: NONE
- Configuration file \[PLUGINS\] options:
   - `geoserver` = Geocoder used to retrieve location data. Can be set to either `Nominatim` (default) or `Photon`.
   - `stadiakey` = StadiaMaps API key.

### Mindle (mindle.py) (new 0.50):
Guess the word in this _Wordle_ game clone. Solution list includes words from computer science, retrocomputing, programming, videogames and technology.<br>
Registered users can play for a place in the high score table.

### Oneliner (oneliner.py):
User-generated messages of up to 39 characters. The last 10 messages are stored in a JSON file located in the \<plugins\> directory.

- Configuration file function: ONELINER
- Configuration file parameters: NONE
- Configuration file \[PLUGINS\] options: NONE

### RSS feed reader (newsfeed.py):
Retrieves the latest ten entries from the specified RSS feed, upon user selection of the entry, it scrapes the target website for text and relevant picture. The plug-in is primarily targeted at WordPress sites, if it can't find the content it expects in the linked URL then the article text from the RSS feed itself will be displayed.

- Configuration file function: NEWSFEED
- Configuration file parameters: `entryZurl` = URL to the RSS feed
- Configuration file \[PLUGINS\] options: NONE

### Search Internet Radios (radio.py):
By __Emanuele Laface__</br>
Uses Radio-browser.info API to search for and listen to internet radios.

### Search Podcasts (podcast.py):
By __Emanuele Laface__</br>
Search for and listen to podcasts.

### Weather (weather.py) (new 0.25):
Displays current weather and forecast for the next 2-3 days as a Hires image. On first run it will display the weather corresponding to the passed Connection object's IP. Further weather forecasts can be queried by typing a new location.

- Configuration file function: WEATHER
- Configuration file parameters: NONE
- Configuration file \[PLUGINS\] options: 

  - `wxunits` = `C` or `F` for metric or customary units, respectively. Defaults to metric
  - `wxdefault` = Fallback location. Defaults to Meyrin, Switzerland.
  - `geoserver` = Geocoder used to retrieve location data. Can be set to either `Nominatim` (default) or `Photon`.

### WebAudio streamer (webaudio.py):
 On the fly conversion and streaming of online audio sources (*Shoutcast*,
 *YouTube* or other sources).

- Configuration file function: WEBAUDIO
- Configuration file parameters:

| key | description
|:---:|:---
| `entryZurl` | full URL to the audio stream
| `entryZimage` | Image to show before starting the stream, can be a local path or URL to an external file

- Configuration file \[PLUGINS\] options: NONE

### Wikipedia (wiki.py):
Search and display *Wikipedia* articles, displays relevant article image if found.

- Configuration file function: WIKI
- Configuration file parameters: NONE
- Configuration file \[PLUGINS\] options: NONE

### YouTube snapshot (youtube.py):
Display a frame from the specified *YouTube* video. It will grab the latest frame if the video is a live stream. Otherwise, it grabs a random frame.

- Configuration file function: GRABYT
- Configuration file parameters:

| key | description
|:---:|:---
| `entryZurl` | full URL to the *YouTube* video
| `entryZcrop` | comma-separated list of image coordinates for cropping the video frame

- Configuration file \[PLUGINS\] options: NONE


---
# 3.2 More Plug-ins
Other plug-ins not included in the distribution or by 3rd parties:

 - [QRcode](https://github.com/retrocomputacion/qrcode): Generate and display a QR code

---
# 4 Common modules
Located inside the \<common\> directory you'll find modules which integrate what could be called the BBS' API. The use of some of these modules is mandatory when writing a new plug-in.

## common.audio - Audio/SID streaming:

### AudioList(conn,title,speech,logtext,path):
Creates and manages an PCM audio/SID file browser.
  - **\<conn\>**: Connection object
  - **\<title\>**: String to be used as the title for the file browser
  - **\<speech\>**: Optional string for the voice synthesizer
  - **\<logtext\>**: String to output in the log
  - **\<path\>**: Path to the directory to browse

### PlayAudio(conn,filename, length = 60.0, dialog=False):
Converts and streams a PCM audio file to **\<conn\>**.
- **\<filename\>**: Path to the file to stream, file can be any audio file format supported by audioread/*FFmpeg*
- **\<length\>**: Length of the audio to stream in seconds
- **\<dialog\>**: Boolean, display audio metadata and instructions before starting streaming

### CHIPStream(conn, filename,ptime, dialog=True):
Stream register writes data to the guest's sound chip
- **\<conn\>**: Destination
- **\<filename\>**: Path to the SID file
- **\<ptime\>**: Playtime in seconds
- **\<dialog\>**: Display SID file metadata and instructions before starting streaming


### SIDStream(conn, filename,ptime, dialog=True): __-DEPRECATED-!__ Use CHIPStream instead
Stream a SID file to **\<conn\>**
- **\<filename\>**: Path to the SID file
- **\<ptime\>**: Playtime in seconds
- **\<dialog\>**: Display SID file metadata and instructions before starting streaming

check the [SID streaming](docs/sid_streaming.md) protocol


### class PCMStream(fn, sr) :
Receive an audio stream from *FFmpeg* in chunks.
- **fn**: Path to the audio, can either be a local filename path or an online stream.
- **sr**: Target sample rate

**PCMStream.read(size)**:
Read a chunk of data **size** bytes in length. Returns a byte string

**PCMStream.stop()**:
Terminates an audio stream, and closes *FFmpeg*.

## common.bbsdebug - Log output to stdout:

### _LOG(message, _end='\n', date=True, id=0, v=1):
Prints **\<message\>** on stdout. **\<message\>** can be any expression valid for the print function.<br>The message will end in a newline by default, you can change this by passing a different end string in the **\<_end\>** parameter.<br>By default, the message will be preceded by the current date and time, disable this by passing `False` in the **\<date\>** parameter.
- **\<id\>**: Should be the connection id corresponding to this message. Defaults to 0 -> general message.
- **\<v\>**: Verbosity level for this message. If greater than the level selected on startup, the log message will not be printed.

Also defined in this module is the <bcolors> class, which enumerates a few ANSI codes for use in the log messages.

## common.c64cvt - Image conversion to raw C64 formats: (__-DEPRECATED-__)

### c64imconvert(Source, gfxmode=1, lumaD=0, fullD=6, preproc=True):
Converts PIL image object **\<Source\>** into C64 graphic data.
- **\<gfxmode\>**: selects the C64 graphic mode to use:<br>`0` = HiRes<br>`1` = MultiColor (default)
- **\<lumaD\>**: dithering type for the luminance channel, defaults 0, none
- **\<fullD\>**: color dithering type, defaults to 6, bayer8x8
- **\<preproc\>**: Auto preprocessing of the image brightness/contrast.

Returns a tuple `(e_img,cells,screen,color,bg_color)` where:
- **\<e_img\>**: PIL image object, rendering of the converted image
- **\<cells\>**: C64 bitmap data (8000 bytes)
- **\<screen\>**: C64 screen matrix color data (1000 bytes)
- **\<color\>**: C64 color ram data (1000 bytes), used only in multicolor mode
- **\<bg_color\>**: C64 background color (1 byte), used only in multicolor mode

## common.imgcvt - Image conversion to a native graphic format:

### gfxmodes
Enum containing all the graphic modes supported by _RetroBBS_.

Current supported values:
```
C64HI: Commodore 64 hires bitmap
C64MULTI: Commodore 64 multicolor bitmap
```

### dithertype
Enum containing the available dithering methods:

```
NONE: No dithering
BAYER2: 2x2 Bayer Ordered dither
BAYER4: 4x4 Bayer Ordered dither
BAYER4ODD: 4x4 Bayer Ordered dither, horizontal lines
BAYER4EVEN: 4x4 Bayer Ordered dither, Vertical lines
BAYER4SPOTTY: 4x4 Bayer Ordered dither, spotty
YLILUOMA: Yliluoma type 1 dither, very slow
CLUSTER: Cluster dither
FLOYDSTEINBERG: Floyd-Steinberg error diffusion dither
```

### cropmodes
Enum containing the possible image position/crop/zoom presets:

```
LEFT: No scaling, positioned to the center-left and cropped to the target image size.
TOP: No scaling, positioned to the top-center and cropped to the target image size.
RIGHT: No scaling, positioned to the center-right and cropped to the target image size.
BOTTOM: No scaling, positioned to the bottom-center and cropped to the target image size.
T_LEFT: No scaling, positioned to the top-left and cropped to the target image size.
T_RIGHT: No scaling, positioned to the top-right and cropped to the target image size.
B_LEFT: No scaling, positioned to the bottom-left and cropped to the target image size.
B_RIGHT: No scaling, positioned to the bottom-right and cropped to the target image size.
CENTER: No scaling, centered and cropped to the target image size.
FILL: Scaled and cropped to fill the whole target image size.
FIT: Scaled to fit completely inside the target image size.
H_FIT: Scaled and cropped to fit the target width.
V_FIT: Scaled and cropped to fit the target height.
```

### ColorProcess class
A simple class defining the image processing values:

- Brightness
- Contrast
- Saturation
- Hue
- Sharpness

Creating a ColorProcess without parameters and passing it to *`convert_To`* will result in no image processing being performed.

### convert_To(Source, gfxmode:gfxmodes=gfxmodes.C64MULTI, preproc:ColorProcess=None, dither:dithertype=dithertype.BAYER8, threshold=4, cmatch=1, g_colors=None)
Convert a _PIL_ image to a native graphic format.

- **\<Source\>**: PIL image source, it will automatically be scaled/cropped to fit the target graphic mode
- **\<gfxmode\>**: Target graphic mode
- **\<preproc\>**: Image preprocessing, pass `None` for automatic image adjustment.
- **\<dither\>**: Dither method
- **\<threshold\>**: Dither threshold
- **\<cmatch\>**: Color matching method
- **\<gcolors\>**: Global colors list, pass `None` for best guess

Returns a PIL image rendering of the result, a list of buffers containing the native data (platform/mode dependent), and a list of global colors

### get_IndexedImg(mode:gfxmodes, bgcolor=0)
Returns a PIL "P" image with the dimensions and palette of `mode`, filled with `bgcolor` color index.

### open_Image(filename)
Open a native image file, returns a PIL image object, native image data and graphic mode

## common.classes - Internal use only

## common.connection
Implements the Connection class, this is the class used to communicate with clients, all plug-ins must include this module. Only properties and methods to be used by plug-ins are described below.

### Connection class properties:
- **\<socket\>**: Socket object for this connection. The socket is set to blocking mode by default, with a timeout of 5 minutes.
- **\<addr\>**: Client's IP address **-READ ONLY-**
- **\<id\>**: ID for this connection **-READ ONLY-**
- **\<outbytes\>**: Total number of bytes sent to this client **-READ ONLY-**
- **\<inbytes\>**: Total number of bytes received from this client **-READ ONLY-**
- **\<samplerate\>**: Supported PCM sample rate **-READ ONLY-**
- **\<TermString\>**: Client's terminal ID string **-READ ONLY-**
- **\<T56KVer\>**: Client's terminal reported _Turbo56K_ version **-READ ONLY-**

### Connection class methods:

**QueryFeature(cmd)**: Query the client's terminal if command `cmd` is supported. Returned value is saved during the client's session. The query transaction will happen only the first time for each command.<br>If the command exist the returned value is the number of parameter bytes needed (up to 127). Otherwise the return value will have it's 7th bit set.

**Sendall(cadena)**: Converts string **\<cadena\>** to a binary string and sends it to the client.

**Sendallbin(cadena)**: Sends binary string **\<cadena\>** to the client.

**Flush(ftime)**: Flush the receiving buffer for **\<ftime\>** seconds.

**Receive(count)**: Receives **\<count\>** binary chars from the client.<br>Returns: binary string.

**ReceiveKey(keys=b'\r')**: Wait for a received character from the client matching any of the characters in the **\<keys\>** binary string.<br>Returns: The received matching char as a binary string.

**ReceiveKeyQuiet(keys=b'\r')**: Same as `ReceiveKey`, but no logging is ever performed, disregarding logging level. Use it when a password or other sensitive user data must be received.

**ReceiveStr(keys, maxlen = 20, pw = False)**: Interactive reception with echo. The call is completed on reception of a carriage return.

- **\<keys\>** is a binary string with the accepted input characters
- **\<maxlen\>** is the maximum input string length

Set **\<pw\>** to `True` to echo `*` for each character received, ie, for password entry.<br>Returns: *ASCII* string received.

**ReceiveInt(minv, maxv, defv, auto = False)**: Interactive reception of a positive integer with echo. The user will be restricted to entering a number between **\<minv\>** and **\<maxv\>**, if the user presses `RETURN` instead, the function will return **\<defv\>**.<br> If **\<auto\>** is `True`, the function will return automatically when the user enters the maximum number of digits possible within the limits, or by pressing `DEL` when there's no digit entered. In which case, this function will return `None`.

**ReceiveDate(prompt, mindate, maxdate, defdate)**: Interactive reception of a calendar date with echo. The user will be restricted to enter a date between **\<mindate\>** and **\<maxdate\>**, if the user presses `RETURN` instead, the function will return **\<defdate\>**. The date format will follow the user preference if set, otherwise the global BBS date format will be used. Returns a _datetime.date_ object

**SendTML(data, registers: dict = {'_A':None,'_S':'','_I':0})**: Parse and send a **\<data\>** **TML** script to the client, optionally initialize the TML parser **\<registers\>**. Returns a dictionary with the last states of the TML parser registers.

## common.dbase - Database management:
### getUsers(): 
Get a list of (id, username) pairs. Both `id` and `username` are strings.

### getUserPrefs(id, defaults={}):
Get a dictionary containing the preferences corresponding to the user **\<id\>**. Pass the **\<defaults\>** values in case the user has no/incomplete preferences.

### updateUserPrefs(id,prefs:dict):
Update the preferences corresponding to user **\<id\>** with the contents of the **\<prefs\>** dictionary

## common.filetools - Functions related to file transfer:
### SendBitmap(conn, filename, dialog=False, save= False, lines=25, display=True, gfxmode:gfxmodes=gfxmodes.C64MULTI, preproc:ColorProcess=None, dither:dithertype=dithertype.BAYER8):
Convert image to C64 mode and send it to the client.
__Important: The parameter order has changed since v0.25__

- **\<conn\>**: Connection object
- **\<filename\>**: Path to image file/bytes object/PIL image object
- **\<save\>**: Set to `True` to save the image to disk. Default `False`
- **\<lines\>**: Total number of lines (1 line = 8 pixels) to transfer starting from the top of the screen, max/default = `25`
- **\<display\>**: Set to `True` to send *Turbo56K* commands to display the image after the transfer is completed
- **\<dialog\>**: Set to `True` to send a dialog asking for graphics mode selection before converting and transferring the image
- **\<gfxmode\>**: Target graphic mode. Overridden by user selection if **\<dialog\>** = `True`
- **\<preproc\>**: Image processing parameters prior to conversion. Pass `None` for automatic processing.
- **\<dither>\>**: Dither method to use _if_ the image needs to be converted to `gfxmode`. 

### SendProgram(conn:Connection, filename):
Sends program file into the client memory at the correct address in turbo mode

- **\<conn\>**: Connection object
- **\<filename\>**: Path of the program file to be sent

### SendFile(conn:Connection, filename, dialog = False, save = False):
Calls the right transfer function for each supported file type. If selected, will display a dialog beforehand.

- **\<conn\>**: Connection object
- **\<filename\>**: Path of the file to be sent
- **\<dialog\>**: Set to `True` to send a dialog asking the action to take. Default `False`
- **\<save\>**: Set to `True` to transfer the file to disk. If `dialog` is `True`, then the _save_ option will be added.

### SendRAWFile(conn:Connection, filename, wait = True):
Sends a file directly without processing

- **\<conn\>**: Connection object
- **\<filename\>**: Path of the file to be sent
- **\<wait\>**: Boolean, wait for `RETURN` after sending the file

### TransferFile(conn:Connection, file, savename, seq = False):
Starts a file transfer to disk, pending the client acceptance.

- **\<conn\>**: Connection object
- **\<file\>**: Either the path string to the file to transfer. Or a _bytes_ object with the actual data to be transferred.
- **\<savename\>**: The name used to save the file on the disk. Mandatory if `file` is a _bytes_ object.
- **\<seq\>**: Set to `True` to save the file as a _SEQ_ file. Otherwise, it will be saved as a _PRG_ file.

### SendText(conn:Connection, filename, title = '', lines = 25):
Display a text (.txt) or sequential (.seq) file.

Text files are displayed through `common.helpers.More`.

Sequential files are scanned for _PETSCII_ control codes and interpreted accordingly.

- **\<conn\>**: Connection object
- **\<filename\>**: Path to the file to display
- **\<title\>**: If not empty, will be used to display a title bar. Otherwise, no title bar will be rendered.
- **\<lines\>**: Number if lines available before scrolling.

### SendCPetscii(conn:Connection, filename, pause = 0):
Display a _.c_ formatted C64 text screen, as exported by _PETSCII_ or _PETMate_. Multiple frames per file are supported

- **\<conn\>**: Connection object
- **\<filename\>**: Path to the file to display
- **\<pause\>**: Seconds to pause between frames. Default: 0, wait for user to press RETURN.

### SendPETPetscii(conn:Connection, filename):
Display a _.PET_ formatted C64 text screen, as exported by _PETMate_. Returns immediately

- **\<conn\>**: Connection object
- **\<filename\>**: Path to the file to display

## common.helpers
Misc functions that do not fit anywhere else at this point. Functions might get deprecated and/or moved to other modules in the future.

**valid_keys**: A string containing the valid characters to be used as user input.

**menu_colors**: List containing the odd/even color pairs for menu entries __-DEPRECATED-__.

**font_bold**: Default bold Imagefont for use on bitmaps, 16px height.

**font_big**: Default big Imagefont for use on bitmaps, 24px height.

**font_text**: Default text Imagefont for use on bitmaps, 16px height.


### formatX(text, columns = 40, convert = True)
Formats the **\<text\>** into **\<columns\>** columns with word wrapping, **\<convert\>** selects if *PETSCII* conversion is performed.

### More(conn, text, lines, colors=default_style):
Paginates **\<text\>**, sends it to **\<conn\>**, the user must press `RETURN` to get next page(s). Supports most *PETSCII* control codes, including color and cursor movement.
- **\<lines\>**: how many lines per page to transfer. Useful when using the windowing commands of *Turbo56K*.
- **\<colors\>**: a `bbsstyle` object defining the color set to use.

### text_displayer(conn, text, lines, colors=default_style):
Displays `text` in a text window `lines` in height. Scrolling up and down with the cursor keys.
- **\<conn\>**: Connection object
- **\<text\>**: Preformatted text list, as returned by `formatX`
- **\<lines\>**: How tall is the text window in use. Text window limits must be set before calling `text_displayer`. Actual displayed text lines is `lines`-1
- **\<colors\>**: Color style to use for rendering the text.

### crop(text, length)
Cuts **\<text\>** to max **\<length\>** characters, adding an ellipsis to the end if needed.

### gfxcrop(text, width, font = font_text):
Cuts **\<text\>** to max **\<width\>** pixels using **\<font\>**, adding an ellipsis to the end if needed.

### format_bytes(b):
Convert an integer **\<b\>** depicting a size in bytes to a string rounded up to B/KB/MB/GB or TB

### catalog(path, dirs = False, full = True):
Return a list of files (and subdirectories) in the specified top directory
- **\<path\>**: Top directory
- **\<dirs\>**: Include subdirectories? Default False
- **\<full\>**: Each entry in the list includes the full path. Default True
  
## common.petscii - *PETSCII* <-> *ASCII* tools and constants
Many control codes and graphic characters are defined as constants in this module, it is recommended to inspect it to learn more.

**PALETTE**: A tuple containing the C64 palette control codes in the correct order

**NONPRINTABLE**: A list of all the non-printable *PETSCII* characters

### toPETSCII(text, full = True):
Converts **\<text\>** from *UTF-8* to *PETSCII*, if **\<full\>** is `True`, some characters are replaced with a visually similar *PETSCII* equivalent.

### toASCII(text):
Converts **\<text\>** from *PETSCII* to plain *ASCII*, no extra care is taken to convert *PETSCII* graphic characters to their *ASCII* equivalents

## common.style:
Defines the BBS style, this module is in a very early stage.

The `bbsstyle` class is defined here, and the default_style instance of this class is initialized. Read the module source to find about the different class properties.

### RenderMenuTitle(conn,title):
Sends the menu title header with text **\<title\>** to **\<conn\>**, using the default style. The client screen is cleared and charset is switched to lowercase. Text mode is not enforced, the caller must ensure that text mode or a text window is active on the client.

### KeyPrompt(text,style=default_style,TML=False):
Returns the key prompt string for **\<text\>**. The prompt takes the form `[<text>]` using the colors defined by **\<style\>**</br>
Set `TML` to `True` to return a _TML_ string instead. **IMPORTANT**: _TML_ string output will become the default in the future.

### KeyLabel(conn,key,label,toggle,style=default_style):
Renders menu option **\<label\>** for assigned **\<key\>** in the selected **\<style\>**, boolean **\<toggle\>** switches between odd/even styles.<br>The result is sent to **\<conn\>**

### RenderDialog(conn,height,title):
Renders the background for file view/play/transfer dialogs.
**\<conn\>** Connection object
**\<height\>** Desired height rows for the dialog in screen
**\<title>\>** Optional title string

## common.turbo56k:
Defines the *[Turbo56k](turbo56k.md)* protocol constants and helper functions

The following functions return either a string or a binary string for
use with the Connection.Sendall() or Connection.Sendallbin() methods.

### to_Text(page, border, background, bin = False):
Switch the client screen to text mode.
- **\<page\>** is the text memory page to use
- **\<border\>** and **\<background\>** set the corresponding client screen colors
- **\<bin\>** selects the return string type

### to_Hires(page,border, bin = False):
Switch the client screen to Hires graphic mode.
- **\<page\>** is the bitmap memory page to use
- **\<border\>** is the client screen border color
- **\<bin\>** selects the return string type

### to_Multi(page, border, background, bin = False):
Switch the client screen to multicolor graphic mode.
- **\<page\>** is the bitmap memory page to use
- **\<border\>** and **\<background\>** set the corresponding client screen colors
- **\<bin\>** selects the return string type

### customTransfer(address, bin = False):
Sets the destination address for the next block transfer command.
- **\<address\>** a valid 16-bit integer value for the destination memory address
- **\<bin\>** selects the return string type

### presetTransfer(preset, bin= False):
Set the destination address for the next block transfer to the one defined by **\<preset\>**
- **\<bin\>** selects the return string type

### blockTransfer(data):
Transfer the binary string <data> to the client.<br>This function returns the entire command sequence to complete the transfer as a byte string, including **\<data\>**. Normal usage is calling `SendAllbin` with the result of this function as the parameter

### to_Screen(bin = False):
Selects the client screen as the output.
- **\<bin\>** selects the return string type

### to_Speech(bin = False):
Selects the optional hardware speech synthesizer as text output.
- **\<bin\>** selects the return string type

### reset_Turbo56K(bin = False):
Return a command sequence that enables the cursor, disables split screen and resets text window limits.
- **\<bin\>** selects the return string type

### set_CRSR(column, row, bin= False):
Sets the client's text cursor position to **\<column\>**, **\<row\>** coordinates
- **\<bin\>** selects the return string type

### Fill_Line(row, char, bin= False):
Fill the client screen **\<row\>** with **\<char\>** (in C64 screencode), fill color is the last used.
- **\<bin\>** selects the return string type

### enable_CRSR(bin = False):
Enables the client's text cursor.
- **\<bin\>** selects the return string type

### disable_CRSR(bin = False):
Disables the client's text cursor.
- **\<bin\>** selects the return string type

### split_Screen(line, multi, bgtop, bgbottom, bin = False):
Splits the client's screen into a bitmap top and a text bottom parts.
- **\<line\>** the text screen row on which the split occurs
- **\<multi\>** boolean, `True` for Multicolor mode on the top part, `False` for Hires
- **\<bgtop\>** Background color for the top part, only used when Multicolor mode is selected
- **\<bgbottom\>** Background color for the bottom part
- **\<bin\>** selects the return string type

### set_Window(top, bottom,bin = False):
Set the **\<top\>** and **\<bottom\>** limits for the client text output, this includes scrolling and screen clearing.
- **\<bin\>** selects the return string type

## common.video:
Video related routines.

### Grabframe(conn:Connection, path, crop, length = None, pos = None):
Grab's a frame from the specified video file/stream.
- **\<conn\>** connection to send the image to
- **\<path\>** video file/stream path or URL
- **\<crop\>** a tuple with the 4 corners coordinates for cropping the video frame, or None
- **\<length\>** video playtime in milliseconds. Pass None to let _Grabframe_ to figure the playtime, or 0 to indicate a live stream
- **\<pos>\>** Grab the frame at `pos` milliseconds. Pass None for random frame. Ignored if the video is a live stream

---
# 5 Encoders
Starting on v0.50 RetroBBS is moving towards an encoding agnostic implementation. This means reducing to the minimum instances of hard coded platform specific strings and control codes, replacing them with generic ASCII/Unicode strings and _TML_ tags.

For this purpose a new `Encoder` class has been created.</br>
This class provides platform specific encoding/decoding of strings, as well as defining the basic control codes and color palette.

Currently, only the `PET64` and `PET264` encoders are implemented, corresponding to the _Commodore 64_ and _Commodore Plus/4_ PETSCII encodings respectively.

---
# 6 Installation/Usage
After ensuring you have installed all the required python modules and extra software, just unpack this archive into a directory of your choice.<br>
If you're upgrading a previous installation, make sure to not overwrite your configuration files with the ones included as example.

  **NOTICE**: Starting at v0.20, all text parameters in the config file are expected to be encoded in *ASCII*, if you're updating from v0.10, remember to convert your *PETSCII* parameters.


You can run this script from a command line by navigating to the Installation
directory and then issuing:

    python retrobbs.py

or

    python3 retrobbs.py

depending on your python install.

Optional arguments:
 - `-v[1-4]` sets the verbosity of the log messages, a value of 1 will only output error messages, while a value of 4 will output every log line.
 - `c [file name]` sets the configuration file to be used, defaults to `config.ini`

---
# 6.1 The intro/login sequence
Once a connection with a client is established and a supported version of *Retroterm* is detected, the client will enter into split screen mode and display the `splash.art` bitmap file found in the `bbsfiles` path preset.
The user will then be asked if he wants to log in or continue as a guest.

After a successful login or directly after choosing guest access, the supported files in the subdirectory `[bbsfiles]/intro` will be shown/played in alphabetical order.

Starting in v0.50 an example _TML_ script is placed at the end of the `[bbsfiles]/intro` sequence. This script will greet a logged-in user and show the amount of unread public and private messages if any.

---
# 6.2 SID SongLength
Currently, the SID streaming routines are only accessed from the `AUDIOLIBRARY` and `SLIDESHOW` internal functions. These functions will set the song length by searching for the `.ssl` files corresponding the `.sid` files found, defaulting to 3 minutes when not found.<br>
The `.ssl` format is used by the songlength files part of the *High Voltage SID Collection* (http://hvsc.c64.com). *HVSC* uses a `SONGLENGTHS` subdirectory to store the `.ssl` files, *RetroBBS* can also read these files in the same directory where the `.sid` files are located.

---
# 6.3 User accounts / Database management
*RetroBBS* now supports the creation of user accounts, this allows for the restriction of BBS areas according to user classes and the incorporation of the messaging system.

*TinyDB* is used as the database backend. The database is a *JSON* file located in the `bbsfiles` directory.

Upon registering, the user will be shown the file `rules.txt` located in `bbsfiles/terms`, you should edit this file according to your needs.

When registering, the user will be asked the following data:

  - Password (stored as a salted hash in the database)
  - First and last names
  - Country of origin
  - Date of birth (Date format is defined by the `dateformat` parameter in the config file)

A registered user will have a userclass=1 by default. Unregistered users (guests) have a userclass=0.
Admins/Sysops are those with a userclass=10.

You can use user classes 2 to 9 for more access granularity as you see fit.

A separate script for database management is included in the form of `dbmaintenance.py`<br>Execute it by issuing the following command (while the BBS is not running):

    python dbmaintenance.py

    or

    python3 dbmaintenance.py

With this script you can:

  * Edit user data, and change their user class.
  * Delete users
  * Add users

The script will also do a quick integrity check on the database file.

**IMPORTANT**: When setting up a new BBS (or upgrading from v0.10) use dbmaintenance.py to create your account and set your class as 10 to assign yourself as admin/sysop.

---
# 6.4 Messaging system
The messaging system permits unlimited public or semipublic boards plus a personal messages board for each registered user.

At the time of writing, this early implementation supports messages of up to 720 characters in length, organized in 18 rows of 40 columns each.
The message editor works on a per-line basis, completing a by pressing `RETURN`, passing the 40 characters limit, or selecting another line to edit (by pressing `F3`).
On entering the editor, if the user is starting a new message thread, they will be asked first to enter a topic for the thread.
Once done with the editing, the user should press `F8` and will be prompted if they want to continue editing, send the message, or cancel the message.

A user with admin/sysop user class (10) can delete threads or individual messages (deleting the first message in a thread will delete the whole thread).

---
# 6.5 Temporal directory
The path preset `temp` is used by the BBS or it's plugins to store temporal files.

Currently, only the SID streaming function makes use of this path.

If you're running the BBS from a Raspberry Pi or other SBC that uses an SD card as main storage we recommend creating a RAM disk and point the `temp` path to it. This will reduce the wear on your SD card.

### Creating a RAM disk
First create a mount point:
```
sudo mkdir /mnt/ramdisk
```
(You can replace _ramdisk_ by any valid name of your choice)

Next you have to mount your new RAM disk:

```
sudo mount -t tmpfs -o rw,size=1M tmpfs /mnt/ramdisk
```
Here the "1M" means the RAM disk will have a size of 1 Megabyte, this is more than enough for current use by the BBS, but this can change in the future.

To make this change permanent you'll need to add the previous command to your fstab file.

First make a backup of your fstab file:
```
sudo cp -v /etc/fstab /etc/fstab.backup
```
Next open /etc/fstab in your favorite text editor (as administrator), and add the following line at the end of the file:

```
sudo mount -t tmpfs -o rw,size=1M tmpfs /mnt/ramdisk
```
And save it.

On your next reboot /mnt/ramdisk should be mounted and ready to use.

Lastly change the `temp` path in your configuration file:
```ini
...
[PATHS]
temp = /mnt/ramdisk/
...
```

---
# 7 TO-DO List

 * More code cleanup, move more functions out of the main script and into their corresponding modules.
 * Work towards user style customization
 * Localization
 * Custom logout sequence, similar to the login one
 * Figure out a way to remove hard-coded filetype handling.

---
# 7.1 Known bugs/issues

  * Config file parser still doesn't check for errors, a poorly built configuration file will cause a crash on startup.
  * If updating from v0.10, the messages already existing in the oneliners.json file will have the wrong encoding. New messages will display correctly.


---
# 8 Acknowledgements

## Development team

  * Jorge Castillo (Pastbytes) - Original idea, creator and developer of *Turbo56K*, *Retroterm* and *RetroBBS*
  * Pablo Roldán (Durandal) - Developer of *RetroBBS* and *Retroterm*, extension of *Turbo56K* protocol

## Thanks

Thanks go to the following persons who helped in the testing of *RetroBBS*

  * Thierry Kurt
  * Ezequiel Filgueiras
  * Juan Musso
  * Vaporatorius
  * Gabriel Garcia
  * Roberto Mandracchia
  * ChrisKewl - [twitter.com/chriskewltv](http://twitter.com/chriskewltv)

Also many thanks to __Emanuele Laface__ for the *Radio* and *Podcast* plugins.

## External software, support files

  * SIDdump by Lasse Öörni (cadaver)
  * FFmpeg by the FFmpeg team
  * Betterpixels font by AmericanHamster
  * karen2blackint font by PaulSpades
  * Map tiles by [Stamen Design](http://stamen.com), under [CC BY 3.0](http://creativecommons.org/licenses/by/3.0). Data by [OpenStreetMap](http://openstreetmap.org), under [ODbL](http://www.openstreetmap.org/copyright).

## Contains code from:

  * sid2psg.py by simondotm under MIT license (https://github.com/simondotm/ym2149f/tree/master)

---