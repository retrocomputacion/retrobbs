###################################
#       File transfer tools       #
###################################

import re
import os
import time
import socket
import errno
from common.connection import Connection
from common import helpers as H
from common import audio as AA
from PIL import Image
from common.imgcvt import convert_To, gfxmodes, PreProcess, dithertype, cropmodes, open_Image, mode_conv, build_File, im_extensions, GFX_MODES
from io import BytesIO
from common import turbo56k as TT
from common import style as S
from common.bbsdebug import _LOG, bcolors
from crc import Calculator, Configuration
from ymodem.Socket import ModemSocket
from ymodem.Protocol import ProtocolType
# import logging
import zipfile
import lhafile
from d64 import DiskImage

########################################################################
# Show a file browser, call fhandler on user selection
########################################################################
# conn: Connection
# title: Title of the file list
# logtext: Text to send to the log
# path: Root path to display
# ffilter: List of file extensions to show, or None to show all files
# fhandler: Function to call upon user selection
# transfer: Boolean, allow file transfers
# subdirs: Boolean, allow to show and browse subdirectories 
########################################################################
def FileList(conn:Connection,title,logtext,path,ffilter,fhandler,transfer=False,subdirs=True):

    st = conn.style
    scwidth,scheight = conn.encoder.txt_geo
    win_s = conn.encoder.features['windows'] != 0
    if win_s:
        r_offset = 0
    else:
        r_offset = 4

    max_e = scheight-7      # Number of entries per page
    e_width = scwidth-8    # Max characters per entry

    curpath = path  # Current path in use
    c_page = 0      # Current page

    if type(path) is not str:
        curpath = '/'
        if type(path) == zipfile.ZipFile:
            filelist = path.infolist()
        elif type(path) == lhafile.lhafile.LhaFile:
            filelist = path.infolist()
            depth = -1
            dix = ''
            for i,f in enumerate(filelist):
                c = f.filename.count('\\')
                if c > 0:
                    if c > depth:
                        depth = c
                        dix = f.filename
                filelist[i].directory = False
                filelist[i].filename = f.filename.replace('\\','/')
            if dix != '':
                dirs = dix.split('\\')[:-1]
                for i in range(1,len(dirs)+1):
                    linfo = lhafile.LhaInfo()
                    linfo.filename = '/'.join(dirs[:i])+'/'
                    linfo.directory = True
                    filelist.append(linfo)
        else:
            # print(type(path))
            return
        realpath = False
    else:
        realpath = True

    _LOG(logtext,id=conn.id, v=4)

    # Send speech message
    # Select screen output
    conn.SendTML(f'<PAUSE n=1><SETOUTPUT><NUL n=2><CURSOR><TEXT border={conn.style.BoColor} background={conn.style.BgColor}>')
    if win_s:
        S.RenderMenuTitle(conn,title)
        conn.SendTML(conn.templates.GetTemplate('main/navbar',**{'barline':scheight-2,'crsr':'A/Z','pages':'N/M','keys':[('U','parent')]}))
        if realpath:
            t_path = curpath.replace(path[:-1],'',1)
            if len(t_path) > (scwidth-len(conn.encoder.ellipsis)-8):
                t_path = conn.encoder.ellipsis+t_path[-scwidth-len(conn.encoder.ellipsis)-8:]
        else:
            tpath = '/'
        conn.SendTML(f'<AT x=0 y=3><RVSON><INK c={st.RvsColor}> Path: {t_path}<RVSOFF>')
        conn.SendTML(f'<WINDOW top=4 bottom={scheight-3}>')


    # Main loop
    while conn.connected:
        programs = []	#filtered list
        directories = [] # subdirectories

        #Read all files from 'path'
        if type(path) in [zipfile.ZipFile,lhafile.lhafile.LhaFile]:
            for entry in filelist:
                # print(entry.filename)
                if len(curpath) != 1:
                    tname = entry.filename.replace(curpath[1:],'',1)
                    if tname == entry.filename:
                        continue
                else:
                    tname = entry.filename
                # print(tname)
                if type(path) == zipfile.ZipFile:
                    isdir = entry.is_dir()
                else:
                    isdir = entry.directory
                if isdir:
                    if tname.count('/') == 1:
                        directories.append(tname)
                elif tname.count('/') == 0:
                        programs.append([tname,entry.file_size])
        else:
            for entry in os.scandir(curpath):
                if entry.is_file():
                    if len(ffilter) > 0:
                        if os.path.splitext(entry.name)[1].upper() in ffilter:
                            programs.append([entry.name,entry.stat().st_size])
                    else:
                        programs.append([entry.name,entry.stat().st_size])
                elif entry.is_dir():
                    directories.append(entry.name)

        programs = sorted(programs, key= lambda l:l[0]) #programs.sort()     #Sort files
        directories.sort()  #Sort subdirectories

        pages = int(((len(programs)+(len(directories) if subdirs else 0))-1) / max_e) + 1
        count = len(programs)+(len(directories) if subdirs else 0)
        # Page render loop
        display = True
        row = 0
        while conn.connected:
            if display:
                conn.SendTML('<CURSOR>')
                conn.SendTML('<CLR>')
                if not win_s:
                    S.RenderMenuTitle(conn,title)
                    conn.SendTML(conn.templates.GetTemplate('main/navbar',**{'barline':scheight-2,'crsr':'A/Z','pages':'N/M','keys':[('U','parent')]}))
                    if realpath:
                        t_path = curpath.replace(path[:-1],'',1)
                    else:
                        t_path = curpath
                    if len(t_path) > (scwidth-len(conn.encoder.ellipsis)-8):
                        t_path = conn.encoder.ellipsis+t_path[-scwidth-len(conn.encoder.ellipsis)-8:]
                    conn.SendTML(f'<AT x=0 y=3><RVSON><INK c={st.RvsColor}> Path: {t_path}<RVSOFF>')
                    conn.SendTML('<AT x=0 y=4>')
                conn.SendTML('')
                start = c_page * max_e
                end = min(start+max_e,count)-1
                # end = start + (max_e-1)
                # if end >= count:
                #     end = count - 1
                if fhandler == SendFile:
                    keywait = False
                else:
                    keywait = True
                page_entries = []
                for x in range(start, end + 1):
                    ix = x - (len(directories) if subdirs else 0)
                    if x < len(directories) and subdirs:
                        if len(directories[x]) > e_width+6:
                            label = H.crop(directories[x], e_width+6, conn.encoder.ellipsis)+'<BR>'
                        else:
                            label = directories[x]+'<BR>'
                        e_color = f'<INK c={st.TevenColor}>'
                        page_entries.append([directories[x],True])
                    else:
                        if len(programs[ix][0]) > e_width:
                            fn = os.path.splitext(programs[ix][0])
                            label = H.crop(fn[0],e_width-len(fn[1])+1, conn.encoder.ellipsis)+fn[1]
                            # label = fn[0][:e_width-len(fn[1])]+fn[1]
                        else:
                            label = programs[ix][0]
                        e_color = f'<INK c={st.TxtColor}>'
                        page_entries.append([programs[ix][0],False])
                        # label += ' ' + format_bytes(programs[ix][1])
                    conn.SendTML(f'{e_color} {label}')
                    if not page_entries[-1][1]:
                        size = H.format_bytes(programs[ix][1])
                        conn.SendTML(f'<INK c={st.TevenColor}><CRSRR n={(e_width-len(label))+(7-len(size))}>{size}')
                    
                conn.SendTML(f'<WINDOW><AT x=0 y={scheight-1}><WHITE> [{c_page+1}/{pages}] <CURSOR enable=False>')
                conn.SendTML(f'<WINDOW top=4 bottom={scheight-3}><YELLOW>')
                display = False
            conn.SendTML(f'<AT x=0 y={row+r_offset}>&gt;<CRSRL>')
            key = conn.ReceiveKey(['a','z','u','m','n',conn.encoder.back,conn.encoder.nl])
            if key == conn.encoder.back:
                conn.SendTML('<CURSOR><WINDOW>')
                if type(path) == zipfile.ZipFile:
                    path.close()
                return
            elif key == 'a':
                if row > 0:
                    conn.SendTML(' ')
                    row -= 1
                elif pages > 1:
                    row = 0
                    if c_page > 0:
                        c_page -= 1
                    else:
                        c_page = pages-1
                    display = True
            elif key == 'z':
                if row < len(page_entries)-1:
                    conn.SendTML(' ')
                    row += 1
                elif pages > 1:
                    row = 0
                    if c_page != pages-1:
                        c_page +=1
                    else:
                        c_page = 0
                    display = True
            elif key == 'm' and pages > 1:
                row = 0
                if c_page != pages-1:
                    c_page +=1
                else:
                    c_page = 0
                display = True
            elif key == 'n' and pages > 1:
                row = 0
                if c_page > 0:
                    c_page -= 1
                else:
                    c_page = pages-1
                display = True
            elif key == 'u':   # Parent dir
                if realpath:
                    if len(curpath) > len(path):
                        curpath = '/'.join(curpath.split('/')[:-2])+'/'
                        c_page = 0
                        if win_s:
                            if realpath:
                                t_path = curpath.replace(path[:-1],'',1)
                            else:
                                t_path = curpath
                            if len(t_path) > (scwidth-len(conn.encoder.ellipsis)-8):
                                t_path = conn.encoder.ellipsis+t_path[-scwidth-len(conn.encoder.ellipsis)-8:]
                            conn.SendTML(f'<CLR><WINDOW><AT x=0 y=3><SPC n=39><AT x=0 y=3><RVSON><INK c={st.RvsColor}> Path: {t_path}<RVSOFF>')
                            conn.SendTML(f'<WINDOW top=4 bottom={scheight-3}>')
                        break
                else:
                    if len(curpath) > 1:
                        curpath = '/'.join(curpath.split('/')[:-2])+'/'
                        c_page = 0
                        if win_s:
                            if realpath:
                                t_path = curpath.replace(path[:-1],'',1)
                            else:
                                t_path = curpath
                            if len(t_path) > (scwidth-len(conn.encoder.ellipsis)-8):
                                t_path = conn.encoder.ellipsis+t_path[-scwidth-len(conn.encoder.ellipsis)-8:]
                            conn.SendTML(f'<CLR><WINDOW><AT x=0 y=3><SPC n=39><AT x=0 y=3><RVSON><INK c={st.RvsColor}> Path: {t_path}<RVSOFF>')
                            conn.SendTML(f'<WINDOW top=4 bottom={scheight-3}>')
                        break
                    else:   # We can exit the image/archive
                        conn.SendTML('<CURSOR><WINDOW>')
                        if type(path) == zipfile.ZipFile:
                            path.close()
                        return
            elif key == conn.encoder.nl:
                if not page_entries[row][1]:
                    conn.SendTML('<WINDOW>')
                    filename = curpath+page_entries[row][0]
                    if not realpath:   # Extract file to temp folder
                        filename = conn.bbs.Paths['temp']+page_entries[row][0]
                        arcname = (curpath+page_entries[row][0])[1:]
                        print(arcname)
                        if type(path) == lhafile.lhafile.LhaFile:
                            # filename = filename.replace('/','\\')
                            arcname = arcname.replace('/','\\')
                            data = path.read(arcname)
                            with open(filename,'wb') as tf:
                                tf.write(data)
                        else:
                            path.extract(arcname,conn.bbs.Paths['temp'])
                    if fhandler == SendFile:
                        parameters = (conn,filename,True,transfer,)
                    else:
                        parameters = (conn,filename,True,transfer,)
                    fhandler(*parameters)
                    if keywait:
                        conn.ReceiveKey
                    conn.SendTML(f'<PAUSE n=1><SETOUTPUT><NUL n=2><CURSOR><TEXT border={conn.style.BoColor} background={conn.style.BgColor}>')
                    if win_s:
                        S.RenderMenuTitle(conn,title)
                        if realpath:
                            t_path = curpath.replace(path[:-1],'',1)
                        else:
                            t_path = curpath
                        if len(t_path) > (scwidth-len(conn.encoder.ellipsis)-8):
                            t_path = conn.encoder.ellipsis+t_path[-scwidth-len(conn.encoder.ellipsis)-8:]
                        conn.SendTML(f'<AT x=0 y=3><SPC n=39><AT x=0 y=3><RVSON><INK c={st.RvsColor}> Path: {t_path}<RVSOFF>')
                        conn.SendTML(conn.templates.GetTemplate('main/navbar',**{'barline':scheight-2,'crsr':'A/Z','pages':'N/M','keys':[('U','parent')]}))
                        conn.SendTML(f'<WINDOW top=4 bottom={scheight-3}>')
                    display = True
                else:   # Change dir
                    curpath = curpath + page_entries[row][0] + ('/' if realpath else '')
                    c_page = 0
                    if win_s:
                        if realpath:
                            t_path = curpath.replace(path[:-1],'',1)
                        else:
                            t_path = curpath
                        if len(t_path) > (scwidth-len(conn.encoder.ellipsis)-8):
                            t_path = conn.encoder.ellipsis+t_path[-scwidth-len(conn.encoder.ellipsis)-8:]
                        conn.SendTML(f'<CLR><WINDOW><AT x=0 y=3><SPC n=39><AT x=0 y=3><RVSON><INK c={st.RvsColor}> Path: {t_path}<RVSOFF>')
                        conn.SendTML(f'<WINDOW top=4 bottom={scheight-3}>')
                    break


