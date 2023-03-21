# Basic 65xx CPU simulator, based on Lasse Oorni (loorni@gmail.com) and Stein Pedersen's work for SIDdump
from common.bbsdebug import _LOG


# Global variables
pc:int  = 0
a:int   = 0
x:int   = 0
y:int   = 0
flags:int = 0
sp:int  = 0
mem:list = [0]*65536
cpucycles:int = 0
watchp:int = 0


#Status register bits
FN:int = 0x80
FV:int = 0x40
FB:int = 0x10
FD:int = 0x08
FI:int = 0x04
FZ:int = 0x02
FC:int = 0x01
#Negated versions
_FN:int = 0x7f
_FV:int = 0xbf
_FB:int = 0xef
_FD:int = 0xf7
_FI:int = 0xfb
_FZ:int = 0xfd
_FC:int = 0xfe

LO = lambda: mem[pc]
HI = lambda: mem[pc+1]

def FETCH():
    global pc
    pc += 1
    return mem[pc-1]

def SETPC(newpc):
    global pc
    pc = newpc

def PUSH(data):
    global mem, sp
    mem[0x100+sp] = data
    sp -= 1

def POP():
    global sp
    sp +=1
    return mem[0x100+sp]

#real	0m3,109s < all lambdas
#real	0m2,975s < no LO() HI()

IMMEDIATE   = lambda: mem[pc] #lambda: LO()
ABSOLUTE    = lambda: mem[pc] | (mem[pc+1] << 8)
ABSOLUTEX   = lambda: ((mem[pc] | (mem[pc+1] << 8)) + x) & 0xffff
ABSOLUTEY   = lambda: ((mem[pc] | (mem[pc+1] << 8)) + y) & 0xffff
ZEROPAGE    = lambda: mem[pc] #& 0xff
ZEROPAGEX   = lambda: (mem[pc] + x) & 0xff
ZEROPAGEY   = lambda: (mem[pc] + y) & 0xff
INDIRECTX   = lambda: mem[(mem[pc] + x) & 0xff] | (mem[(mem[pc] + x + 1) & 0xff] << 8)
INDIRECTY   = lambda: ((mem[mem[pc]] | (mem[(mem[pc] + 1) & 0xff] << 8)) + y) & 0xffff
INDIRECTZP  = lambda: ((mem[mem[pc]] | (mem[(mem[pc] + 1) & 0xff] << 8)) + 0) & 0xffff

def WRITE(address):
  global watchp
  if (((wpoint['acctype'] & 1) == 1) and (address >= wpoint['startaddr']) and (address <= wpoint['endaddr'])):
    watchp = address

EVALPAGECROSSING = lambda baseaddr, realaddr: 1 if (((baseaddr) ^ (realaddr)) & 0xff00) != 0 else 0
EVALPAGECROSSING_ABSOLUTEX = lambda: EVALPAGECROSSING(ABSOLUTE(), ABSOLUTEX())
EVALPAGECROSSING_ABSOLUTEY = lambda: EVALPAGECROSSING(ABSOLUTE(), ABSOLUTEY())
EVALPAGECROSSING_INDIRECTY = lambda: EVALPAGECROSSING(INDIRECTZP(), INDIRECTY())

def BRANCH():
  global cpucycles
 
  cpucycles += 1
  temp = FETCH()
  temp = temp if temp < 0x80 else temp-256
  cpucycles += EVALPAGECROSSING(pc, pc + temp)
  SETPC(pc + temp)
  # if (temp < 0x80):
  #   cpucycles += EVALPAGECROSSING(pc, pc + temp)
  #   SETPC(pc + temp)
  # else:
  #   cpucycles += EVALPAGECROSSING(pc, pc + temp - 0x100)
  #   SETPC(pc + temp - 0x100)

def SETFLAGS(data):
  global flags

  if not(data):
    flags = (flags & _FN) | FZ
  else:
    flags = (flags & (~(FN|FZ)&0xff)) | ((data) & FN)

