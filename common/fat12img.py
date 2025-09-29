###########################################
# FAT12 Disk Image handling
# Based on dsktool.c
# https://github.com/nataliapc/MSX_devs
###########################################

#  MEDIA DESCRIPTOR TABLE
#  FAT-ID             F8   F9   FA   FB   FC   FD   FE   FF
#  Format code        891  892  881  882  491  492  481  482
#  Directory entries  112  112  112  112  64   112  64   112
#  Sectors / FAT      2    3    1    2    2    2    1    1
#  Sectors / track    9    9    8    8    9    9    8    8
#  Heads              1    2    1    2    1    2    1    2
#  Sectors / head     80   80   80   80   40   40   40   40
#  Sectors / cluster  2    2    2    2    1    2    1    2
#  Total sectors      720  1440 640  1280 360  720  320  640
#  Total clusters     360  720  320  640  360  360  320  320
#  Total Kbytes       360  720  320  640  180  360  160  320

################## Boot sector
class bootsector:
    dummy : bytes = b'\xeb\xfe\x90'     # 0x000 [3]  Dummy jump instruction (e.g. 0xEB 0xFE 0x90)
    oemname : str = ' '*8               # 0x003 [8]  OEM Name (padded with spaces 0x20)
    bytesPerSector : int = 0x0200       # 0x00B [2]  Bytes per logical sector in powers of two (e.g. 512 0x0200)
    sectorsPerCluster : int = 0x02      # 0x00D [1]  Logical sectors per cluster (e.g. 2 0x02)
    reservedSectors : int = 0x0001      # 0x00E [2]  Count of reserved logical sectors (e.g. 1 0x0001)
    numberOfFATs : int = 0x02           # 0x010 [1]  Number of File Allocation Tables (e.g. 2 0x02)
    maxDirectoryEntries : int = 0x0070	# 0x011 [2]  Maximum number of FAT12 or FAT16 root directory entries (e.g. 112 0x0070)
    totalSectors : int = 0x05a0         # 0x013 [2]  Total logical sectors (e.g. 1440 0x05a0)
    mediaDescriptor : int = 0xf9        # 0x015 [1]  Media descriptor: 0xf9:3.5"720Kb | 0xf8:3.5"360Kb (see previous table)
    sectorsPerFAT : int = 0x0003        # 0x016 [2]  Logical sectors per FAT (e.g. 3 0x0003)
    sectorsPerTrack : int = 0x0009      # 0x018 [2]  Physical sectors per track for disks with CHS geometry (e.g. 9 0x0009)
    numberOfHeads : int = 0x0002        # 0x01A [2]  Number of heads (e.g. 2 0x0002)
    hiddenSectors : int = 0x0000        # 0x01C [2]  Count of hidden sectors preceding the partition that contains this FAT volume (e.g. 0 0x0000)
    codeEntryPoint : int = 0x0000		# 0x01E [2]  MSX-DOS 1 code entry point for Z80 processors into MSX boot code. This is where MSX-DOS 1 machines jump to when passing control to the boot sector.
    bootCode : bytes = bytes(482)       # 0x020 [-]  This location overlaps with BPB formats since DOS 3.2 or the x86 compatible boot sector code of IBM PC compatible boot sectors and will lead to a crash on the MSX machine unless special precautions have been taken such as catching the CPU in a tight loop here (opstring 0x18 0xFE for JR 0x01E).

    def __init__(self, data):
        if type(data) == bytes:
            if len(data) == 512:
                self.dummy = data[0:3]
                self.oemname = data[3:11].decode('cp437')
                self.bytesPerSector = int.from_bytes(data[11:13],'little')
                self.sectorsPerCluster = data[13]
                self.reservedSectors = int.from_bytes(data[14:16],'little')
                self.numberOfFATs = data[16]
                self.maxDirectoryEntries = int.from_bytes(data[17:19],'little')
                self.totalSectors = int.from_bytes(data[19:21],'little')
                self.mediaDescriptor = data[21]
                self.sectorsPerFAT = int.from_bytes(data[22:24],'little')
                self.sectorsPerTrack = int.from_bytes(data[24:26],'little')
                self.numberOfHeads = int.from_bytes(data[26:28],'little')
                self.hiddenSectors = int.from_bytes(data[28:30],'little')
                self.codeEntryPoint = int.from_bytes(data[30:32],'little')
                self.bootCode = data[32:]