########################################################################
# Display image dialog
########################################################################
# conn: Connection
# title: Title of the dialog
# width/height: Original size of the image
# save: Show save option
########################################################################
# Returns:	Bit 1: Graphic mode 0: Hires | 1: Multicolor
#			Bit 7: 0: View Image | 1: Save image
########################################################################
def ImageDialog(conn:Connection, title, width=0, height=0, save=False):
    S.RenderDialog(conn, (11 if save and width !=0 else 10), title)
    keys=  [conn.encoder.back] #conn.encoder.nl
    tml = ''
    if width != 0:
        tml += f'<RVSON> Original size: {width}x{height}<BR><BR>'
        if 'PET' in conn.mode:
            tml +='''<RVSON> Select:<BR><BR><RVSON> * &lt; M &gt; for multicolor conversion<BR>
<RVSON>   &lt; H &gt; for hi-res conversion<BR>'''
            keys.extend(['h','m'])
            out = 1
        else:
            out = 0
    elif 'PET' in conn.mode:
        out = 1
    else:
        out = 0
    if save:
        tml += '<BR><RVSON> &lt; S &gt; to save image<BR>'
        keys.append('s')
    if conn.QueryFeature(TT.PRADDR) < 0x80 or (conn.T56KVer == 0 and len(conn.encoder.gfxmodes) > 0):
        tml += '<RVSON> &lt; RETURN &gt; to view image<BR>'
        keys.append(conn.encoder.nl)
    tml += '<RVSON> &lt; <BACK> &gt; to exit<CURSOR enable=False>'
    conn.SendTML(tml)
    while conn.connected:
        k = conn.ReceiveKey(keys)
        if k == 'h' and out == 1:
            conn.SendTML('<RVSON><AT x=1 y=5> <CRSRD><CRSRL>*')
            out = 0
        elif k == 'm' and out == 0:
            conn.SendTML('<RVSON><AT x=1 y=6> <CRSRU><CRSRL>*')
            out = 1
        elif k == 's':
            out |= 0x80
            break
        elif k == conn.encoder.nl:
            break
        elif k == conn.encoder.back:
            out = -1
            break
    conn.SendTML('<RVSON><CURSOR>')
    return out