def ASSIGNSETFLAGS(data):
  global flags

  dest = data & 0xff
  if not dest:
    flags = (flags & _FN) | FZ
  else:
    flags = (flags & (~(FN|FZ)&0xff)) | (dest & FN)

  return dest

def ADC(data):
    global flags, a
    #tempval = data

    if (flags & FD):
        temp = (a & 0xf) + (data & 0xf) + (flags & FC)
        if (temp > 0x9):
            temp += 0x6
        if (temp <= 0x0f):
            temp = (temp & 0xf) + (a & 0xf0) + (data & 0xf0)
        else:
            temp = (temp & 0xf) + (a & 0xf0) + (data & 0xf0) + 0x10
        if (not((a + data + (flags & FC)) & 0xff)):
            flags |= FZ
        else:
            flags &= _FZ
        if (temp & 0x80):
            flags |= FN
        else:
            flags &= _FN
        if (((a ^ temp) & 0x80) and not((a ^ data) & 0x80)):
            flags |= FV
        else:
            flags &= _FV
        if ((temp & 0x1f0) > 0x90):
            temp += 0x60
        if ((temp & 0xff0) > 0xf0):
            flags |= FC
        else:
            flags &= _FC
    else:
        temp = data + a + (flags & FC)
        SETFLAGS(temp & 0xff)
        if (not((a ^ data) & 0x80) and ((a ^ temp) & 0x80)):
            flags |= FV
        else:
            flags &= _FV
        if (temp > 0xff):
            flags |= FC
        else:
            flags &= _FC
    a = temp & 0xff


def SBC(data):
    global flags,a

    #tempval = data
    temp = (a - data - ((flags & FC) ^ FC))&0x1ff
    if (flags & FD):
        tempval2 = (a & 0xf) - (data & 0xf) - ((flags & FC) ^ FC)
        if (tempval2 & 0x10):
            tempval2 = ((tempval2 - 6) & 0xf) | ((a & 0xf0) - (data & 0xf0) - 0x10)
        else:
            tempval2 = (tempval2 & 0xf) | ((a & 0xf0) - (data & 0xf0))
        if (tempval2 & 0x100):
            tempval2 -= 0x60
        if (temp < 0x100):
            flags |= FC
        else:
            flags &= _FC
        SETFLAGS(temp & 0xff)
        if (((a ^ temp) & 0x80) and ((a ^ data) & 0x80)):
            flags |= FV
        else:
            flags &= _FV
        a = tempval2 & 0xff
    else:
        SETFLAGS(temp & 0xff)
        if (temp < 0x100):
            flags |= FC
        else:
            flags &= _FC
        if (((a ^ temp) & 0x80) and ((a ^ data) & 0x80)):
            flags |= FV
        else:
            flags &= _FV
        a = temp & 0xff

def CMP(src, data):
  global flags

  temp = (src - data) & 0xff
  flags = (flags & (~(FC|FN|FZ)&0xff)) | (temp & FN)
  if (not temp):
     flags |= FZ
  if (src >= data):
     flags |= FC

def ASL(data):
  global flags

  #temp = data
  data <<= 1
  if (data & 0x100):
    flags |= FC
  else:
    flags &= _FC
  return ASSIGNSETFLAGS(data)

def LSR(data):
  global flags

  #temp = data
  if (data & 1):
    flags |= FC
  else:
    flags &= _FC
  data >>= 1
  return ASSIGNSETFLAGS(data)

def ROL(data):
  global flags

  #temp = data
  data <<= 1
  if (flags & FC):
    data |= 1
  if (data & 0x100):
    flags |= FC
  else:
    flags &= _FC
  return ASSIGNSETFLAGS(data)

def ROR(data):
  global flags

  #temp = data
  if (flags & FC):
    data |= 0x100
  if (data & 1):
    flags |= FC
  else:
    flags &= _FC
  data >>= 1
  return ASSIGNSETFLAGS(data)