################## Directory entry
class direntry:
    name : str = ''                     # 0x000 [8]  Short file name (padded with spaces). First char '0xE5' for deleted files. "σ"
    ext : str = ''                      # 0x008 [3]  Short file extension (padded with spaces)
    attr : int = 0                      # 0x00B [1]  File Attributes. Mask: 0x01:ReadOnly | 0x02:Hidden | 0x04:System | 0x08:Volume | 0x10:Directory | 0x20:Archive
    unused1 : str = ' '                 # 0x00C [1]  MSX-DOS 2: For a deleted file, the original first character of the filename
    unused2 : bytes = b'\x00'           # 0x00D [1]
    ctime : int = 0x0000                # 0x00E [2]  Create time: #0-4:Seconds/2 #5-10:Minuts #11-15:Hours
    cdate : int = 0x0000                # 0x010 [2]  Create date: #0-4:Day #5-8:Month #9-15:Year(0=1980)
    unused3 : bytes = '\x00\x00'        # 0x012 [2]
    unused4 : bytes = '\x00\x00'        # 0x014 [2]
    mtime : int = 0x0000                # 0x016 [2]  Last modified time: #0-4:Seconds/2 #5-10:Minuts #11-15:Hours
    mdate : int = 0x0000                # 0x018 [2]  Last modified date: #0-4:Day #5-8:Month #9-15:Year(0=1980)
    cluini : int = 0x0000               # 0x01A [2]  Initial cluster for this file
    fsize : int = 0x00000000            # 0x01C [4]  File size in bytes

    def __init__(self,entry):
        if type(entry) == bytes:
            if len(entry) == 32:
                if int.from_bytes(entry[:8],'little') != 0:
                    self.name = entry[:8].decode('cp437')
                    self.name = self.name.replace(' ','')
                if int.from_bytes(entry[:8],'little') != 0:
                    self.ext = entry[8:11].decode('cp437')
                    self.ext = self.ext.replace(' ','')
                self.attr = entry[11]
                self.unused1 = chr(entry[12])
                self.unused2 = entry[13]
                self.ctime = int.from_bytes(entry[14:16],'little')
                self.cdate = int.from_bytes(entry[16:18],'little')
                self.unused3 = entry[18:20]
                self.unused4 = entry[20:22]
                self.mtime = int.from_bytes(entry[22:24],'little')
                self.mdate = int.from_bytes(entry[24:26],'little')
                self.cluini = int.from_bytes(entry[26:28],'little')
                self.fsize = int.from_bytes(entry[28:],'little')
        

################## File info
class fileinfo:
    name : str = ''
    size : int = 0
    hour : int = 0
    min : int = 0
    sec : int = 0
    day : int = 0
    month : int = 0
    year : int = 0
    first : int = 0
    pos : int = 0       # Position in the directory list
    attr : int = 0

    def __init__(self, dir_entry:direntry, pos = 0):
        if dir_entry.name != '' and dir_entry.attr & 0x08 == 0:
            self.name = dir_entry.name + (f'.{dir_entry.ext}' if dir_entry.ext != '' else '')
            self.size = dir_entry.fsize
            self.attr = dir_entry.attr
            self.hour = dir_entry.mtime >> 11
            self.min = (dir_entry.mtime >> 5) & 0b111111
            self.sec = (dir_entry.mtime & 0b11111) << 1
            self.day = dir_entry.mdate & 0b11111
            self.month = (dir_entry.mdate >>5) & 0b1111
            self.year = (dir_entry.mdate >> 9) + 1980
            self.first = dir_entry.cluini
            self.pos = pos
            self.attr = dir_entry.attr
        else:
            pass

    def __repr__(self):
        if self.is_dir():
            res = f'[ {self.name} ]'
        else:
            res = f'Name: {self.name:<12} | size: {self.size:>10} bytes |\
 {self.day:02d}/{self.month:02d}/{self.year} |\
 {self.hour:02d}:{self.min:02d}:{self.sec:02d} |\
 {"R" if self.attr & 0x01 != 0 else "-"}{"H" if self.attr & 0x02 != 0 else "-"}{"S" if self.attr & 0x04 != 0 else "-"}{"V" if self.attr & 0x08 != 0 else "-"}{"A" if self.attr & 0x20 != 0 else "-"}'
        return res

    def is_readonly(self):
        return (self.attr & 0x01) != 0

    def is_hidden(self):
        return (self.attr & 0x02) != 0
    
    def is_volume(self):
        return (self.attr & 0x08) != 0

    def is_dir(self):
        return (self.attr & 0x10) != 0

    def is_archived(self):
        return (self.attr & 0x20) != 0
    


