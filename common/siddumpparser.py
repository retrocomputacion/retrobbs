#########################################################
#                   SIDDump Parser                      #
#########################################################

import subprocess
from shutil import which
from enum import IntEnum, auto
import os
import sys
from common import cpu65 as c65
from common.bbsdebug import _LOG
# from common import ymparse as YM      # Moved to the end of the file to bypass 'circular' imports

# compute's sidplayer driver, taken from sidplay2/w
mus_driver = \
    b"\x00\xe0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" \
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" \
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" \
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" \
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" \
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" \
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" \
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" \
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" \
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" \
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" \
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" \
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" \
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" \
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" \
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" \
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" \
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" \
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" \
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" \
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" \
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" \
    b"\x00\x61\xe1\x60\x01\x02\x04\x00\x07\x0e\x02\x02\xfe\x02\x02\xfe" \
    b"\xfe\x00\x01\x00\xff\x00\x02\x04\x05\x07\x09\x0b\x1e\x18\x8b\x7e" \
    b"\xfa\x06\xac\xf3\xe6\x8f\xf8\x2e\x86\x8e\x96\x9f\xa8\xb3\xbd\xc8" \
    b"\xd4\xe1\xee\xfd\x8c\x78\x64\x50\x3c\x28\x14\x00\x00\x02\x03\x05" \
    b"\x07\x08\x0a\x0c\x0d\x0f\x11\x12\x00\xe0\x00\x05\x0a\x0f\xf9\x00" \
    b"\xf5\x00\x00\x00\x10\x00\x00\x20\x00\x00\x30\x00\x00\x40\x00\x00" \
    b"\x50\x00\x00\x60\x00\x00\x70\x00\x00\x80\x00\x00\x90\x00\x00\xa0" \
    b"\x00\xa9\x00\x8d\x00\xe0\xa2\x95\xa0\x42\xad\xa6\x02\xf0\x04\xa2" \
    b"\x25\xa0\x40\x8e\x5b\xe1\x8c\x5c\xe1\xea\xea\xea\xea\xea\xea\xea" \
    b"\xea\xea\xea\xea\xea\xea\xea\xea\xea\xea\xea\xea\xea\xea\xea\xea" \
    b"\xea\x60\xa9\x00\x8d\x00\xe0\x86\x61\x84\x62\xa0\xbc\x99\x00\xe0" \
    b"\x88\xd0\xfa\xa0\x72\x99\xbc\xe0\x88\xd0\xfa\x8d\x15\xd4\x8d\x16" \
    b"\xd4\xa9\x08\x8d\x25\xe0\x8d\x17\xd4\x8d\x26\xe0\x8d\x18\xd4\xa9" \
    b"\x90\x8d\x27\xe0\xa9\x60\x8d\x28\xe0\xa9\x0c\x8d\x29\xe0\xad\x5b" \
    b"\xe1\x8d\x2d\xe0\xad\x5c\xe1\x8d\x2e\xe0\xa9\xff\x8d\xcc\xe0\xa9" \
    b"\xd4\x85\x64\xa2\x02\xa9\xff\x9d\x0b\xe0\xa9\x01\x9d\x30\xe0\x9d" \
    b"\x2a\xe0\x8a\x9d\x33\xe0\x9d\xae\xe0\xa9\x04\x9d\x39\xe0\xbd\xa8" \
    b"\xe1\x9d\xba\xe0\xa9\x5b\x9d\x7e\xe0\xbd\x65\xe1\x85\x63\xa9\x00" \
    b"\xa8\x91\x63\xc8\x91\x63\xc8\x91\x63\xa9\x08\x9d\x17\xe0\x9d\x9c" \
    b"\xe0\xc8\x91\x63\xc8\x91\x63\xa9\x40\x9d\x1a\xe0\x91\x63\xa9\x20" \
    b"\x9d\x1d\xe0\xc8\x91\x63\xa9\xf5\x9d\x20\xe0\xc8\x91\x63\xca\x10" \
    b"\xa4\x8a\xa2\x17\x9d\x3e\xe1\xca\x10\xfa\xa5\x61\x18\x69\x06\x85" \
    b"\x63\xa9\x00\xaa\xa8\x65\x62\x85\x64\x9d\xab\xe0\x9d\xb4\xe0\xa5" \
    b"\x63\x9d\xa8\xe0\x9d\xb1\xe0\x18\x71\x61\x85\x63\xa5\x64\xc8\x71" \
    b"\x61\xc8\xe8\xe0\x03\xd0\xe0\xa6\x63\xa8\x60\xa9\x00\x8d\x04\xd4" \
    b"\x8d\x0b\xd4\x8d\x12\xd4\x8d\x01\xd4\x8d\x08\xd4\x8d\x0f\xd4\xa9" \
    b"\x08\x8d\x17\xd4\xad\x5b\xe1\x8d\x04\xdc\xad\x5c\xe1\x8d\x05\xdc" \
    b"\x60\xea\xea\xea\xea\xea\xea\xea\xea\xea\xea\xea\xea\xea\xea\x60" \
    b"\xa9\x08\x8d\x00\xe0\x6c\x5d\xe1\xea\xea\xea\xad\x00\xe0\x30\xf0" \
    b"\x09\x80\xa8\x29\x07\xf0\xee\xd8\x8c\x00\xe0\xea\xa5\xfb\x8d\x56" \
    b"\xe1\xa5\xfc\x8d\x57\xe1\xa5\xfd\x8d\x58\xe1\xa5\xfe\x8d\x59\xe1" \
    b"\xa5\xff\x8d\x5a\xe1\xad\x23\xe0\x18\x6d\xd9\xe0\x48\x29\x07\xa8" \
    b"\xad\xdc\xe0\x69\x00\x85\xff\x68\x46\xff\x6a\x46\xff\x6a\x46\xff" \
    b"\x6a\x18\x6d\x24\xe0\x8c\x15\xd4\x8d\x16\xd4\xad\x25\xe0\x8d\x17" \
    b"\xd4\xad\x26\xe0\x8d\x18\xd4\xa9\xd4\x85\xfc\xa2\x00\xad\x00\xe0" \
    b"\x3d\x62\xe1\xf0\x51\xbd\x65\xe1\x85\xfb\xbd\x0e\xe0\x18\x7d\x51" \
    b"\xe0\xa8\xbd\x11\xe0\x7d\x54\xe0\x48\x98\x18\x7d\xcd\xe0\xa0\x00" \
    b"\x91\xfb\x68\x7d\xd0\xe0\xc8\x91\xfb\xbd\x14\xe0\x18\x7d\x69\xe0" \
    b"\x85\xff\xbd\x17\xe0\x7d\x6c\xe0\x48\xa5\xff\x18\x7d\xd3\xe0\xc8" \
    b"\x91\xfb\x68\x7d\xd6\xe0\xc8\x91\xfb\xbd\x1d\xe0\xc8\xc8\x91\xfb" \
    b"\xbd\x20\xe0\xc8\x91\xfb\xe8\xe0\x03\xd0\xa2\xac\x1a\xe0\xae\x1b" \
    b"\xe0\xad\x1c\xe0\x8c\x04\xd4\x8e\x0b\xd4\x8d\x12\xd4\xae\x2d\xe0" \
    b"\xac\x2e\xe0\x8e\x04\xdc\x8c\x05\xdc\xad\x1b\xd4\x8d\xbe\xe0\xad" \
    b"\x1c\xd4\x8d\xbf\xe0\xa2\x00\xad\x00\xe0\x3d\x62\xe1\xf0\x10\x8e" \
    b"\x2f\xe0\x20\x36\xe5\xad\x00\xe0\x29\x78\xf0\x03\x4c\x0c\xe5\xe8" \
    b"\xe0\x03\xd0\xe3\xad\xc9\xe0\xd0\x52\xad\xca\xe0\x0d\xcb\xe0\xf0" \
    b"\x78\xad\xdf\xe0\xd0\x28\xad\xca\xe0\xf0\x28\x18\x6d\xbd\xe0\xb0" \
    b"\x07\xcd\xcc\xe0\x90\x60\xf0\x5e\xa9\x00\x8d\xdf\xe0\xad\xcb\xe0" \
    b"\xf0\x54\xee\xdf\xe0\xad\xbd\xe0\xed\xcb\xe0\x4c\xb4\xe4\xad\xcb" \
    b"\xe0\xf0\xd3\xad\xbd\xe0\x38\xed\xcb\xe0\xb0\x3a\xa9\x00\x8d\xdf" \
    b"\xe0\xad\xca\xe0\xd0\x30\xee\xdf\xe0\xd0\x28\xce\xe0\xe0\xd0\x29" \
    b"\xad\xdf\xe0\xd0\x11\xee\xdf\xe0\xad\xcb\xe0\xd0\x02\xa9\x20\x8d" \
    b"\xe0\xe0\xa9\x00\xf0\x10\xce\xdf\xe0\xad\xca\xe0\xd0\x02\xa9\x20" \
    b"\x8d\xe0\xe0\xad\xcc\xe0\x8d\xbd\xe0\xa2\x00\xbd\xc3\xe0\xf0\x44" \
    b"\xa9\x00\x85\xff\xbc\xc0\xe0\xb9\xbd\xe0\xbc\xc6\xe0\xf0\x0e\x30" \
    b"\x08\x0a\x26\xff\x88\xd0\xfa\xf0\x04\x4a\xc8\xd0\xfc\xbc\xc3\xe0" \
    b"\x88\xd0\x0b\x9d\xcd\xe0\xa5\xff\x9d\xd0\xe0\x4c\x02\xe5\x88\xd0" \
    b"\x0b\x9d\xd3\xe0\xa5\xff\x9d\xd6\xe0\x4c\x02\xe5\x8d\xd9\xe0\xa5" \
    b"\xff\x8d\xdc\xe0\xe8\xe0\x03\xd0\xb2\xad\x00\xe0\x29\x7f\x8d\x00" \
    b"\xe0\xad\x56\xe1\x85\xfb\xad\x57\xe1\x85\xfc\xad\x58\xe1\x85\xfd" \
    b"\xad\x59\xe1\x85\xfe\xad\x5a\xe1\x85\xff\x6c\x5d\xe1\xbd\x60\xe0" \
    b"\xd0\x03\x4c\x9f\xe6\x4c\xba\xe5\xde\x30\xe0\xd0\x03\x4c\xa0\xe6" \
    b"\xbd\x36\xe0\x30\xe8\xd0\x1a\xbd\x3f\xe0\xf0\x05\xde\x3f\xe0\xd0" \
    b"\x10\xbd\x39\xe0\xdd\x30\xe0\x90\x08\xbd\x1a\xe0\x29\xfe\x9d\x1a" \
    b"\xe0\xbd\x42\xe0\xf0\x56\x0a\xbd\x0e\xe0\xb0\x1d\x7d\x45\xe0\x9d" \
    b"\x0e\xe0\xa8\xbd\x11\xe0\x7d\x48\xe0\x9d\x11\xe0\x48\x98\xdd\x8d" \
    b"\xe0\x68\xfd\x90\xe0\xb0\x1f\x90\x2e\xfd\x45\xe0\x9d\x0e\xe0\xbd" \
    b"\x11\xe0\xfd\x48\xe0\x9d\x11\xe0\xbd\x8d\xe0\xdd\x0e\xe0\xbd\x90" \
    b"\xe0\xfd\x11\xe0\x90\x11\xbd\x8d\xe0\x9d\x0e\xe0\xbd\x90\xe0\x9d" \
    b"\x11\xe0\xa9\x00\x9d\x42\xe0\xbd\x60\xe0\xf0\x55\xbd\x4b\xe0\xf0" \
    b"\x4b\xa0\x00\xde\x4e\xe0\xd0\x31\xbd\x51\xe0\x1d\x54\xe0\xd0\x1b" \
    b"\xbd\x5d\xe0\x9d\x57\xe0\x9d\x4e\xe0\xbd\x4b\xe0\x0a\xbd\x5a\xe0" \
    b"\x90\x04\x49\xff\x69\x00\x9d\x4b\xe0\xd0\x10\xbd\x57\xe0\x9d\x4e" \
    b"\xe0\x98\x38\xfd\x4b\xe0\x9d\x4b\xe0\xc9\x00\x10\x01\x88\x18\x7d" \
    b"\x51\xe0\x9d\x51\xe0\x98\x7d\x54\xe0\x9d\x54\xe0\xbd\x36\xe0\x30" \
    b"\x15\xbd\x93\xe0\xf0\x10\x18\x7d\x14\xe0\x9d\x14\xe0\xbd\x96\xe0" \
    b"\x7d\x17\xe0\x9d\x17\xe0\xbd\x63\xe0\xf0\x4b\xa0\x00\xde\x66\xe0" \
    b"\xd0\x31\xbd\x69\xe0\x1d\x6c\xe0\xd0\x1b\xbd\x72\xe0\x9d\x6f\xe0" \
    b"\x9d\x66\xe0\xbd\x63\xe0\x0a\xbd\x75\xe0\x90\x04\x49\xff\x69\x00" \
    b"\x9d\x63\xe0\xd0\x10\xbd\x6f\xe0\x9d\x66\xe0\x98\x38\xfd\x63\xe0" \
    b"\x9d\x63\xe0\xc9\x00\x10\x01\x88\x18\x7d\x69\xe0\x9d\x69\xe0\x98" \
    b"\x7d\x6c\xe0\x9d\x6c\xe0\xbd\x36\xe0\x10\x03\x4c\x9f\xe6\xa0\x00" \
    b"\xbd\xa2\xe0\xf0\x1c\x10\x01\xc8\x18\x6d\x23\xe0\x48\x29\x07\x8d" \
    b"\x23\xe0\x68\x6a\x4a\x4a\x18\x79\xa6\xe1\x18\x6d\x24\xe0\x8d\x24" \
    b"\xe0\x60\xbd\xa8\xe0\x85\xfd\xbd\xab\xe0\x85\xfe\xd0\x04\x60\x20" \
    b"\x98\xe8\xad\x00\xe0\x3d\x62\xe1\xf0\xf4\xa0\x00\xb1\xfd\x85\xff" \
    b"\xc8\xb1\xfd\xa8\xa5\xfd\x18\x69\x02\x85\xfd\x9d\xa8\xe0\xa5\xfe" \
    b"\x69\x00\x85\xfe\x9d\xab\xe0\xa5\xff\x29\x03\xd0\xd2\xbd\x8d\xe0" \
    b"\x9d\x0e\xe0\xbd\x90\xe0\x9d\x11\xe0\xa5\xff\x9d\x05\xe0\x98\x9d" \
    b"\x02\xe0\x29\x07\xa8\xb9\x67\xe1\x8d\x6f\xe1\xbd\x02\xe0\x29\x38" \
    b"\x4a\x4a\x4a\x7d\x81\xe0\x85\xfd\xbd\x02\xe0\x29\xc0\x0a\x2a\x2a" \
    b"\xa8\xb9\x6f\xe1\x85\xfe\xbd\x02\xe0\x29\x07\xf0\x62\xa8\xb9\x72" \
    b"\xe1\x65\xfe\x18\x7d\x84\xe0\x10\x05\x18\x69\x0c\xe6\xfd\xc9\x0c" \
    b"\x90\x04\xe9\x0c\xc6\xfd\x85\xfe\xa8\xb9\x86\xe1\x85\xff\xb9\x7a" \
    b"\xe1\xa4\xfd\x88\x30\x06\x46\xff\x6a\x88\x10\xfa\x18\x7d\x87\xe0" \
    b"\x9d\x8d\xe0\xa5\xff\x7d\x8a\xe0\x9d\x90\xe0\xbd\x05\xe0\xd0\x03" \
    b"\x4c\xa0\xe6\xbd\x45\xe0\x1d\x48\xe0\xf0\x16\xbd\x0e\xe0\xdd\x8d" \
    b"\xe0\xbd\x11\xe0\xfd\x90\xe0\xa9\xfe\x6a\x9d\x42\xe0\x90\x11\xf0" \
    b"\x4a\x9d\x42\xe0\xbd\x8d\xe0\x9d\x0e\xe0\xbd\x90\xe0\x9d\x11\xe0" \
    b"\xbd\x36\xe0\x0a\xd0\x35\xbd\x93\xe0\xf0\x0c\xbd\x99\xe0\x9d\x14" \
    b"\xe0\xbd\x9c\xe0\x9d\x17\xe0\xbd\x9f\xe0\xf0\x0f\xa4\xfd\x18\x79" \
    b"\x92\xe1\xa4\xfe\x18\x79\x9a\xe1\x18\x90\x08\xbd\xa2\xe0\xf0\x0b" \
    b"\xbd\xa5\xe0\x8d\x24\xe0\xa9\x00\x8d\x23\xe0\xbd\x3c\xe0\x9d\x3f" \
    b"\xe0\xbd\x05\xe0\x29\x40\x9d\x36\xe0\xbd\x05\xe0\x4a\x4a\x29\x07" \
    b"\xd0\x30\xbd\x05\xe0\x30\x14\xad\x27\xe0\x29\x3c\xd0\x1e\xad\x27" \
    b"\xe0\x0a\x2a\x2a\xd0\x02\xa9\x04\x4c\x70\xe8\xad\x28\xe0\xf0\x0c" \
    b"\x29\x3f\xd0\x08\xad\x28\xe0\x0a\x2a\x2a\xd0\x66\xa9\x10\x8d\x00" \
    b"\xe0\x60\xc9\x01\xd0\x13\xbd\x05\xe0\x29\x20\xd0\x06\xad\x29\xe0" \
    b"\x4c\x70\xe8\xbd\x2a\xe0\x4c\x70\xe8\xa8\xbd\x05\xe0\x29\xa0\xc9" \
    b"\x80\xf0\x30\x85\xff\x18\xad\x27\xe0\xd0\x01\x38\x88\x88\xf0\x06" \
    b"\x6a\xb0\x4e\x88\xd0\xfa\xa4\xff\x85\xff\xf0\x26\x46\xff\xb0\x41" \
    b"\xf0\x42\x65\xff\xb0\x3e\xc8\x10\x19\x46\xff\xb0\x34\x65\xff\x90" \
    b"\x11\xb0\x31\xad\x28\xe0\xf0\x29\x88\x88\xf0\x06\x4a\xb0\x22\x88" \
    b"\xd0\xfa\x9d\x30\xe0\xbd\x1a\xe0\x29\xf6\x9d\x1a\xe0\x38\xbd\x02" \
    b"\xe0\x29\x07\xd0\x03\x7e\x36\xe0\xbd\x1a\xe0\x69\x00\x9d\x1a\xe0" \
    b"\x60\xa9\x10\x2c\xa9\x18\x8d\x00\xe0\x60\x98\x48\xa5\xff\x4a\x90" \
    b"\x03\x4c\x42\xea\x4a\x4a\xb0\x1e\x4a\xb0\x0e\x9d\x9c\xe0\x9d\x17" \
    b"\xe0\x68\x9d\x99\xe0\x9d\x14\xe0\x60\x4a\x90\x02\x09\xf8\x9d\x8a" \
    b"\xe0\x68\x9d\x87\xe0\x60\x4a\xb0\x03\x4c\x4a\xe9\x4a\xb0\x61\x4a" \
    b"\xb0\x0f\xd0\x08\x68\x9d\xa5\xe0\x8d\x24\xe0\x60\x68\x9d\x3c\xe0" \
    b"\x60\xd0\x48\x68\x9d\x7e\xe0\xc9\x5b\xf0\x33\xa8\x4a\x4a\x4a\x38" \
    b"\xe9\x0b\x18\x7d\x84\xe0\x30\x0c\xc9\x0c\x90\x11\xe9\x0c\xde\x81" \
    b"\xe0\x4c\x0b\xe9\xc9\xf5\xb0\x05\x69\x0c\xfe\x81\xe0\x9d\x84\xe0" \
    b"\x98\x29\x07\x38\xe9\x03\x18\x7d\x81\xe0\x9d\x81\xe0\x60\xbd\x78" \
    b"\xe0\x9d\x81\xe0\xbd\x7b\xe0\x9d\x84\xe0\x60\x68\x9d\xc6\xe0\x60" \
    b"\x4a\xb0\x08\x9d\x0b\xe0\x68\x9d\x08\xe0\x60\x4a\x6a\x6a\x6d\x5b" \
    b"\xe1\x8d\x2d\xe0\x68\x6d\x5c\xe1\x8d\x2e\xe0\x60\x4a\x90\x03\x4c" \
    b"\xd3\xe9\x4a\xb0\x40\x4a\xb0\x17\x4a\xb0\x0f\x68\x8d\x27\xe0\x4a" \
    b"\x4a\x4a\xa8\xb9\xaf\xe1\x8d\x28\xe0\x60\x68\x9d\x5d\xe0\x60\x4a" \
    b"\xb0\x05\x68\x8d\x01\xe0\x60\x68\xf0\x11\x9d\x75\xe0\xbc\x63\xe0" \
    b"\xd0\x08\x9d\x63\xe0\xa9\x01\x9d\x66\xe0\x60\x9d\x63\xe0\x9d\x69" \
    b"\xe0\x9d\x6c\xe0\x60\x4a\xb0\x30\x4a\xb0\x05\x68\x9d\x39\xe0\x60" \
    b"\x68\xa0\x00\x4a\x90\x02\xc8\x18\x48\x29\x07\x79\xac\xe1\x9d\x78" \
    b"\xe0\x9d\x81\xe0\x68\x4a\x4a\x4a\x18\x79\xad\xe1\x9d\x7b\xe0\x9d" \
    b"\x84\xe0\xa9\x5b\x9d\x7e\xe0\x60\x4a\xb0\x05\x68\x9d\xa2\xe0\x60" \
    b"\x68\x8d\xcc\xe0\x60\x4a\xb0\x27\x4a\xb0\x0d\x4a\xb0\x05\x68\x8d" \
    b"\x29\xe0\x60\x68\x9d\x9f\xe0\x60\x4a\xb0\x0f\x68\x9d\x93\xe0\xa0" \
    b"\x00\x0a\x90\x01\x88\x98\x9d\x96\xe0\x60\x68\x9d\x72\xe0\x60\x4a" \
    b"\xb0\x1c\x4a\xb0\x15\x68\x9d\xb7\xe0\xa5\xfd\x9d\xb1\xe0\xa5\xfe" \
    b"\x9d\xb4\xe0\xbd\x33\xe0\x9d\xae\xe0\x60\x68\x6c\x5f\xe1\x4a\xb0" \
    b"\x1e\x68\xd0\x0a\x9d\x4b\xe0\x9d\x51\xe0\x9d\x54\xe0\x60\x9d\x5a" \
    b"\xe0\xbc\x4b\xe0\xd0\x08\x9d\x4b\xe0\xa9\x01\x9d\x4e\xe0\x60\x68" \
    b"\x9d\x2a\xe0\x60\x4a\x90\x08\x9d\x48\xe0\x68\x9d\x45\xe0\x60\x68" \
    b"\x4a\xb0\x61\x4a\xb0\x25\x4a\xb0\x05\x4a\xa0\xf0\xd0\x06\x0a\x0a" \
    b"\x0a\x0a\xa0\x0f\x85\xff\x98\xb0\x09\x3d\x1d\xe0\x05\xff\x9d\x1d" \
    b"\xe0\x60\x3d\x20\xe0\x05\xff\x9d\x20\xe0\x60\x4a\xb0\x38\x4a\xb0" \
    b"\x64\x85\xff\xbd\xba\xe0\xdd\xa9\xe1\xf0\x54\xfe\xba\xe0\xa8\xa5" \
    b"\xfd\x99\xe1\xe0\xa5\xfe\x99\xf0\xe0\xbd\x33\xe0\x99\x2f\xe1\xa4" \
    b"\xff\xb9\x17\xe1\xf0\x36\x85\xfe\xb9\xff\xe0\x85\xfd\xb9\x3e\xe1" \
    b"\x9d\x33\xe0\x60\xb0\x4b\x4a\xb0\x3c\xa8\xa5\xfd\x99\xff\xe0\xa5" \
    b"\xfe\x99\x17\xe1\xbd\x33\xe0\x99\x3e\xe1\xbd\xba\xe0\xdd\xa9\xe1" \
    b"\xf0\x0d\xfe\xba\xe0\xa8\xa9\x00\x99\xf0\xe0\x60\xa9\x30\x2c\xa9" \
    b"\x28\x8d\x00\xe0\x60\x0a\x0a\x0a\x0a\x4d\x25\xe0\x29\xf0\x4d\x25" \
    b"\xe0\x8d\x25\xe0\x60\x4d\x26\xe0\x29\x0f\x4d\x26\xe0\x8d\x26\xe0" \
    b"\x60\x4a\xb0\x0b\x4a\xb0\x04\x8d\xca\xe0\x60\x8d\xcb\xe0\x60\x4a" \
    b"\x90\x03\x4c\xa5\xeb\x4a\xa8\xf0\x21\x88\xf0\x34\x88\xf0\x42\x88" \
    b"\xf0\x4a\x88\xf0\x52\x88\xf0\x5c\x88\xf0\x66\x88\xf0\x73\x29\x07" \
    b"\x09\x10\xb0\x03\x4c\xb7\xea\x4c\x7f\xea\xac\x26\xe0\xb0\x07\xc8" \
    b"\x98\x29\x0f\xd0\x07\x60\x98\x29\x0f\xf0\x04\x88\x8c\x26\xe0\x60" \
    b"\xbd\x62\xe1\x49\xff\x2d\x25\xe0\x90\x03\x1d\x62\xe1\x8d\x25\xe0" \
    b"\x60\xbd\x1a\xe0\x29\xfb\x90\x55\x09\x04\xb0\x51\xbd\x1a\xe0\x29" \
    b"\xfd\x90\x4a\x09\x02\xb0\x46\xad\x25\xe0\x29\xf7\x90\x02\x09\x08" \
    b"\x8d\x25\xe0\x60\xad\x26\xe0\x29\x7f\x90\x02\x09\x80\x8d\x26\xe0" \
    b"\x60\x98\x8d\xbd\xe0\x8d\xdf\xe0\xc8\x8c\xe0\xe0\x2a\x8d\xc9\xe0" \
    b"\x60\x98\x2a\x9d\x60\xe0\x60\x4a\xb0\x27\x4a\xb0\x14\xd0\x02\xa9" \
    b"\x08\x0a\x0a\x0a\x0a\x5d\x1a\xe0\x29\xf0\x5d\x1a\xe0\x9d\x1a\xe0" \
    b"\x60\x0a\x0a\x0a\x0a\x4d\x26\xe0\x29\x70\x4d\x26\xe0\x8d\x26\xe0" \
    b"\x60\x4a\x90\x04\x9d\xc0\xe0\x60\xa8\xf0\x20\x88\xf0\x40\x88\xf0" \
    b"\x63\x29\x03\x9d\xc3\xe0\xa9\x00\x9d\xcd\xe0\x9d\xd0\xe0\x9d\xd3" \
    b"\xe0\x9d\xd6\xe0\x8d\xd9\xe0\x8d\xdc\xe0\x60\xbd\xb7\xe0\xf0\x05" \
    b"\xde\xb7\xe0\xf0\x12\xbd\x33\xe0\xdd\xae\xe0\xd0\x0b\xbd\xb1\xe0" \
    b"\x85\xfd\xbd\xb4\xe0\x85\xfe\x60\xa9\x38\x8d\x00\xe0\x60\xbd\xba" \
    b"\xe0\xdd\xa8\xe1\xf0\x18\xde\xba\xe0\xa8\x88\xb9\xf0\xe0\xf0\x0d" \
    b"\x85\xfe\xb9\xe1\xe0\x85\xfd\xb9\x2f\xe1\x9d\x33\xe0\x60\xa9\x20" \
    b"\x8d\x00\xe0\x60\xad\x00\xe0\x5d\x62\xe1\x8d\x00\xe0\xa9\x01\x9d" \
    b"\x30\xe0\x60\xad\x00\xe0\x29\x07\x8d\x81\xec\xd0\x03\x20\xe9\xe2" \
    b"\x60\x00\xa2\x51\xa0\xec\x8e\x5d\xe1\x8c\x5e\xe1\x20\xcf\xe1\xa2" \
    b"\x00\xa0\x09\x20\x00\xe2\xa9\x07\x8d\x00\xe0\x8d\x81\xec\x60\x00" \
    b"\x00\x00\xa9\x00\x29\xff\xf0\xf6\x4c\x29\xe3\xa9\x07\x8d\x00\xe0" \
    b"\x60" \
    b"\xa9\x35\x85\x01\x4c\x60\xec"
    # $EC8F LDA #$35
    # $EC91 STA $01
    # $EC93 JMP $EC60 