# def DEC(data):
#   temp = (data - 1)&0xff
#   return ASSIGNSETFLAGS(temp)

DEC = lambda data: ASSIGNSETFLAGS((data - 1)&0xff)

# def INC(data):
#   #temp = (data + 1)&0xff
#   return ASSIGNSETFLAGS((data + 1)&0xff)

INC = lambda data: ASSIGNSETFLAGS((data + 1)&0xff)

def EOR(data):
  global a

  a ^= data
  SETFLAGS(a)

def ORA(data):
  global a
  a |= data
  SETFLAGS(a)

def AND(data):
  global a

  a &= data
  SETFLAGS(a)

def BIT(data):
  global flags

  flags = (flags & (~(FN|FV)&0xff)) | (data & (FN|FV))
  if (not(data & a)):
    flags |= FZ
  else:
    flags &= _FZ

cpucycles_table = [
  7,  6,  0,  8,  3,  3,  5,  5,  3,  2,  2,  2,  4,  4,  6,  6, 
  2,  5,  0,  8,  4,  4,  6,  6,  2,  4,  2,  7,  4,  4,  7,  7, 
  6,  6,  0,  8,  3,  3,  5,  5,  4,  2,  2,  2,  4,  4,  6,  6, 
  2,  5,  0,  8,  4,  4,  6,  6,  2,  4,  2,  7,  4,  4,  7,  7, 
  6,  6,  0,  8,  3,  3,  5,  5,  3,  2,  2,  2,  3,  4,  6,  6, 
  2,  5,  0,  8,  4,  4,  6,  6,  2,  4,  2,  7,  4,  4,  7,  7, 
  6,  6,  0,  8,  3,  3,  5,  5,  4,  2,  2,  2,  5,  4,  6,  6, 
  2,  5,  0,  8,  4,  4,  6,  6,  2,  4,  2,  7,  4,  4,  7,  7, 
  2,  6,  2,  6,  3,  3,  3,  3,  2,  2,  2,  2,  4,  4,  4,  4, 
  2,  6,  0,  6,  4,  4,  4,  4,  2,  5,  2,  5,  5,  5,  5,  5, 
  2,  6,  2,  6,  3,  3,  3,  3,  2,  2,  2,  2,  4,  4,  4,  4, 
  2,  5,  0,  5,  4,  4,  4,  4,  2,  4,  2,  4,  4,  4,  4,  4, 
  2,  6,  2,  8,  3,  3,  5,  5,  2,  2,  2,  2,  4,  4,  6,  6, 
  2,  5,  0,  8,  4,  4,  6,  6,  2,  4,  2,  7,  4,  4,  7,  7, 
  2,  6,  2,  8,  3,  3,  5,  5,  2,  2,  2,  2,  4,  4,  6,  6, 
  2,  5,  0,  8,  4,  4,  6,  6,  2,  4,  2,  7,  4,  4,  7,  7
]



wpoint ={'acctype':0,'startaddr':0,'endaddr':0}

def initcpu(newpc, newa, newx, newy):
  global pc, a, x, y, flags, sp, cpucycles, wpoint, watchp

  pc = newpc
  a = newa
  x = newx
  y = newy
  flags = 0
  sp = 0xff
  cpucycles = 0

  wpoint = {'acctype':0,'startaddr':0,'endaddr':0}
  watchp = -1

def watch(startaddr, endaddr, acctype):
  global wpoint
  wpoint = {'acctype':acctype,'startaddr':startaddr,'endaddr':endaddr}