################## Main class
class FAT12Image:
    rawdata = None
    boot_sector = None
    directory = []
    current_dir = '..'
    file_info = []
    FAT = []
    disk_size = 0
    bytes_per_cluster = 0
    data_offset = 0

    def __init__(self, filename):
        try:
            with open(filename,'rb') as fimg:
                self.rawdata = fimg.read()
            self.boot_sector = bootsector(self.rawdata[:512])
            bps = self.boot_sector.bytesPerSector
            self.disk_size = bps * self.boot_sector.totalSectors
            self.bytes_per_cluster = bps * self.boot_sector.sectorsPerCluster
            rootsectors = ((self.boot_sector.maxDirectoryEntries * 32)+(bps-1) )// bps
            self.data_offset = (self.boot_sector.reservedSectors + (self.boot_sector.numberOfFATs * self.boot_sector.sectorsPerFAT) + rootsectors) * bps
            pos = 0
            self.chdir()    # Read root directory
            # Index FAT
            for i in range(512,512+(self.boot_sector.sectorsPerFAT*bps),3):
                entry = self.rawdata[i:i+3]
                self.FAT.append(entry[0]+((entry[1] & 0x0f)<<8))
                self.FAT.append((entry[1]>>4)+(entry[2]<<4))
        except:
            print("ERROR")
            pass

    def chdir(self,directory = '..'):
        de = -1
        for fi in self.file_info:
            if fi.name == directory:
                if fi.first == 0:
                    directory = '..'
                    de = fi.pos
        if de == -1 and directory != '..':
            return False
        if directory == '..':
            bps = self.boot_sector.bytesPerSector
            dirstart = (self.boot_sector.reservedSectors + (self.boot_sector.numberOfFATs * self.boot_sector.sectorsPerFAT)) * bps
            dirsectors = ((self.boot_sector.maxDirectoryEntries * 32)+(bps-1) )// bps
            dirend = (self.boot_sector.reservedSectors + (self.boot_sector.numberOfFATs * self.boot_sector.sectorsPerFAT) + dirsectors) * bps
            dirdata = self.rawdata[dirstart:dirend]
            self.current_dir = '..'
        else:
            dirdata = self.read(directory)
            if dirdata == b'':
                return False
        self.directory = []
        self.file_info = []
        pos = 0
        for i in range(0,len(dirdata),32):
            dir_e = direntry(dirdata[i:i+32])
            finfo = fileinfo(dir_e,pos)
            if finfo.name == '':
                break
            self.file_info.append(finfo)
            self.directory.append(dir_e)
            pos += 1
        return True


    def read(self,filename):
        finfo = None
        for fi in self.file_info:
            if fi.name == filename:
                finfo = fi
                break
        if finfo == None:
            return b''
        size = finfo.size
        log_cluster = finfo.first
        data = b''
        cluster_size = self.bytes_per_cluster
        while True:
            cluster_offs = self.data_offset + (cluster_size * (log_cluster-2))
            print(log_cluster, cluster_offs)
            data = data + self.rawdata[cluster_offs:cluster_offs+cluster_size]
            log_cluster = self.FAT[log_cluster]
            if log_cluster == 0 or ( 0xff0 <= log_cluster <= 0xff7):
                break
            elif log_cluster >= 0xff8:
                data = data[:size]
                break
        return data