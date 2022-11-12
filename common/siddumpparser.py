#########################################################
#                   SIDDump Parser                      #
#########################################################

import subprocess
#import os.path

def SIDParser(filename,ptime,order = 0):

    V1f = [1,1] # Voice 1 Frequency
    V1p = [6,1] # Voice 1 Pulse Width
    V1c = [4,0] # Voice 1 Control
    V1e = [5,1] # Voice 1 Envelope

    V2f = [7,1] # Voice 2 Frequency
    V2p = [12,1] # Voice 2 Pulse Width
    V2c = [10,0] # Voice 2 Control
    V2e = [11,1] # Voice 2 Envelope

    V3f = [13,1] # Voice 3 Frequency
    V3p = [18,1] # Voice 3 Pulse Width
    V3c = [16,0] # Voice 3 Control
    V3e = [17,1] # Voice 3 Envelope

    Fco = [19,1] # Filter Cutoff Frequency
    Frs = [20,0] # Filter Resonance
    Vol = [21,0] # Filter and Volume Control


    #RTable = [[[V1f,0],[V1p,2],[V1c,4],[V1e,5] , [V2f,7],[V2p,9],[V2c,11],[V2e,12] , [V3f,14],[V3p,16],[V3c,18],[V3e,19] , [Fco,21],[Frs,23],[Vol,24]], #Default
    #          [[Frs,0],[Fco,1] , [V3f,3],[V3p,5],[V3c,7],[V3e,8] , [V2f,10],[V2p,12],[V2c,14],[V2e,15] , [V1f,17],[V1p,19],[V1c,21],[V1e,22] , [Vol,24]]] #MoN/Bjerregaard

    RTable = [[V1f,V1p,V1c,V1e , V2f,V2p,V2c,V2e , V3f,V3p,V3c,V3e , Fco,Frs,Vol], #Default
              [Frs,Fco , V3e,V3c,V3f,V3p , V2e,V2c,V2f,V2p , V1e,V1c,V1f,V1p , Vol]] #MoN/Bjerregaard

    FilterMode = {'Off':b'\x00', 'Low':b'\x10', 'Bnd':b'\x20', 'L+B':b'\x30', 'Hi':b'\x40', 'L+H':b'\x50', 'B+H':b'\x60', 'LBH':b'\x70'}

    # if os.path.isfile(filename[:-3]+'ssl') == True:
    #     tf = open(filename[:-3]+'ssl')
    #     tstr = tf.read()
    #     tf.close()
    #     ptime = str((ord(tstr[0])*60)+ord(tstr[1])) # Playtime for the 1st subtune
    # else:
    #     ptime = str(60*3)


    try:
        sidsub = subprocess.Popen('siddump '+filename+' -t'+str(ptime), shell=True, stdout=subprocess.PIPE)
    except:
        return(None)
    output = sidsub.stdout.read()
    outlines = output.split(b'\n')[7:-1] #Split in lines, skip first 7

    oldmode = 0 #Last filter mode
    oldvol = 0  #Last volume

    oldv1f = b'\x00\x00' #Last Voice 1 freq
    oldv2f = b'\x00\x00' #Last Voice 2 freq
    oldv3f = b'\x00\x00' #Last Voice 3 freq
    
    oldv1pw = b'\x00\x00' #Last Voice 1 pulse width
    oldv2pw = b'\x00\x00' #Last Voice 2 pulse width
    oldv3pw = b'\x00\x00' #Last Voice 3 pulse width

    oldv1adsr = b'\x00\x00' #Last Voice 1 ADSR
    oldv2adsr = b'\x00\x00' #Last Voice 2 ADSR
    oldv3adsr = b'\x00\x00' #Last Voice 3 ADSR

    oldff = b'\x00\x00' #Last filter cutoff freq

    dump = []

    for line in outlines:
        sidregs= b''
        rbitmap = 0
        rcount = 0
        temp = line.split()[1:-1]
        frame = [y for y in temp if y !=b'|']
        #Fill in registers
        offset = 0
        for ix,rp in enumerate(RTable[order]):
            rsection = rp[0]
            rbit = ix + offset  #rp[1]
            #<<<<<<<<<<<<<<<<<< Voices 1-3 Frequency
            if rsection == 1:
                if frame[1] != b'....':
                    tt = bytes.fromhex(frame[1].decode("utf-8"))
                    #if oldv1f[1] != tt[1]:
                    rbitmap |= 2**rbit
                    sidregs += bytes([tt[1]]) #Low Byte
                    rcount += 1
                    #if oldv1f[0] != tt[0]:
                    rbitmap |= 2**(rbit+1)
                    sidregs += bytes([tt[0]]) #High Byte
                    rcount += 1
                    oldv1f = tt
            if rsection == 7:
                if frame[7] != b'....':
                    tt = bytes.fromhex(frame[7].decode("utf-8"))
                    #if oldv2f[1] != tt[1]:
                    rbitmap |= 2**rbit
                    sidregs += bytes([tt[1]]) #Low Byte
                    rcount += 1
                    #if oldv2f[0] != tt[0]:
                    rbitmap |= 2**(rbit+1)
                    sidregs += bytes([tt[0]]) #High Byte
                    rcount += 1
                    oldv2f = tt
            if rsection == 13:
                if frame[13] != b'....':
                    tt = bytes.fromhex(frame[13].decode("utf-8"))
                    #if oldv3f[1] != tt[1]:
                    rbitmap |= 2**rbit
                    sidregs += bytes([tt[1]]) #Low Byte
                    rcount += 1
                    #if oldv3f[0] != tt[0]:
                    rbitmap |= 2**(rbit+1)
                    sidregs += bytes([tt[0]]) #High Byte
                    rcount += 1
                    oldv3f = tt
            #<<<<<<<<<<<<<<<<<< Voices 1-3 Pulse Width
            if rsection == 6:
                if frame[6] != b'...':
                    tt = bytes.fromhex('0'+frame[6].decode("utf-8"))
                    #if oldv1pw[1] != tt[1]:
                    rbitmap |= 2**rbit
                    sidregs += bytes([tt[1]]) #Low Byte
                    rcount += 1
                    #if oldv1pw[0] != tt[0]:
                    rbitmap |= 2**(rbit+1)
                    sidregs += bytes([tt[0]]) #High Byte
                    rcount += 1
                    oldv1pw = tt
            if rsection == 12:
                if frame[12] != b'...':
                    tt = bytes.fromhex('0'+frame[12].decode("utf-8"))
                    #if oldv2pw[1] != tt[1]:
                    rbitmap |= 2**rbit
                    sidregs += bytes([tt[1]]) #Low Byte
                    rcount += 1
                    #if oldv2pw[0] != tt[0]:
                    rbitmap |= 2**(rbit+1)
                    sidregs += bytes([tt[0]]) #High Byte
                    rcount += 1
                    oldv2pw = tt
            if rsection == 18:
                if frame[18] != b'...':
                    tt = bytes.fromhex('0'+frame[18].decode("utf-8"))
                    #if oldv3pw[1] != tt[1]:
                    rbitmap |= 2**rbit
                    sidregs += bytes([tt[1]]) #Low Byte
                    rcount += 1
                    #if oldv3pw[0] != tt[0]:
                    rbitmap |= 2**(rbit+1)
                    sidregs += bytes([tt[0]]) #High Byte
                    rcount += 1
                    oldv3pw = tt
            #<<<<<<<<<<<<<<< Voices 1-3 control
            if rsection == 4 or rsection == 10 or rsection == 16:
                if frame[rsection] != b'..':
                    rbitmap |= 2**rbit
                    sidregs += bytes.fromhex(frame[rsection].decode("utf-8"))
                    rcount += 1
            #<<<<<<<<<<<<<<< Voices 1-3 ADSR
            if rsection == 5:
                if frame[5] != b'....':
                    tt = bytes.fromhex(frame[5].decode("utf-8"))
                    #if oldv1adsr[0] != tt[0]:
                    rbitmap |= 2**rbit
                    sidregs += bytes([tt[0]]) #Attack/Decay
                    rcount += 1
                    #if oldv1adsr[1] != tt[1]:
                    rbitmap |= 2**(rbit+1)
                    sidregs += bytes([tt[1]]) #Sustain/Release
                    rcount += 1
                    oldv1adsr = tt
            if rsection == 11:
                if frame[11] != b'....':
                    tt = bytes.fromhex(frame[11].decode("utf-8"))
                    #if oldv2adsr[0] != tt[0]:
                    rbitmap |= 2**rbit
                    sidregs += bytes([tt[0]]) #Attack/Decay
                    rcount += 1
                    #if oldv2adsr[1] != tt[1]:
                    rbitmap |= 2**(rbit+1)
                    sidregs += bytes([tt[1]]) #Sustain/Release
                    rcount += 1
                    oldv2adsr = tt
            if rsection == 17:
                if frame[17] != b'....':
                    tt = bytes.fromhex(frame[17].decode("utf-8"))
                    #if oldv3adsr[0] != tt[0]:
                    rbitmap |= 2**rbit
                    sidregs += bytes([tt[0]]) #Attack/Decay
                    rcount += 1
                    #if oldv3adsr[1] != tt[1]:
                    rbitmap |= 2**(rbit+1)
                    sidregs += bytes([tt[1]]) #Sustain/Release
                    rcount += 1
                    oldv3adsr = tt
            #<<<<<<<<<<<<<<< Filter cutoff frequency
            if rsection == 19:
                if frame[19] != b'....':
                    tt = bytes.fromhex(frame[19].decode("utf-8"))
                    if oldff[1] != tt[1]:
                        rbitmap |= 2**rbit
                        sidregs += bytes([tt[1]]) # Low Nibble
                        rcount += 1
                    if oldff[0] != tt[0]:
                        rbitmap |= 2**(rbit+1)
                        sidregs += bytes([tt[0]]) # High Byte
                        rcount += 1
                    oldff = tt
            #<<<<<<<<<<<<<<< Filter resonance and control
            if rsection == 20:
                if frame[20] != b'..':
                    rbitmap |= 2**rbit
                    sidregs += bytes.fromhex(frame[20].decode("utf-8"))
                    rcount += 1
            #<<<<<<<<<<<<<<< Volume and filter mode
            if rsection == 21:
                if frame[21] != b'...' or frame[22] != b'.':
                    rbitmap |= 2**rbit
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
            offset += rp[1]
        
        rcount += 4 #Add the 4 bytes from the register bitmap
        dump.append([rcount.to_bytes(1,'little'),rbitmap.to_bytes(4,'big'),sidregs])
    return(dump)
#SIDParser('sids/leparc.sid')