######################################################################################################################################################################################################################################
# Send bitmap image
######################################################################################################################################################################################################################################
# conn: Connection to send the image/dialog to
# filename: file name or image object
# lines: Number of "text" lines to send, from the top
# display: Display the image after transfer
# dialog: Show convert options dialog before file transfer
# gfxmode: Graphic mode
# preproc: Preprocess image before converting
######################################################################################################################################################################################################################################
def SendBitmap(conn:Connection, filename, dialog = False, save = False, lines = 25, display = True,  gfxmode:gfxmodes = None, preproc:PreProcess = None, cropmode:cropmodes = cropmodes.FILL, dither:dithertype = dithertype.BAYER8):

    lines = lines if lines < conn.encoder.txt_geo[1] else conn.encoder.txt_geo[1]

    if conn.T56KVer > 0:
        if conn.QueryFeature(TT.PRADDR) >= 0x80 and not save:
            return False
    elif len(conn.encoder.gfxmodes) == 0 and not save:
        return False
    
    cmode = conn.mode


    gfxmulti = -1
    if gfxmode == None:
        gfxmode = conn.encoder.def_gfxmode
    if 'PET64' in conn.mode:
        gfxhi = gfxmodes.C64HI
        gfxmulti = gfxmodes.C64MULTI
        cmode = 'PET64'
    elif conn.mode == 'PET264':
        gfxhi = gfxmodes.P4HI
        gfxmulti = gfxmodes.P4MULTI
    elif conn.mode == 'MSX1':
        gfxhi = gfxmodes.MSXSC2
        gfxmulti = -1
    elif conn.mode == 'VidTex':
        gfxhi = gfxmodes.VTHI if gfxmodes.VTHI in conn.encoder.gfxmodes else gfxmodes.VTMED
        gfxmulti = -1
    else:
        return False

    ftitle = {'.GIF':' GIF  Image ', '.PNG':' PNG  Image ', '.JPEG':' JPEG Image ', '.JPG':' JPEG Image '}
    fok = '<CLR><LOWER><GREEN>File transfer successful!<BR>'
    fabort = '<CLR><LOWER><ORANGE> File transfer aborted!<BR>'

    # Find image format
    data = [None]*3
    bgcolor = None
    border = None

    mode = 1 if gfxmode == gfxmulti else 0
    save &= (conn.QueryFeature(TT.FILETR) < 0x80 or conn.T56KVer == 0)
    pimg = None
    convert = False
    Source = None
    th = 4

    if type(filename)==str:
        extension = os.path.splitext(filename)[1].upper()
        if extension not in ['.GIF','.PNG','.JPG','JPEG']:
            pimg = open_Image(filename)
            if pimg == None:	#Invalid file, exit
                return False
            elif pimg[1] not in conn.encoder.gfxmodes:	#Image from another platform, convert
                convert = True
                Source = pimg[0]
                if preproc == None:
                    preproc = PreProcess()
                cropmode = cropmodes.BIG_FILL
                if gfxmode == None:
                    # print(mode_conv, cmode, pimg[1])
                    gfxmode = mode_conv[cmode][pimg[1]]
                th = 3
            else:
                gfxmode = pimg[1]
                data = pimg[2]
            text = pimg[4]
            border = pimg[3][0]
            gcolors = pimg[3]
        else:
            text = ftitle[extension]
            convert = True
    else:
        convert = True

    if convert:
        conn.SendTML('<SPINNER><CRSRL>')
        if Source == None:
            if type(filename)==str:
                Source = Image.open(filename)
            elif type(filename)==bytes:
                Source = Image.open(BytesIO(filename))
            elif isinstance(filename,Image.Image):
                Source = filename
        Source = Source.convert("RGB")
        if dialog:
            mode = ImageDialog(conn,text,Source.size[0],Source.size[1],save)
            if mode < 0:
                return False
            conn.SendTML('<SPINNER><CRSRL>')
        else:
            mode = 1 if (gfxmode == gfxmulti) else 0
        gfxmode = gfxmulti if (mode & 0x7f) == 1 else gfxhi
        if preproc == None and cmode == 'PET264':
            preproc = PreProcess(1,1.5,1.5)
        cvimg,data,gcolors = convert_To(Source, gfxmode, preproc, cropmode=cropmode,dither=dither, threshold=th)
        Source.close()
        bgcolor = bytes([gcolors[0]])	#Convert[4].to_bytes(1,'little')
        gcolors = [gcolors[0]]+gcolors # Border color = bgcolor
        #
        border = bgcolor if border == None else bytes([border])
    elif pimg != None and dialog:
        mode = ImageDialog(conn,text,save=save)
        if mode < 0:
            return False


    alines = lines*(8//GFX_MODES[gfxmode]['attr'][1])   # <<<< This assumes a text line is 8 pixels tall

    # Screen mem byte count (C64) / Color data byte count (Plus4) / NameTable byte count (MSX)
    tchars = (GFX_MODES[gfxmode]['out_size'][0]//(8//GFX_MODES[gfxmode]['bpp']))*lines
    # ColorRAM byte count (C64) / Luminance byte count (Plus4) / ColorTable byte count (MSX)
    tcolor = (GFX_MODES[gfxmode]['out_size'][0]//GFX_MODES[gfxmode]['attr'][0])*alines
    # Bitmap byte count
    tbytes = GFX_MODES[gfxmode]['out_size'][0]*GFX_MODES[gfxmode]['bpp']*lines    # <<<< This assumes a text line is 8 pixels tall

    # tchars = 40*lines
    # tbytes = 320*lines

    if mode & 0x80 == 0:	# Transfer to memory

        if conn.T56KVer > 0:    #Turbo56K memory transfer
            # Sync
            binaryout = b'\x00'
            # Enter command mode
            binaryout += b'\xFF'
            # Set the transfer pointer + $10 (bitmap memory)
            binaryout += b'\x81\x10'
            # Transfer bitmap block + Byte count (low, high)
            binaryout += b'\x82'
            binaryout += tbytes.to_bytes(2,'little')	#Block size

            if display:
                conn.SendTML('<CURSOR enable=False>')	#Disable cursor blink
            conn.Sendallbin(binaryout)

            # Bitmap data
            binaryout = data[0][0:tbytes] #Bitmap
            # Set the transfer pointer + $00 (screen memory)
            binaryout += b'\x81\x00'
            # Transfer screen block + Byte count (low, high)
            binaryout += b'\x82'
            binaryout += tchars.to_bytes(2,'little')	#Block size
            # Screen Data
            binaryout += data[1][0:tchars] #Screen
            if border == None:
                border = b'\x00' if bgcolor == None else bgcolor
            border = bytes([border]) if type(border) == int else border
            if (gfxmode == gfxmulti) or (cmode != 'PET64' and data[2] != None):
                # Set the transfer pointer + $20 (color memory)
                if 'MSX' in cmode:
                    binaryout += b'\x81\x21'
                else:
                    binaryout += b'\x81\x20'
                # Transfer color block + Byte count (low, high)
                binaryout += b'\x82'	# Color data
                binaryout += tcolor.to_bytes(2,'little')	#Block size
                binaryout += data[2][0:tcolor] #ColorRAM
            if bgcolor == None:
                bgcolor = bytes([gcolors[1]]) if gcolors[1] != None else b'\x00'
            if display:
                if gfxmode == gfxmulti:
                    # Switch to multicolor mode + Page number: 0 (default) + Border color: border + Background color: bgcolor
                    binaryout += b'\x92\x00'
                    binaryout += border
                    binaryout += bgcolor
                    if cmode == 'PET264':
                        binaryout += gcolors[4].to_bytes(1,'big')
                else:
                    # Switch to hires mode + Page number: 0 (default) + Border color: border
                    binaryout += b'\x91\x00'
                    binaryout += border
            # Exit command mode
            binaryout += b'\xFE'
            # if display:
            #     conn.Sendall(TT.disable_CRSR())	#Disable cursor blink
            conn.Sendallbin(binaryout)
            return bgcolor
        else:   #Other image transfers
            if conn.mode == 'VidTex':
                conn.encoder.SetVTMode('M') # Just set the internal flag to something different than text mode. See VT52encoder.SetBTMode() for the reason
                if len(data[0]) > 15000:    # Increase socket timeout in case the RLE stream is too big (Assuming 600 baud connection)
                    conn.socket.settimeout(60.0*10)  # A dynamic value would be even better
            conn.Sendallbin(bytes(data[0])) #Assume data[0] already has the required 'commands' to set the client in the correct mode
    else:
        savename = os.path.splitext(os.path.basename(filename))[0]
        if cmode in ['PET64','PET264']:
            savename = savename.upper().translate({ord(i): None for i in ':#$*?'})	#Remove CBMDOS reserved characters
        binaryout, savename = build_File(data,gcolors,savename, gfxmode)
        if conn.T56KVer > 0:
            if TransferFile(conn, binaryout, savename):
                conn.SendTML(fok)
            else:
                conn.SendTML(fabort)
        else:
            with open(conn.bbs.Paths['temp']+savename,"wb") as oh:
                oh.write(binaryout)
            if xFileTransfer(conn,conn.bbs.Paths['temp']+savename,savename):
                conn.SendTML(fok)
            else:
                conn.SendTML(fabort)
        conn.SendTML('<KPROMPT t=RETURN>')
        return

####################################################################################
# Sends a file to the client, calls the adequate function according to the filetype
####################################################################################
# conn: Connection
# filename: path to the file to transfer
# dialog: Show dialog before transfer
# save: Allow file downloading to disk
####################################################################################
def SendFile(conn:Connection,filename, dialog = False, save = False):
    fok = '<CLR><LOWER><GREEN>File transfer successful!<BR>'
    fabort = '<CLR><LOWER><ORANGE> File transfer aborted!<BR>'
    if os.path.exists(filename):
        ext = os.path.splitext(filename)[1].upper()
        # Executables
        if ext == '.PRG' and 'PET' in conn.mode:    # Commodore PRG
            if conn.encoder.check_fit(filename):
                if dialog:
                    res = FileDialog(conn,os.path.basename(filename), os.path.getsize(filename), 'Commodore Program', save = save)
                else:
                    res = 1+(1*save)
            elif save:
                if dialog:
                    res = FileDialog(conn,os.path.basename(filename), os.path.getsize(filename), 'Commodore Program','Download to disk', save = False)*2
                else:
                    res = 2
            else:
                res = 0
            if res == 1:
                SendProgram(conn,filename)
            elif res == 2:
                savename = os.path.splitext(os.path.basename(filename))[0].upper()
                savename = savename.translate({ord(i): None for i in ':#$*?'})	#Remove CBMDOS reserved characters
                if TransferFile(conn,filename, savename[:16]):
                    conn.SendTML(fok)
                else:
                    conn.SendTML(fabort)
                conn.SendTML('<KPROMPT t=RETURN>')
                conn.ReceiveKey()
            return
        elif ext == '.ROM' and 'MSX' in conn.mode:  # MSX ROM
            if conn.encoder.check_fit(filename):
                if dialog:
                    res = FileDialog(conn,os.path.basename(filename), os.path.getsize(filename), 'MSX ROM', save = save)
                else:
                    res = 1+(1*save)
            elif save:
                if dialog:
                    res = FileDialog(conn,os.path.basename(filename), os.path.getsize(filename), 'MSX ROM','save to disk', save = False)*2
                else:
                    res = 2
            else:
                res = 0
            if res == 1:
                SendProgram(conn,filename)
            elif res == 2:
                savename = os.path.splitext(os.path.basename(filename))[0].upper()
                savename = savename.translate({ord(i): None for i in '"*+,/:;<=>?\[]|'})	#Remove MSX-DOS reserved characters
                if TransferFile(conn,filename, savename[:16]):
                    conn.SendTML(fok)
                else:
                    conn.SendTML(fabort)
                conn.SendTML('<KPROMPT t=RETURN>')
                conn.ReceiveKey()
            return
        # Text files
        elif ext in ['.SEQ','.MSEQ','.TXT']:
            if dialog:
                res = FileDialog(conn,os.path.basename(filename), os.path.getsize(filename), 'Sequential/Text File', 'view', save = save)
            else:
                res = 1+(1*save)
            if res == 1:
                title = 'Viewing text file' if ext == '.TXT' else ''
                SendText(conn,filename,title)
            elif res == 2:
                if ext == '.TXT':
                    if len(os.path.basename(filename)) > 16:
                        fn = os.path.splitext(os.path.basename(filename))
                        savename = (fn[0][:16-len(fn[1])]+fn[1]).upper()
                    else:
                        savename = os.path.basename(filename).upper()
                else:
                    savename = os.path.splitext(os.path.basename(filename))[0].upper()
                savename = savename.translate({ord(i): None for i in ':#$*?'})	#Remove CBMDOS reserved characters
                if TransferFile(conn,filename, savename[:16],True):
                    conn.SendTML(fok)
                else:
                    conn.SendTML(fabort)
                conn.SendTML('<KPROMPT t=RETURN>')
                conn.ReceiveKey()
            return
        # Images
        elif ext in ['.JPG','.GIF','.PNG']+im_extensions:    #,'.OCP','.KOA','.KLA','.ART','.DD','.DDL']:
            if type(SendBitmap(conn,filename,dialog,save)) != bool:
                conn.SendTML('<INKEYS><NUL><CURSOR>')
        elif ext == '.C':
            ...
        elif ext == '.PET':
            ...
        # Audio
        elif ext in ['.MP3','.WAV'] and not save:
            AA.PlayAudio(conn,filename,None,dialog)
        # TML script
        elif ext == '.TML': 
            with open(filename,'r') as slide:
                tml = slide.read()
                conn.SendTML(tml)
        # Default -> check if compressed archive -> download to disk
        else:
            arc = HandleArchives(conn,filename)
            if save:
                if dialog:
                    if arc == None:
                        res = FileDialog(conn,os.path.basename(filename), os.path.getsize(filename), 'Download file to disk', prompt='save to disk', save = False)
                    else:
                        res = FileDialog(conn,os.path.basename(filename), os.path.getsize(filename), arc[1], prompt='open', save = save)
                        if res == 1:
                            FileList(conn, os.path.basename(filename), 'Browsing Image/Archive', arc[0], None, SendFile, True, True)
                            res = 0
                        elif res == 2:
                            res = 1
                else:
                    res = 1
                if res == 1:
                    if len(os.path.basename(filename)) > 16:
                        fn = os.path.splitext(os.path.basename(filename))
                        savename = (fn[0][:16-len(fn[1])]+fn[1]).upper()
                    else:
                        savename = os.path.basename(filename).upper()
                    savename = savename.translate({ord(i): None for i in ':#$*?'})	#Remove CBMDOS reserved characters
                    if TransferFile(conn,filename,savename[:16]):
                        conn.SendTML(fok)
                    else:
                        conn.SendTML(fabort)
                    conn.SendTML('<KPROMPT t=RETURN>')
                    conn.ReceiveKey()

#################################################################################
# Sends program file into the client memory at the correct address in turbo mode
#################################################################################
# conn: Connection to send the file to
# filename: name+path of the file to be sent
#################################################################################
def SendProgram(conn:Connection,filename):
    # Verify .prg extension
    ext = os.path.splitext(filename)[1].upper()
    # if ext == '.PRG' and conn.encoder.check_fit(filename):
    if conn.encoder.check_fit(filename):
        _LOG('Memory transfer, filename: '+filename, id=conn.id,v=3)
        # Open file
        # archivo=open(filename,"rb")
        # Read load address
        # binario=archivo.read(2)
        # staddr = binario[0]+(binario[1]*256)
        staddr,bin = conn.encoder.get_exec(filename)
        if bin == None:
            return
        # Sync
        binaryout = b'\x00'
        # Enter command mode
        binaryout += b'\xFF'

        # Set the transfer pointer to load address (low:high)
        filesize = len(bin)     #os.path.getsize(filename) - 2
        endaddr = staddr + filesize
        binaryout += b'\x80'
        binaryout += staddr.to_bytes(2,'little')
        # if isinstance(binario[0],str) == False:
        #     binaryout += binario[0].to_bytes(1,'big')
        #     binaryout += binario[1].to_bytes(1,'big')
        # else:
        #     binaryout += binario[0]
        #     binaryout += binario[1]
        # Setup transfer pointer + program size (low:high)
        binaryout += b'\x82'
        binaryout += filesize.to_bytes(2,'little')
        _LOG('Load Address: '+bcolors.OKGREEN+str(staddr)+bcolors.ENDC, '/ Bytes: '+bcolors.OKGREEN+str(filesize)+bcolors.ENDC,id=conn.id,v=4)
        # Program data
        binaryout += bin    #archivo.read(filesize)

        # Exit command mode
        binaryout += b'\xFE'
        # Close file
        # archivo.close()
        # Send the data
        conn.Sendallbin(binaryout)
        if 'PET' in conn.mode:
            conn.SendTML(   f'<CLR><RVSOFF><ORANGE>Program file transferred to ${staddr:0{4}x}-${endaddr:0{4}x}<BR>'
                            f'To execute this program, <YELLOW><RVSON>L<RVSOFF><ORANGE>og off from<BR>'
                            f'this BBS, and exit Retroterm with <BR>RUN/STOP.<BR>'
                            f'Then use RUN or the correct SYS.<BR>'
                            f'Or <YELLOW><RVSON>C<RVSOFF><ORANGE>ontinue your session')
        elif 'MSX' in conn.mode:
            conn.SendTML(   f'<CLR><RVSOFF><PINK>Program file transferred to<BR>'
                            f'${staddr:0{4}x}-${endaddr:0{4}x}<BR>'
                            f'To execute this program, <YELLOW><RVSON>L<RVSOFF><PINK>og off'
                            f'from this BBS, and exit<BR>Retroterm with CTRL-U.<BR>'
                            f'Or <YELLOW><RVSON>C<RVSOFF><PINK>ontinue your session')

        if conn.ReceiveKey('cl') == 'l':
            conn.connected = False

#####################################################################################
# Transfer a file to be stored in media by the client
#####################################################################################
# conn: Connection to send the file to
# file: name+path of the file to be sent, or bytes
# savename: if defined, the filename sent to the client (mandatory if file is bytes)
#####################################################################################
def TransferFile(conn:Connection, file, savename = None, seq=False):
    if isinstance(file,str):
        if os.path.exists(file) == False:
            return False
        else:
            if conn.T56KVer > 0:
                with open(file,'rb') as fb:
                    data = fb.read()
            else:
                return xFileTransfer(conn,file,savename if savename != None else '')
    else:
        data = file
    if (conn.QueryFeature(TT.FILETR) < 0x80):
        basename = os.path.basename(file).upper()
        conn.Sendall(chr(TT.CMDON)+chr(TT.FILETR))
        if os.path.splitext(basename)[1] == '.SEQ' or seq:
            conn.Sendallbin(b'\x00')	# File type: SEQ
        else:
            conn.Sendallbin(b'\xF0')	# File type: PRG
        if savename != None:
            basename = savename
        else:
            basename = os.path.splitext(basename)[0]
        time.sleep(0.1)
        conn.Sendall(basename+chr(0))
        repeats = 0
        b_crc = Calculator(Configuration(width=16, polynomial=0x1021, init_value=0xffff, final_xor_value=0, reverse_input=False, reverse_output=False))
        if conn.ReceiveKey(b'\x81\x42\xAA') == b'\x81':
            for i in range(0,len(data),256):
                block = data[i:i+256]
                repeats = 0
                while repeats < 4:
                    conn.Sendallbin(len(block).to_bytes(2,'big')) # Endianess switched around because the terminal stores it back to forth
                    conn.Sendallbin(b_crc.checksum(block).to_bytes(2,'big')) # Endianess switched around because the terminal stores it back to forth
                    conn.Sendallbin(block)
                    rpl = conn.ReceiveKey(b'\x81\x42\xAA')
                    if  rpl == b'\x81':
                        break   # Block OK get next block
                    elif rpl == b'\xAA':
                        repeats += 1    # Block error, resend
                        _LOG('File download-Block CRC error',id=conn.id,v=3)
                    else:
                        _LOG('File download canceled',id=conn.id,v=3)
                        repeats = 5     # Disk error/User abort

                if repeats >= 4:
                    conn.Sendallbin(b'\x00\x00\x00\x00')    # Zero length block ends transfer
                    break
        else:
            repeats = 5
        conn.Sendallbin(b'\x00\x00\x00\x00\x00\x00')    # Make sure terminal exits transfer mode. Zero length block ends transfer + NULL name + Sequential file
        if repeats < 4:
            _LOG('TransferFile: Transfer complete',id=conn.id,v=3)
        elif repeats == 4:
            _LOG('TransferFile: Transfer aborted, too many errors',id=conn.id,v=2)
        else:
            _LOG('TransferFile: Client aborted the transfer',id=conn.id,v=2)
        return repeats < 4
    else:
        _LOG("TransferFile: Client doesn't suppport File Transfer command", id = conn.id, v=2)
        return False


##### X/YModem file transfer
def xFileTransfer(conn:Connection, file, savename = '', seq=False):

    tbytes = -1
    okbytes = 0

    def xread(size, timeout=3):
        timeout = 3 # Override timeout parameter
        data = b''
        conn.socket.setblocking(False)
        tmp = time.time()
        while ((time.time()-tmp) < timeout) and (len(data) < size):
            try:
                data += conn.socket.recv(1) 
            except socket.error as e:
                err = e.args[0]
                if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
                    time.sleep(0.5)
                    continue
                else:
                    pass
        conn.socket.setblocking(True)
        conn.socket.settimeout(conn.bbs.TOut)
        return data

    def xwrite(data, timeout=3):
        conn.Sendallbin(data)

    def xcallback(tindex, tname, tpackets, spackets):
        nonlocal tbytes, okbytes
        # print(f'Task Name: {tname}\nTask index: {tindex} - Total bytes: {tpackets} - OK bytes: {spackets}')
        if tbytes == -1:
            tbytes = tpackets
        okbytes = spackets

    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')

    conn.SendTML('<RVSOFF><CLR>Select protocol:<BR>[a] XModem-CRC<BR>[b] XModem-1K<BR>[c] YModem<BR>[<BACK>] Abort')
    k = conn.ReceiveKey('abc'+conn.encoder.decode(conn.encoder.back))
    if k == 'a':
        psize = 128
        proto = ProtocolType.XMODEM
    elif k == 'b':
        psize = 1024
        proto = ProtocolType.XMODEM
    elif k == 'c':
        psize = 128
        proto = ProtocolType.YMODEM
    else:
        return False
    conn.SendTML('<BR>Transferring file...<BR>')
    conn.Sendall(savename)
    # print(file,os.path.isfile(file))
    tmodem = ModemSocket(xread, xwrite, proto,packet_size=psize)
    result = tmodem.send([file], callback=xcallback)
    conn.SendTML('<BR><PAUSE n=1>')
    return tbytes - okbytes == 0


##########################################################################################################
# Generic file dialog
##########################################################################################################
# conn: Connection
# filename: File basename
# size:	File size, 0 to ignore
# filetype: File type, shown as title, if none, filename is used as title
# prompt: <return> option prompt text
# save: Show save option
##########################################################################################################
# Returns: 	0: Cancel
#			1: <RETURN> option
#			2: <S>ave option
##########################################################################################################
def FileDialog(conn:Connection,filename:str,size=0,filetype=None,prompt='transfer to memory',save=False):
    S.RenderDialog(conn,5+(size!=0)+(filetype!=None)+save,(filename if filetype == None else filetype))
    tml = '<AT x=0 y=2>'
    keys = conn.encoder.decode(conn.encoder.back)+conn.encoder.nl
    scwidth = conn.encoder.txt_geo[0]
    if filetype != None:
        tml += f'<RVSON> File: {H.crop(filename,scwidth-8,conn.encoder.ellipsis)}<BR>'
    if size > 0:
        tml += f'<RVSON> Size: {size}<BR><BR>'
    else:
        tml += '<BR>'
    if save:
        tml += '<RVSON> Press &lt;S&gt; to save to disk, or<BR><RVSON>'
        keys += 's'
    else:
        tml += '<RVSON> Press'
    tml += f' &lt;RETURN&gt; to {prompt[:scwidth-14]}<BR><RVSON> &lt;<BACK>&gt; to cancel'
    conn.SendTML(tml)
    rc = conn.ReceiveKey(keys)
    return keys.index(rc)

########################################################
# Sends a file directly without processing
########################################################
# conn: Connection to send the file to
# filename: name+path of the file to be sent
# wait: boolean, wait for RETURN after sending the file
########################################################
def SendRAWFile(conn:Connection,filename, wait=True):
    _LOG('Sending RAW file: ', filename, id=conn.id,v=3)

    with open(filename,'rb') as rf:
        binary=rf.read()
        conn.Sendallbin(binary)
    # Wait for the user to press RETURN
    if wait == True:
        conn.ReceiveKey()


#############################################################
# Sends a text or sequential file
#############################################################
def SendText(conn:Connection, filename, title='', lines=25):
    if title != '':
        S.RenderMenuTitle(conn, title)
        l = conn.encoder.txt_geo[1]-3
        conn.SendTML(f'<WINDOW top=3 bottom={l+2}>')
    else:
        l = lines
        conn.SendTML('<CLR>')

    if filename.endswith(('.txt','.TXT')):
        #Convert format text to the client's screen width and display with More
        with open(filename,"r") as tf:
            ot = tf.read()
        text = H.formatX(ot,conn.encoder.txt_geo[0])
    elif filename.endswith(('.seq','.SEQ')):
        with open(filename,"rb") as tf:
            ot = tf.read()
        tf.close()
        text = ot.decode('latin1')
    H.More(conn,text,l)

    if lines == 25:
        conn.SendTML('<WINDOW top=0 bottom=24>')
    return -1

####################################################
# Send C formatted C64 screens
#################################################### 
def SendCPetscii(conn:Connection,filename,pause=0):
    try:
        fi = open(filename,'r')
    except:
        return()
    text = fi.read()
    fi.close
    if text.find('upper') != -1:
        cs = '<UPPER>'
    else:
        cs = '<LOWER>'
    frames = text.split('unsigned char frame')
    for f in frames:
        if f == '':
            continue
        binary = b''
        fr = re.sub('(?:[0-9]{4})*\[\]={// border,bg,chars,colors\n','',f)
        fl = fr.split('\n')
        scc = fl[0].split(',')
        bo = int(scc[0]).to_bytes(1,'big') #border
        bg = int(scc[1]).to_bytes(1,'big') #background
        binary += b'\xff\xb2\x00\x90\x00'+bo+bg+b'\x81\x00\x82\xe8\x03'
        i = 0
        for line in fl[1:26]:
            for c in line.split(','):	#Screen codes
                if c.isnumeric():
                    binary += int(c).to_bytes(1,'big')
                    i += 1
        binary+= b'\x81\x20\x82\xe8\x03'
        i = 0
        for line in fl[26:52]:
            for c in line.split(','):	#Color RAM
                if c.isnumeric():
                    binary += int(c).to_bytes(1,'big')
                    i+=1
        binary+= b'\xfe'
        conn.Sendallbin(binary)
        conn.SendTML(cs)
        if pause > 0:
            time.sleep(pause)
        else:
            conn.ReceiveKey()
    conn.SendTML('<CURSOR>')
    return -1

##############################################
# Send .PET formatted C64 screens
##############################################
def SendPETPetscii(conn:Connection,filename):
    try:
        f = open(filename,'rb')
    except:
        return -1
    pet = f.read()
    bo = pet[2].to_bytes(1,'big')
    bg = pet[3].to_bytes(1,'big')
    binary = b'\xff\xb2\x00\x90\x00'+bo+bg+b'\x81\x00\x82\xe8\x03'
    binary += pet[5:1005]
    binary += b'\x81\x20\x82\xe8\x03'
    binary += pet[1005:]
    binary += b'\xfe'
    conn.Sendallbin(binary)
    if pet[4] == 1:
        conn.SendTML('<UPPER>')
    else:
        conn.SendTML('<LOWER>')
    return 0

###################################################
# Handle compressed archives and disk/tape images
###################################################
def HandleArchives(conn, filename):
    # Check if it is a ZIP compressed file
    if zipfile.is_zipfile(filename):
        try:
            return((zipfile.ZipFile(filename,'r'),'ZIP Archive'))
        except:
            return None
    # Check if it is a ZIP compressed file
    if lhafile.is_lhafile(filename):
        try:
            return((lhafile.Lhafile(filename,'r'),'LHA Archive'))
        except:
            return None
    ext = os.path.splitext(filename)[1].upper()
    if ext in ['.D64','.D71','.D81']:
        try:
            return((DiskImage(filename,'r'),'Commodore Disk Image'))
        except:
            return None
    return None
    ...

###########
# TML tags
###########
t_mono = {	'SENDRAW':(lambda c,file,wait:SendRAWFile(c,file,wait),[('c','_C'),('file',''),('wait','True')]),
            'SENDFILE':(lambda c,file,dialog,save:SendFile(c,file,dialog,save),[('c','_C'),('file',''),('dialog',False),('save',False)]),
            'SENDBITMAP':(lambda c,file,lines,display:SendBitmap(c,file,False,False,lines,display),[('c','_C'),('file',''),('lines',25),('display',True)]),
            }
