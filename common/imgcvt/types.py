from enum import IntEnum

#Graphic modes
gfxmodes = IntEnum('gfxmodes',['C64HI','C64MULTI','P4HI','P4MULTI','MSXSC2','VTHI','VTMED'], start=0)

#Image scale/crop modes
cropmodes = IntEnum('cropmodes',['LEFT','TOP','RIGHT','BOTTOM','T_LEFT','T_RIGHT','B_LEFT','B_RIGHT','CENTER','FILL','FIT','H_FIT','V_FIT','BIG_FILL'], start=0)