class SIDbits(IntEnum):
    V1FLO	= 0
    V1FHI	= 1
    V1PWLO	= 2
    V1PWHI	= 3
    V1CTRL	= 4
    V1AD	= 5
    V1SR	= 6

    V2FLO	= 7
    V2FHI	= 8
    V2PWLO	= 9
    V2PWHI	= 10
    V2CTRL	= 11
    V2AD	= 12
    V2SR	= 13

    V3FLO	= 14
    V3FHI	= 15
    V3PWLO	= 16
    V3PWHI	= 17
    V3CTRL	= 18
    V3AD	= 19
    V3SR	= 20

    FCOLO	= 21
    FCOHI	= 22
    FRES	= 23
    VOL		= 24

######################################################
# SIDParser using external SIDdumpHR or SIDdump
# defaulting to Python version otherwise
######################################################
def SIDParser(filename,ptime,order = 0, subtune = 1):

    if which('siddumphr') != None:
        _siddump = 'siddumphr'
    elif which('siddump') != None:
        _siddump = 'siddump'
    else:
        _LOG('WARNING: siddump not found on PATH, using python version', v=2)
        return SIDParser2(filename, ptime, order, subtune)
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

    try:
        sidsub = subprocess.Popen(_siddump+' '+filename+' -t'+str(ptime)+' -a'+str(subtune-1), shell=True, stdout=subprocess.PIPE)
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
                ctrl = frame[rsection]
                if len(ctrl) > 6:   #ANSI escape codes present
                    # Hardrestart?
                    rbitmap |= 2**(29+((rsection-4)//6))
                    ctrl = ctrl[7:]
                if ctrl[:2] != b'..':
                    rbitmap |= 2**rbit
                    sidregs += bytes.fromhex(ctrl[:2].decode("utf-8"))
                    rcount += 1
            #<<<<<<<<<<<<<<< Voices 1-3 ADSR
            if rsection == 5:
                adsr = frame[5]
                if len(adsr) > 8:   #ANSI escape codes present
                    rbitmap |= 2**26
                    adsr = adsr[7:]
                if adsr[:4] != b'....':
                    tt = bytes.fromhex(adsr[:4].decode("utf-8"))
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
                adsr = frame[11]
                if len(adsr) > 8:   #ANSI escape codes present
                    rbitmap |= 2**27
                    adsr = adsr[7:]
                if adsr[:4] != b'....':
                    tt = bytes.fromhex(adsr[:4].decode("utf-8"))
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
                adsr = frame[17]
                if len(adsr) > 8:   #ANSI escape codes present
                    rbitmap |= 2**28
                    adsr = adsr[7:]
                if adsr[:4] != b'....':
                    tt = bytes.fromhex(adsr[:4].decode("utf-8"))
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
                        sidregs += bytes([tt[1]>>5]) # Low Nibble (fixed missing shift right)
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

##########################################################
# Fallback internal SIDParser using Python 6502 simulator
##########################################################
def SIDParser2(filename,ptime,order = 0, subtune = 1):
    MAX_INSTR = 0x100000

    def readword(f):
        w = f.read(2)
        return (w[0]<<8)|w[1]

    try:
        with open(filename,'rb') as f_in:
            header = f_in.read(4)
            if header == b'PSID' or header == b'RSID':
                f_in.seek(6,0)
                dataoffset = readword(f_in)
                loadaddress = readword(f_in)
                initaddress = readword(f_in)
                playaddress = readword(f_in)
                f_in.seek(dataoffset,0)
                if loadaddress == 0:
                    loadaddress = f_in.read(1)[0]|f_in.read(1)[0]<<8
                #Load C64 data
                loadpos = f_in.tell()
                f_in.seek(0,2)
                loadend = f_in.tell()
                f_in.seek(loadpos,0)
                loadsize = loadend-loadpos
                memconf = 0x37
                if loadsize + loadaddress > 0x10000:
                    _LOG("SIDParser Error: SID data continues past end of C64 memory.")
                c65.mem[loadaddress:loadaddress+loadsize] = list(f_in.read(loadsize))
            else: #MUS file
                f_in.seek(2, 0) # Skip load address
                voice1size = f_in.read(1)[0]|(f_in.read(1)[0] << 8)
                voice2size = f_in.read(1)[0]|(f_in.read(1)[0] << 8)
                voice3size = f_in.read(1)[0]|(f_in.read(1)[0] << 8)
                f_in.seek(voice1size+6, 0)
                v1hlt = readword(f_in)
                f_in.seek(voice1size+6+voice2size, 0)
                v2hlt = readword(f_in)
                f_in.seek(voice1size+6+voice2size+voice3size, 0)
                v3hlt = readword(f_in)
                if ((v1hlt != 0x014f)or(v2hlt != 0x014f)or(v3hlt != 0x014f)):
                    _LOG("SIDParser Error: Unknown file type.")
                f_in.seek(0,2)
                loadsize = f_in.tell()-2
                f_in.seek(2, 0)
                loadaddress = 0x0900
                c65.mem[loadaddress:loadaddress+loadsize] = f_in.read(loadsize)
                playaddress = 0xec80
                initaddress = 0xec60
                memconf = 0x35
                c65.mem[0xe000,0xe000+len[mus_driver]-2] = mus_driver
        c65.mem[0x01] = memconf
        c65.initcpu(initaddress,subtune-1,0,0)
        instr = 0
        while c65.runcpu():
            c65.mem[0xd012] += 1
            if (not c65.mem[0xd012] or ((c65.mem[0xd011] & 0x80) and c65.mem[0xd012] >= 0x38)):
                c65.mem[0xd011] ^= 0x80
                c65.mem[0xd012] = 0x00
            instr += 1
            if instr > MAX_INSTR:
                _LOG("SIDParser Warning: CPU executed a high number of instructions in init, breaking",v=2)
                break
        if (playaddress == 0):
            _LOG("SIDParser Warning: SID has play address 0, reading from interrupt vector instead",v=2)
            if ((c65.mem[0x01] & 0x07) == 0x5):
                playaddress = c65.mem[0xfffe] | (c65.mem[0xffff] << 8)
            else:
                playaddress = c65.mem[0x314] | (c65.mem[0x315] << 8)
        #Clear temporal registers
        oldregs = [0]*25
        #writecnt = [0]*25
        frames = 0
        out = []
        while frames < ptime*50:
            #Run the play routine
            instr = 0
            rcount = 4
            rbitmap = 0
            sidregs = b''
            c65.initcpu(playaddress,0,0,0)
            c65.watch(0xd400,0xd418,1)
            writecnt = [0]*25
            while c65.runcpu():
                instr += 1
                if instr > MAX_INSTR:
                    _LOG("SIDParser Warning: CPU executed a high number of instructions in playroutine, breaking",v=2)
                    break
                if c65.watchp >= 0:
                    writecnt[c65.watchp-0xd400] += 1
                if (c65.mem[0x01]&0x07 != 0x05) and (c65.pc == 0xea31 or c65.pc == 0xea81):
                    break
            for r,c in enumerate(writecnt):
                #if register was written to and has different value than last frame
                #or if control or ADSR has been written to more than once
                if ((c > 0) and (c65.mem[0xd400+r]!=oldregs[r])) or ((c > 1) and (r in [4,11,18,5,6,12,13,19,20])):	
                    rbitmap |= 2**r
                    rcount += 1
                    sidregs += c65.mem[0xd400+r].to_bytes(1,'little')
                #Hard restart bits
                if (c > 1):
                    if r in [4,11,18]:	# Gate hardrestart
                        rbitmap |= 2**(29+int((r-4)/7))
                    elif r in [5,6,12,13,19,20]:	# ADSR hardrestart
                        rbitmap |= 2**(26+round((r-5)/7))
            oldregs = c65.mem[0xd400:0xd419]
            out.append([rcount.to_bytes(1,'little'),rbitmap.to_bytes(4,'big'),sidregs])
            frames += 1
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        _LOG(f'SIDParser error:{exc_type} on {fname} line {exc_tb.tb_lineno}')
    return out

#########################################
# Convert AY register dump to SID stream
#########################################
def AYtoSID(filename):

    sidsus = lambda i: round(2**(((i*2)+1-31)/4)*15)	# Converts the AY logarithmic volume level to SID linear sustain level
    sidtone = lambda i: int(i) if i<65536 else 65535

    prev_stat = [{'freq':0,'freqHz':0,'Gate':False,'Env':False,'Tone':False,'Noise':False,'Nfreq':0,'Vol':0},  #Channel A
                {'freq':0,'freqHz':0,'Gate':False,'Env':False,'Tone':False,'Noise':False,'Nfreq':0,'Vol':0},  #Channel B
                {'freq':0,'freqHz':0,'Gate':False,'Env':False,'Tone':False,'Noise':False,'Nfreq':0,'Vol':0},  #Channel C
                {'Nfreq':0,'Ep':0,'Shape':0}]  #Noise and Envelope
    
    sid_decay = [0.006,0.024,0.048,0.072,0.114,0.168,0.204,0.240,0.300,0.720,1.5,2.4,3,9,15,24]
    sid_attack = [0.002,0.008,0.016,0.024,0.038,0.056,0.068,0.080,0.100,0.240,0.500,0.800,1,3,5,8]
    sidfreq = 985248	#PAL clock
    dump = None
    try:
        data = YM.YMOpen(filename)
        if data != None:
            frames,meta = YM.YMDump(data)
            ymfreq = meta['clock']
            if frames != None:
                dump = []
                # Init SID
                rcount = 26 # 22 register + 4 bytes from the bitmap
                rbitmap = 0b1000111111111111111111111
                sidregs = b'\x00\x00\x00\x08\x00\x00\x00\x00\x00\x00\x08\x00\x00\x00\x00\x00\x00\x08\x00\x00\x00\x0f'
                dump.append([rcount.to_bytes(1,'little'),rbitmap.to_bytes(4,'big'),sidregs])
                for fn,frame in enumerate(frames):
                    Gate = [False,False,False]
                    envgate = False	#Envelope gate
                    srtmp = [0x00]*25
                    sidregs = b''
                    rbitmap = 0
                    rcount = 4
                    for v in range(3):
                        rstart = False
                        Wave = 0x40		#Pulse
                        # useP True if SID frequency register needs to be refreshed with PSG tone frequency
                        useP = ((not prev_stat[v]['Tone'])and((frame[7] & 2**v)== 0)and((frame[7] & 2**(v+3))!= 0))\
                            or (prev_stat[v]['Noise'] and ((frame[7] & 2**v)== 0)and((frame[7] & 2**(v+3))!= 0))
                        if (frame[7] & 2**v)== 0:    # Tone enabled?
                            prev_stat[v]['Tone'] = True
                            Gate[v] = True
                        pitch = frame[0+(2*v)]+((frame[1+(2*v)]&15)*256)
                        try:
                            freq = ymfreq/(16*pitch)    #16!!!
                        except:
                            freq = 0
                        if (pitch != prev_stat[v]['freq']) or (fn == 0) or useP:
                            prev_stat[v]['freqHz'] = freq
                            prev_stat[v]['freq'] = pitch
                            sidpitch = sidtone((freq*16777216)//sidfreq)
                            srtmp[SIDbits.V1FLO+(7*v)] = sidpitch.to_bytes(2,'little')[0]
                            srtmp[SIDbits.V1FHI+(7*v)] = sidpitch.to_bytes(2,'little')[1]
                            rbitmap |= (2**(SIDbits.V1FLO+(v*7)))|(2**(SIDbits.V1FHI+(v*7)))
                        if (frame[7] & 2**(v+3))== 0:  # Noise enabled?
                            Gate[v] = True
                            Wave = 0x80	#Noise
                        if (frame[8+v] & 16)== 0:     # Amplitude control
                            if (prev_stat[v]['Vol'] != frame[8+v]&15) or (fn == 0) or prev_stat[v]['Env']:
                                if (prev_stat[v]['Vol']<(frame[8+v] & 15)) or prev_stat[v]['Env']:
                                    if sidsus(frame[8+v]&15)>0:    # Converted sustain level is > 0
                                        ... #New volume higher than previous, or envelope disengaged, retrigger note
                                        rbitmap |= 2**(26+v) | 2**(29+v)	# Hard restart
                                        rstart = True
                                prev_stat[v]['Vol'] = frame[8+v]&15
                                if frame[8+v]&15 == 0:
                                    Gate[v] = False
                                else:
                                    rbitmap |= 2**(SIDbits.V1SR+(v*7))
                                    srtmp[SIDbits.V1SR+(v*7)] = 16*sidsus(frame[8+v]&15)
                                prev_stat[v]['Env'] = False
                                rbitmap |= 2**(SIDbits.V1AD+(v*7))
                                srtmp[SIDbits.V1AD+(v*7)] = 0
                            Gate[v] &= (frame[8+v] & 31)!= 0
                        else:
                            prev_stat[v]['Env'] = True
                        if Gate[v] != prev_stat[v]['Gate']:
                            prev_stat[v]['Gate'] = Gate[v]
                        rbitmap |= 2**(SIDbits.V1CTRL+(v*7))
                        srtmp[SIDbits.V1CTRL+(v*7)] = Wave|(1 if Gate[v] else 0)
                    if (prev_stat[3]['Nfreq'] != frame[6]) or (fn == 0):
                        prev_stat[3]['Nfreq'] = frame[6]
                    for i in range(3):  #set noise frequency if used
                        if (not prev_stat[i]['Noise']) and ((frame[7] & 2**(i+3))== 0):
                            try:
                                freq = ymfreq/(256*frame[6]) #16!!!!
                            except:
                                freq = 4000
                            sidpitch = sidtone((freq*16777216)/sidfreq)
                            srtmp[SIDbits.V1FLO+(7*i)] = sidpitch.to_bytes(2,'little')[0]
                            srtmp[SIDbits.V1FHI+(7*i)] = sidpitch.to_bytes(2,'little')[1]
                            rbitmap |= (2**(SIDbits.V1FHI+(i*7)))|(2**(SIDbits.V1FLO+(i*7)))
                        prev_stat[i]['Noise'] = (frame[7] & 2**(i+3))== 0
                    if (prev_stat[3]['Ep'] != frame[11]+(frame[12]*256)) or (fn == 0):
                        prev_stat[3]['Ep'] = frame[11]+(frame[12]*256)
                        try:
                            enfreq = ymfreq/(prev_stat[3]['Ep']*256)
                        except:
                            enfreq = 4000
                    if frame[13] != 255:
                        prev_stat[3]['Shape'] = frame[13]&15
                        envgate = True
                    for i in range(3):
                        #Check if any voice is using the envelope
                        if (frame[8+i] & 16)!= 0:
                            #this voice uses the envelope
                            if (prev_stat[3]['Shape'] == 8) or (prev_stat[3]['Shape'] ==12):    #Both Sawtooth envelopes
                                if (prev_stat[i]['Tone'])and(prev_stat[i]['Noise'] == False)and(0.3<(prev_stat[i]['freqHz']/enfreq)<2.6):  # Noise not selected and envelope frequency near voice freq or armonic
                                    #Mixed waveforms
                                    rbitmap |= 2**(SIDbits.V1CTRL+(i*7))
                                    srtmp[SIDbits.V1CTRL+(i*7)] = 0x60 | (1 if Gate[i] else 0)
                                elif not prev_stat[i]['Tone'] and not prev_stat[i]['Noise']:
                                    #Envelope as waveform
                                    rbitmap |= 2**(SIDbits.V1CTRL+(i*7))|2**(SIDbits.V1FLO+(i*7))|2**(SIDbits.V1FHI+(i*7))
                                    srtmp[SIDbits.V1CTRL+(i*7)] = 0x21
                                    sidpitch = sidtone((enfreq*16777216)//sidfreq)
                                    srtmp[SIDbits.V1FLO+(7*i)] = sidpitch.to_bytes(2,'little')[0]
                                    srtmp[SIDbits.V1FHI+(7*i)] = sidpitch.to_bytes(2,'little')[1]
                            elif (prev_stat[3]['Shape'] == 10) or (prev_stat[3]['Shape'] == 14): #Both Triangle envelopes
                                if (prev_stat[i]['Tone'])and(prev_stat[i]['Noise'] == False)and(0.3<(prev_stat[i]['freqHz']/(enfreq/2))<2.6):  # Noise not selected and envelope frequency near voice freq or armonic
                                    #Mixed waveforms
                                    rbitmap |= 2**(SIDbits.V1CTRL+(i*7))
                                    srtmp[SIDbits.V1CTRL+(i*7)] = 0x50 | (1 if Gate[i] else 0)
                                elif not prev_stat[i]['Tone'] and not prev_stat[i]['Noise']:
                                    #Envelope as waveform
                                    rbitmap |= 2**(SIDbits.V1CTRL+(i*7))|2**(SIDbits.V1FLO+(i*7))|2**(SIDbits.V1FHI+(i*7))
                                    srtmp[SIDbits.V1CTRL+(i*7)] = 0x11
                                    sidpitch = sidtone((enfreq*16777216)//sidfreq)
                                    srtmp[SIDbits.V1FLO+(7*i)] = sidpitch.to_bytes(2,'little')[0]
                                    srtmp[SIDbits.V1FHI+(7*i)] = sidpitch.to_bytes(2,'little')[1]
                            elif (prev_stat[3]['Shape'] == 9) or (prev_stat[3]['Shape']<4) and envgate: #Both Release envelopes
                                rbitmap |= 2**(26+i) | 2**(29+i) | 2**(SIDbits.V1AD+(i*7)) | 2**(SIDbits.V1CTRL+(i*7))	# Hard restart
                                srtmp[SIDbits.V1AD+(i*7)] = sid_decay.index(min(sid_decay, key=lambda x:abs(x-(1/enfreq))))
                                srtmp[SIDbits.V1CTRL+(i*7)] = (0x80 if  prev_stat[i]['Noise'] else 0x80 if prev_stat[i]['Tone'] else 0)|(1 if Gate[i] else 0)
                            elif (3 < prev_stat[3]['Shape'] < 8 ) or (prev_stat[3]['Shape']== 15) and envgate: #Both Attack envelopes
                                rbitmap |= 2**(26+i) | 2**(29+i) | 2**(SIDbits.V1AD+(i*7)) | 2**(SIDbits.V1CTRL+(i*7))	# Hard restart
                                srtmp[SIDbits.V1AD+(i*7)] = sid_attack.index(min(sid_attack, key=lambda x:abs(x-(1/enfreq))))*16
                                srtmp[SIDbits.V1CTRL+(i*7)] = (0x80 if  prev_stat[i]['Noise'] else 0x80 if prev_stat[i]['Tone'] else 0)|(1 if Gate[i] else 0)
                            elif (prev_stat[3]['Shape'] == 13) and envgate: # Attack-Sustain envelope
                                rbitmap |= 2**(26+i) | 2**(29+i) | 2**(SIDbits.V1SR+(i*7)) | 2**(SIDbits.V1AD+(i*7)) | 2**(SIDbits.V1CTRL+(i*7))	# Hard restart
                                srtmp[SIDbits.V1AD+(i*7)] = sid_attack.index(min(sid_attack, key=lambda x:abs(x-(1/enfreq))))*16
                                srtmp[SIDbits.V1SR+(i*7)] = 0xf0
                                srtmp[SIDbits.V1CTRL+(i*7)] = (0x80 if  prev_stat[i]['Noise'] else 0x80 if prev_stat[i]['Tone'] else 0)|(1 if Gate[i] else 0)
                    for b in range(25):
                        if (rbitmap & 2**b) != 0:
                            rcount +=1
                            sidregs += srtmp[b].to_bytes(1,'little')
                    dump.append([rcount.to_bytes(1,'little'),rbitmap.to_bytes(4,'big'),sidregs])
        else:
            _LOG('AYtoSID: Error opening file')
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        _LOG(f'AYtoSID error:{exc_type} on {fname} line {exc_tb.tb_lineno}')
    return dump

# Moved here to bypass 'circular' imports
from common import ymparse as YM