def runcpu():
  global a, x, y, sp, cpucycles, flags, pc, mem, watchp
  op = FETCH()

  #print(f"PC: {pc-1:#0{6}x} OP: {op:#0{4}x} A:{a:#0{4}x} X:{x:#0{4}x} Y:{y:#0{4}x}")

  cpucycles += cpucycles_table[op]
  watchp = -1
  if op == 0xa7:
    a = ASSIGNSETFLAGS(mem[ZEROPAGE()])
    x = a
    pc += 1
  elif op == 0xb7:
    a = ASSIGNSETFLAGS(mem[ZEROPAGEY()])
    x = a
    pc += 1
  elif op == 0xaf:
    a = ASSIGNSETFLAGS(mem[ABSOLUTE()])
    x = a
    pc += 2
  elif op == 0xa3:
    a = ASSIGNSETFLAGS(mem[INDIRECTX()])
    x = a
    pc +=1
  elif op == 0xb3:
    cpucycles += EVALPAGECROSSING_INDIRECTY()
    a = ASSIGNSETFLAGS(mem[INDIRECTY()])
    x = a
    pc += 1
  elif op in [0x1a,0x3a,0x5a,0x7a,0xda,0xfa]:
    ...
  elif op in [0x80,0x82,0x89,0xc2,0xe2,0x04,0x44,0x64,0x14,0x34,0x54,0x74,0xd4,0xf4]:
    pc += 1
  elif op in [0x0c,0x1c,0x3c,0x5c,0x7c,0xdc,0xfc]:
    cpucycles += EVALPAGECROSSING_ABSOLUTEX()
    pc += 2
  elif op == 0x69:
    ADC(IMMEDIATE())
    pc += 1
  elif op == 0x65:
    ADC(mem[ZEROPAGE()])
    pc += 1
  elif op == 0x75:
    ADC(mem[ZEROPAGEX()])
    pc += 1
  elif op == 0x6d:
    ADC(mem[ABSOLUTE()])
    pc += 2
  elif op == 0x7d:
    cpucycles += EVALPAGECROSSING_ABSOLUTEX()
    ADC(mem[ABSOLUTEX()])
    pc += 2
  elif op == 0x79:
    cpucycles += EVALPAGECROSSING_ABSOLUTEY()
    ADC(mem[ABSOLUTEY()])
    pc += 2
  elif op == 0x61:
    ADC(mem[INDIRECTX()])
    pc += 1
  elif op == 0x71:
    cpucycles += EVALPAGECROSSING_INDIRECTY()
    ADC(mem[INDIRECTY()])
    pc += 1
  elif op == 0x29:
    AND(IMMEDIATE())
    pc += 1
  elif op == 0x25:
    AND(mem[ZEROPAGE()])
    pc += 1
  elif op == 0x35:
    AND(mem[ZEROPAGEX()])
    pc += 1
  elif op == 0x2d:
    AND(mem[ABSOLUTE()])
    pc += 2
  elif op == 0x3d:
    cpucycles += EVALPAGECROSSING_ABSOLUTEX()
    AND(mem[ABSOLUTEX()])
    pc += 2
  elif op == 0x39:
    cpucycles += EVALPAGECROSSING_ABSOLUTEY()
    AND(mem[ABSOLUTEY()])
    pc += 2
  elif op == 0x21:
    AND(mem[INDIRECTX()])
    pc += 1
  elif op == 0x31:
    cpucycles += EVALPAGECROSSING_INDIRECTY()
    AND(mem[INDIRECTY()])
    pc += 1
  elif op == 0x0a:
    a = ASL(a)
  elif op == 0x06:
    mem[ZEROPAGE()] = ASL(mem[ZEROPAGE()])
    pc += 1
  elif op == 0x16:
    mem[ZEROPAGEX()] = ASL(mem[ZEROPAGEX()])
    pc += 1
  elif op == 0x0e:
    mem[ABSOLUTE()] = ASL(mem[ABSOLUTE()])
    pc += 2
  elif op == 0x1e:
    mem[ABSOLUTEX()] = ASL(mem[ABSOLUTEX()])
    pc += 2
  elif op == 0x90:
    if (not(flags & FC)):
       BRANCH()
    else:
       pc += 1
  elif op == 0xb0:
    if (flags & FC):
       BRANCH()
    else:
       pc += 1
  elif op == 0xf0:
    if (flags & FZ):
       BRANCH()
    else:
       pc += 1
  elif op == 0x24:
    BIT(mem[ZEROPAGE()])
    pc += 1
  elif op == 0x2c:
    BIT(mem[ABSOLUTE()])
    pc += 2
  elif op == 0x30:
    if (flags & FN):
       BRANCH()
    else:
       pc += 1
  elif op == 0xd0:
    if (not(flags & FZ)):
       BRANCH()
    else:
       pc += 1
  elif op == 0x10:
    if (not(flags & FN)):
       BRANCH()
    else:
       pc += 1
  elif op == 0x50:
    if (not(flags & FV)):
       BRANCH()
    else:
       pc += 1
  elif op == 0x70:
    if (flags & FV):
       BRANCH()
    else:
       pc += 1
  elif op == 0x18:
    flags &= _FC
  elif op == 0xd8:
    flags &= _FD
  elif op == 0x58:
    flags &= _FI
  elif op == 0xb8:
    flags &= _FV
  elif op == 0xc9:
    CMP(a, IMMEDIATE())
    pc += 1
  elif op == 0xc5:
    CMP(a, mem[ZEROPAGE()])
    pc += 1
  elif op == 0xd5:
    CMP(a, mem[ZEROPAGEX()])
    pc += 1
  elif op == 0xcd:
    CMP(a, mem[ABSOLUTE()])
    pc += 2
  elif op == 0xdd:
    cpucycles += EVALPAGECROSSING_ABSOLUTEX()
    CMP(a, mem[ABSOLUTEX()])
    pc += 2
  elif op == 0xd9:
    cpucycles += EVALPAGECROSSING_ABSOLUTEY()
    CMP(a, mem[ABSOLUTEY()])
    pc += 2
  elif op == 0xc1:
    CMP(a, mem[INDIRECTX()])
    pc += 1
  elif op == 0xd1:
    cpucycles += EVALPAGECROSSING_INDIRECTY()
    CMP(a, mem[INDIRECTY()])
    pc += 1
  elif op == 0xe0:
    CMP(x, IMMEDIATE())
    pc += 1
  elif op == 0xe4:
    CMP(x, mem[ZEROPAGE()])
    pc += 1
  elif op == 0xec:
    CMP(x, mem[ABSOLUTE()])
    pc += 2
  elif op == 0xc0:
    CMP(y, IMMEDIATE())
    pc += 1
  elif op == 0xc4:
    CMP(y, mem[ZEROPAGE()])
    pc += 1
  elif op == 0xcc:
    CMP(y, mem[ABSOLUTE()])
    pc += 2
  elif op == 0xc6:
    mem[ZEROPAGE()] = DEC(mem[ZEROPAGE()])
    WRITE(ZEROPAGE())
    pc += 1
  elif op == 0xd6:
    mem[ZEROPAGEX()] = DEC(mem[ZEROPAGEX()])
    WRITE(ZEROPAGEX())
    pc += 1
  elif op == 0xce:
    mem[ABSOLUTE()] = DEC(mem[ABSOLUTE()])
    WRITE(ABSOLUTE())
    pc += 2
  elif op == 0xde:
    mem[ABSOLUTEX()] = DEC(mem[ABSOLUTEX()])
    WRITE(ABSOLUTEX())
    pc += 2
  elif op == 0xca:
    x -= 1
    x &= 0xff
    SETFLAGS(x)
  elif op == 0x88:
    y -= 1
    y &= 0xff
    SETFLAGS(y)
  elif op == 0x49:
    EOR(IMMEDIATE())
    pc += 1
  elif op == 0x45:
    EOR(mem[ZEROPAGE()])
    pc += 1
  elif op == 0x55:
    EOR(mem[ZEROPAGEX()])
    pc += 1
  elif op == 0x4d:
    EOR(mem[ABSOLUTE()])
    pc += 2
  elif op == 0x5d:
    cpucycles += EVALPAGECROSSING_ABSOLUTEX()
    EOR(mem[ABSOLUTEX()])
    pc += 2
  elif op == 0x59:
    cpucycles += EVALPAGECROSSING_ABSOLUTEY()
    EOR(mem[ABSOLUTEY()])
    pc += 2
  elif op == 0x41:
    EOR(mem[INDIRECTX()])
    pc += 1
  elif op == 0x51:
    cpucycles += EVALPAGECROSSING_INDIRECTY()
    EOR(mem[INDIRECTY()])
    pc += 1
  elif op == 0xe6:
    mem[ZEROPAGE()] = INC(mem[ZEROPAGE()])
    WRITE(ZEROPAGE())
    pc += 1
  elif op == 0xf6:
    mem[ZEROPAGEX()] = INC(mem[ZEROPAGEX()])
    WRITE(ZEROPAGEX())
    pc += 1
  elif op == 0xee:
    mem[ABSOLUTE()] = INC(mem[ABSOLUTE()])
    WRITE(ABSOLUTE())
    pc += 2
  elif op == 0xfe:
    mem[ABSOLUTEX()] = INC(mem[ABSOLUTEX()])
    WRITE(ABSOLUTEX())
    pc += 2
  elif op == 0xe8:
    x += 1
    x &= 0xff
    SETFLAGS(x)
  elif op == 0xc8:
    y += 1
    y &= 0xff
    SETFLAGS(y)
  elif op == 0x20:
    PUSH((pc+1) >> 8)
    PUSH((pc+1) & 0xff)
    pc = ABSOLUTE()
  elif op == 0x4c:
    pc = ABSOLUTE()
  elif op == 0x6c:
      adr = ABSOLUTE()
      pc = mem[adr] | (mem[((adr + 1) & 0xff) | (adr & 0xff00)] << 8)
  elif op == 0xa9:
    a = ASSIGNSETFLAGS(IMMEDIATE())
    pc += 1
  elif op == 0xa5:
    a = ASSIGNSETFLAGS(mem[ZEROPAGE()])
    pc += 1
  elif op == 0xb5:
    a = ASSIGNSETFLAGS(mem[ZEROPAGEX()])
    pc += 1
  elif op == 0xad:
    a = ASSIGNSETFLAGS(mem[ABSOLUTE()])
    pc += 2
  elif op == 0xbd:
    cpucycles += EVALPAGECROSSING_ABSOLUTEX()
    a = ASSIGNSETFLAGS(mem[ABSOLUTEX()])
    pc += 2
  elif op == 0xb9:
    cpucycles += EVALPAGECROSSING_ABSOLUTEY()
    a = ASSIGNSETFLAGS(mem[ABSOLUTEY()])
    pc += 2
  elif op == 0xa1:
    a = ASSIGNSETFLAGS(mem[INDIRECTX()])
    pc += 1
  elif op == 0xb1:
    cpucycles += EVALPAGECROSSING_INDIRECTY()
    a = ASSIGNSETFLAGS(mem[INDIRECTY()])
    pc += 1
  elif op == 0xa2:
    x = ASSIGNSETFLAGS(IMMEDIATE())
    pc += 1
  elif op == 0xa6:
    x = ASSIGNSETFLAGS(mem[ZEROPAGE()])
    pc += 1
  elif op == 0xb6:
    x = ASSIGNSETFLAGS(mem[ZEROPAGEY()])
    pc += 1
  elif op == 0xae:
    x = ASSIGNSETFLAGS(mem[ABSOLUTE()])
    pc += 2
  elif op == 0xbe:
    cpucycles += EVALPAGECROSSING_ABSOLUTEY()
    x = ASSIGNSETFLAGS(mem[ABSOLUTEY()])
    pc += 2
  elif op == 0xa0:
    y = ASSIGNSETFLAGS(IMMEDIATE())
    pc += 1
  elif op == 0xa4:
    y = ASSIGNSETFLAGS(mem[ZEROPAGE()])
    pc += 1
  elif op == 0xb4:
    y = ASSIGNSETFLAGS(mem[ZEROPAGEX()])
    pc += 1
  elif op == 0xac:
    y = ASSIGNSETFLAGS(mem[ABSOLUTE()])
    pc += 2
  elif op == 0xbc:
    cpucycles += EVALPAGECROSSING_ABSOLUTEX()
    y = ASSIGNSETFLAGS(mem[ABSOLUTEX()])
    pc += 2
  elif op == 0x4a:
    a = LSR(a)
  elif op == 0x46:
    mem[ZEROPAGE()] = LSR(mem[ZEROPAGE()])
    WRITE(ZEROPAGE())
    pc += 1
  elif op == 0x56:
    mem[ZEROPAGEX()] = LSR(mem[ZEROPAGEX()])
    WRITE(ZEROPAGEX())
    pc += 1
  elif op == 0x4e:
    mem[ABSOLUTE()] = LSR(mem[ABSOLUTE()])
    WRITE(ABSOLUTE())
    pc += 2
  elif op == 0x5e:
    mem[ABSOLUTEX()] = LSR(mem[ABSOLUTEX()])
    WRITE(ABSOLUTEX())
    pc += 2
  elif op == 0xea:
    ...
  elif op == 0x09:
    ORA(IMMEDIATE())
    pc += 1
  elif op == 0x05:
    ORA(mem[ZEROPAGE()])
    pc += 1
  elif op == 0x15:
    ORA(mem[ZEROPAGEX()])
    pc += 1
  elif op == 0x0d:
    ORA(mem[ABSOLUTE()])
    pc += 2
  elif op == 0x1d:
    cpucycles += EVALPAGECROSSING_ABSOLUTEX()
    ORA(mem[ABSOLUTEX()])
    pc += 2
  elif op == 0x19:
    cpucycles += EVALPAGECROSSING_ABSOLUTEY()
    ORA(mem[ABSOLUTEY()])
    pc += 2
  elif op == 0x01:
    ORA(mem[INDIRECTX()])
    pc += 1
  elif op == 0x11:
    cpucycles += EVALPAGECROSSING_INDIRECTY()
    ORA(mem[INDIRECTY()])
    pc += 1
  elif op == 0x48:
    PUSH(a)
  elif op == 0x08:
    PUSH(flags | 0x30)
  elif op == 0x68:
    a = ASSIGNSETFLAGS(POP())
  elif op == 0x28:
    flags = POP()
  elif op == 0x2a:
    a = ROL(a)
  elif op == 0x26:
    mem[ZEROPAGE()] = ROL(mem[ZEROPAGE()])
    WRITE(ZEROPAGE())
    pc += 1
  elif op == 0x36:
    mem[ZEROPAGEX()] = ROL(mem[ZEROPAGEX()])
    WRITE(ZEROPAGEX())
    pc += 1
  elif op == 0x2e:
    mem[ABSOLUTE()] = ROL(mem[ABSOLUTE()])
    WRITE(ABSOLUTE())
    pc += 2
  elif op == 0x3e:
    mem[ABSOLUTEX()] = ROL(mem[ABSOLUTEX()])
    WRITE(ABSOLUTEX())
    pc += 2
  elif op == 0x6a:
    a = ROR(a)
  elif op == 0x66:
    mem[ZEROPAGE()] = ROR(mem[ZEROPAGE()])
    WRITE(ZEROPAGE())
    pc += 1
  elif op == 0x76:
    mem[ZEROPAGEX()] = ROR(mem[ZEROPAGEX()])
    WRITE(ZEROPAGEX())
    pc += 1
  elif op == 0x6e:
    mem[ABSOLUTE()] = ROR(mem[ABSOLUTE()])
    WRITE(ABSOLUTE())
    pc += 2
  elif op == 0x7e:
    mem[ABSOLUTEX()] = ROR(mem[ABSOLUTEX()])
    WRITE(ABSOLUTEX())
    pc += 2
  elif op == 0x40:
    if (sp == 0xff):
      return 0
    flags = POP()
    pc = POP()
    pc |= POP() << 8
  elif op == 0x60:
    if (sp == 0xff):
      return 0
    pc = POP()
    pc |= POP() << 8
    pc += 1
  elif op in [0xe9,0xeb]:
    SBC(IMMEDIATE())
    pc += 1
  elif op == 0xe5:
    SBC(mem[ZEROPAGE()])
    pc += 1
  elif op == 0xf5:
    SBC(mem[ZEROPAGEX()])
    pc += 1
  elif op == 0xed:
    SBC(mem[ABSOLUTE()])
    pc += 2
  elif op == 0xfd:
    cpucycles += EVALPAGECROSSING_ABSOLUTEX()
    SBC(mem[ABSOLUTEX()])
    pc += 2
  elif op == 0xf9:
    cpucycles += EVALPAGECROSSING_ABSOLUTEY()
    SBC(mem[ABSOLUTEY()])
    pc += 2
  elif op == 0xe1:
    SBC(mem[INDIRECTX()])
    pc += 1
  elif op == 0xf1:
    cpucycles += EVALPAGECROSSING_INDIRECTY()
    SBC(mem[INDIRECTY()])
    pc += 1
  elif op == 0x38:
    flags |= FC
  elif op == 0xf8:
    flags |= FD
  elif op == 0x78:
    flags |= FI
  elif op == 0x85:
    mem[ZEROPAGE()] = a
    WRITE(ZEROPAGE())
    pc += 1
  elif op == 0x95:
    mem[ZEROPAGEX()] = a
    WRITE(ZEROPAGEX())
    pc += 1
  elif op == 0x8d:
    mem[ABSOLUTE()] = a
    WRITE(ABSOLUTE())
    pc += 2
  elif op == 0x9d:
    mem[ABSOLUTEX()] = a
    WRITE(ABSOLUTEX())
    pc += 2
  elif op == 0x99:
    mem[ABSOLUTEY()] = a
    WRITE(ABSOLUTEY())
    pc += 2
  elif op == 0x81:
    mem[INDIRECTX()] = a
    WRITE(INDIRECTX())
    pc += 1
  elif op == 0x91:
    mem[INDIRECTY()] = a
    WRITE(INDIRECTY())
    pc += 1
  elif op == 0x86:
    mem[ZEROPAGE()] = x
    WRITE(ZEROPAGE())
    pc += 1
  elif op == 0x96:
    mem[ZEROPAGEY()] = x
    WRITE(ZEROPAGEY())
    pc += 1
  elif op == 0x8e:
    mem[ABSOLUTE()] = x
    WRITE(ABSOLUTE())
    pc += 2
  elif op == 0x84:
    mem[ZEROPAGE()] = y
    WRITE(ZEROPAGE())
    pc += 1
  elif op == 0x94:
    mem[ZEROPAGEX()] = y
    WRITE(ZEROPAGEX())
    pc += 1
  elif op == 0x8c:
    mem[ABSOLUTE()] = y
    WRITE(ABSOLUTE())
    pc += 2
  elif op == 0xaa:
    x = ASSIGNSETFLAGS(a)
  elif op == 0xba:
    x = ASSIGNSETFLAGS(sp)
  elif op == 0x8a:
    a = ASSIGNSETFLAGS(x)
  elif op == 0x9a:
    sp = x
  elif op == 0x98:
    a = ASSIGNSETFLAGS(y)
  elif op == 0xa8:
    y = ASSIGNSETFLAGS(a)
  elif op == 0x00:
    return 0
  elif op == 0x02:
    _LOG(f"CPU65 Error: CPU halt at {pc-1:#0{6}x}", pc-1)
    return 0
  else:
    _LOG(f"CPU65 Error: Unknown opcode {op:#0{4}x} at {pc-1:#0{6}x}", op, pc-1)
    return 0
  return 1

# def setpc(newpc):
#   global pc
#   pc = newpc

