#########################################################
#                   SIDDump Parser                      #
#########################################################

import subprocess
#import os.path

def SIDParser(filename,ptime):

    FilterMode = {'Off':b'\x00', 'Low':b'\x10', 'Bnd':b'\x20', 'L+B':b'\x30', 'Hi':b'\x40', 'L+H':b'\x50', 'B+H':b'\x60', 'LBH':b'\x70'}

    # if os.path.isfile(filename[:-3]+'ssl') == True:
    #     tf = open(filename[:-3]+'ssl')
    #     tstr = tf.read()
    #     tf.close()
    #     ptime = str((ord(tstr[0])*60)+ord(tstr[1])) # Playtime for the 1st subtune
    # else:
    #     ptime = str(60*3)

    # print(ptime)

    try:
        sidsub = subprocess.Popen('siddump '+filename+' -t'+str(ptime), shell=True, stdout=subprocess.PIPE)
    except:
        return(None)
    output = sidsub.stdout.read()
    outlines = output.split(b'\n')[7:-1] #Split in lines, skip first 7

    oldmode = 0 #Modo filtro previo
    oldvol = 0  #Volumen previo

    dump = []

    for line in outlines:
        sidregs= b''
        rbitmap = 0
        rcount = 0
        temp = line.split()[1:-1]
        frame = [y for y in temp if y !=b'|']
        #print(frame)
        #Fill in registers
        #<<<<<<<<<<<<<<<Voz 1 - Frecuencia
        if frame[1] != b'....':
            rbitmap |= 2**0 | 2**1  
            tt = bytes.fromhex(frame[1].decode("utf-8"))
            sidregs += bytes([tt[1]]) #Byte bajo
            rcount += 1
            sidregs += bytes([tt[0]]) #Byte alto
            rcount += 1
        #<<<<<<<<<<<<<<<Voz 1 - Ancho de pulso
        if frame[6] != b'...':
            rbitmap |= 2**2 | 2**3
            tt = bytes.fromhex('0'+frame[6].decode("utf-8"))
            sidregs += bytes([tt[1]]) #Byte bajo
            rcount += 1
            sidregs += bytes([tt[0]]) #Byte alto
            rcount += 1
        #<<<<<<<<<<<<<<<Voz 1 - Control
        if frame[4] != b'..':
            rbitmap |= 2**4

            sidregs += bytes.fromhex(frame[4].decode("utf-8"))
            rcount += 1
        #<<<<<<<<<<<<<<<Voz 1 - ADSR
        if frame[5] != b'....':
            rbitmap |= 2**5 | 2**6
            tt = bytes.fromhex(frame[5].decode("utf-8"))
            sidregs += bytes([tt[0]]) #Attack/Decay
            rcount += 1
            sidregs += bytes([tt[1]]) #Sustain/Release
            rcount += 1

        #<<<<<<<<<<<<<<<Voz 2 - Frecuencia
        if frame[7] != b'....':
            rbitmap |= 2**7 | 2**8  
            tt = bytes.fromhex(frame[7].decode("utf-8"))
            sidregs += bytes([tt[1]]) #Byte bajo
            rcount += 1
            sidregs += bytes([tt[0]]) #Byte alto
            rcount += 1
        #<<<<<<<<<<<<<<<Voz 2 - Ancho de pulso
        if frame[12] != b'...':
            rbitmap |= 2**9 | 2**10
            tt = bytes.fromhex('0'+frame[12].decode("utf-8"))
            sidregs += bytes([tt[1]]) #Byte bajo
            rcount += 1
            sidregs += bytes([tt[0]]) #Byte alto
            rcount += 1
        #<<<<<<<<<<<<<<<Voz 2 - Control
        if frame[10] != b'..':
            rbitmap |= 2**11
            sidregs += bytes.fromhex(frame[10].decode("utf-8"))
            rcount += 1
        #<<<<<<<<<<<<<<<Voz 2 - ADSR
        if frame[11] != b'....':
            rbitmap |= 2**12 | 2**13
            tt = bytes.fromhex(frame[11].decode("utf-8"))
            sidregs += bytes([tt[0]]) #Attack/Decay
            rcount += 1
            sidregs += bytes([tt[1]]) #Sustain/Release
            rcount += 1

        #<<<<<<<<<<<<<<<Voz 3 - Frecuencia
        if frame[13] != b'....':
            rbitmap |= 2**14 | 2**15  
            tt = bytes.fromhex(frame[13].decode("utf-8"))
            sidregs += bytes([tt[1]]) #Byte bajo
            rcount += 1
            sidregs += bytes([tt[0]]) #Byte alto
            rcount += 1
        #<<<<<<<<<<<<<<<Voz 3 - Ancho de pulso
        if frame[18] != b'...':
            rbitmap |= 2**16 | 2**17
            tt = bytes.fromhex('0'+frame[18].decode("utf-8"))
            sidregs += bytes([tt[1]]) #Byte bajo
            rcount += 1
            sidregs += bytes([tt[0]]) #Byte alto
            rcount += 1
        #<<<<<<<<<<<<<<<Voz 3 - Control
        if frame[16] != b'..':
            rbitmap |= 2**18
            sidregs += bytes.fromhex(frame[16].decode("utf-8"))
            rcount += 1
        #<<<<<<<<<<<<<<<Voz 3 - ADSR
        if frame[17] != b'....':
            rbitmap |= 2**19 | 2**20
            tt = bytes.fromhex(frame[17].decode("utf-8"))
            sidregs += bytes([tt[0]]) #Attack/Decay
            rcount += 1
            sidregs += bytes([tt[1]]) #Sustain/Release
            rcount += 1

        #<<<<<<<<<<<<<<< Frecuencia de corte del filtro
        if frame[19] != b'....':
            rbitmap |= 2**21 | 2**22
            tt = bytes.fromhex(frame[19].decode("utf-8"))
            sidregs += bytes([tt[1]]) # Nibble bajo
            rcount += 1
            sidregs += bytes([tt[0]]) # Byte alto
            rcount += 1
        #<<<<<<<<<<<<<<< Resonancia y control del filtro
        if frame[20] != b'..':
            rbitmap |= 2**23
            sidregs += bytes.fromhex(frame[20].decode("utf-8"))
            rcount += 1
        #<<<<<<<<<<<<<<< Modo filtro y volumen
        if frame[21] != b'...' or frame[22] != b'.':
            rbitmap |= 2**24
            if frame[21] != b'...':
                mode = FilterMode[frame[21].decode("utf-8")]
            else:
                mode = oldmode
            if frame[22] != b'.':
                vol = bytes.fromhex('0'+frame[22].decode("utf-8"))
            else:
                vol = oldvol
            sidregs += bytes([ord(mode) | ord(vol)])
            rcount += 1
            oldmode = mode
            oldvol = vol
        
        rcount += 4 #Add the 4 bytes from the register bitmap
        #print(format(rcount,'02d'), format(rbitmap,'025b'), sidregs)
        dump.append([rcount.to_bytes(1,'little'),rbitmap.to_bytes(4,'big'),sidregs])
    #print(dump)
    #print(len(dump))
    return(dump)

#SIDParser('sids/leparc.sid')