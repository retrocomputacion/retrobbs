import random
import string
from tinydb import Query, where
from datetime import datetime

from common.connection import Connection
from common.style import RenderMenuTitle
from common.bbsdebug import _LOG
from common.style import KeyLabel
from common.style import bbsstyle
import common.turbo56k as TT

wordlist = {0:[],1:[],2:[],3:[],4:[],5:[],6:[]}

##################
# Plugin setup
##################
def setup():
    global wordlist
    with open("plugins/mindle_words/dict1.txt",'r') as wf:
        words = wf.read().splitlines()
    for l in words:
        if ' ' in words[0]: # Wordlist has dificulty info
            d,w = l.split(' ')
        else:
            d = 6
            w = l
        wordlist[int(d)].append(w)
    fname = "MINDLE"    # UPPERCASE function name for config.ini
    parpairs = []   # config.ini Parameter pairs (name,defaultvalue)
    return(fname,parpairs)



#####################
# Plugin function
#####################
def plugFunction(conn:Connection):

    # Render title
    def header():
        conn.SendTML(conn.templates.GetTemplate('mindle/title'))

    window_s = conn.QueryFeature(TT.SET_WIN) < 0x80

    if conn.encoder.colors == {}:
        conn.SendTML("<CLR><FORMAT>You need a color terminal to play Mindle...</FORMAT><BR><PAUSE n=3>")
        return
    if  conn.encoder.txt_geo[0] < 30:
        conn.SendTML("<CLR><FORMAT>Mindle needs at least 30 columns to work...</FORMAT><BR><PAUSE n=3>")
        return
    mcolors = conn.templates.GetStyle('mindle/default')
    if conn.encoder.features['bgcolor'] == 0:
        if '64' in conn.mode:
            badcolor = ('<ORANGE>','Orange')
        else:
            badcolor = ('<PINK>','Pink')
    else:
        if conn.mode == 'ATRSTM':
            badcolor = ('<RED>','Red')
        else:
            badcolor = ('<BLACK>','Black')

    if conn.mode == 'ATRSTM':
        cowcolor = ('<BLACK>','Black')
    else:
        cowcolor = ('<YELLOW>','Yellow')
    dbase = conn.bbs.database
    table = dbase.db
    dbQ = Query()
    today = datetime.today().timetuple().tm_yday
    dificulty = datetime.today().weekday()
    xwords = []
    scwidth, scheight = conn.encoder.txt_geo
    for i in range(dificulty,7):
        xwords += wordlist[i]
    if table.get(dbQ.record == 'mindle') == None:
        table.insert({'record':'mindle', 'daily': xwords[random.randrange(0,len(xwords))].lower(), 'day': today, 'scores':{}, 'players':[]})
    mdata = table.get(dbQ.record == 'mindle')
    if mdata['day'] != today:  # New word every day
        mdata['day'] = today
        mdata['daily'] = xwords[random.randrange(0,len(xwords))].lower()
        mdata['players'] = []
        table.update({'daily':mdata['daily'], 'day':mdata['day'],'players':[]}, where('record') == 'mindle')
    tops = sorted(mdata['scores'].items(), key=lambda x:x[1], reverse=True) # Sorted list of top scores

    valid = []
    with open(f"plugins/mindle_words/valid{str(len(mdata['daily']))}.txt",'r') as wf:
        valid = wf.read().splitlines()
    valid += [word for wl in wordlist.values() for word in wl if len(word)== len(mdata['daily'])]

    players = mdata.get('players',[])

    conn.SendTML(f'<TEXT border={mcolors.BgColor} background={mcolors.BgColor}><CLR>')

    header()
    xc = scwidth//4
    back = conn.encoder.decode(conn.encoder.back)
    while conn.connected:
        keys = 'bcd' + back
        conn.SendTML(f'<AT x={xc} y=8>')
        if (conn.userclass != 0) and (conn.userid not in players):
            KeyLabel(conn,'a','Play daily Mindle',True,mcolors)
            keys += 'a'
        conn.SendTML(f'<BR><CRSRR n={xc}>')
        KeyLabel(conn,'b','Free play',False,mcolors)
        conn.SendTML(f'<BR><CRSRR n={xc}>')
        KeyLabel(conn,'c','View High Scores',True,mcolors)
        conn.SendTML(f'<BR><CRSRR n={xc}>')
        KeyLabel(conn,'d','How to play',False,mcolors)
        conn.SendTML(f'<BR><CRSRR n={xc}>')
        KeyLabel(conn,'_','Exit',True,mcolors)
        rec = conn.ReceiveKey(keys)
        if rec == 'b':     ##### Free play
            if window_s:
                conn.SendTML(f'<WINDOW top=3 bottom={scheight-1}><CLR><WINDOW>')
            else:
                conn.SendTML('<CLR>')
                header()
            xwords = [] # Include _all_ words for free play
            for wl in wordlist:
                xwords +=wordlist[wl]
            xword = xwords[random.randrange(0,len(xwords))].lower()
            xvalid = [] # Get the valid words for this xword lenght
            with open(f"plugins/mindle_words/valid{str(len(xword))}.txt",'r') as wf:
                xvalid = wf.read().splitlines()
                xvalid += [word for word in xwords if len(word)== len(xword)]
            score = mindle(conn, xword, xvalid,mcolors)
            if  score >= 0:
                conn.SendTML('<PAUSE n=5>')
            if window_s:
                conn.SendTML(f'<WINDOW top=3 bottom={scheight}><CLR><WINDOW>')
            else:
                conn.SendTML('<CLR>')
                header()
        elif rec == 'c':   # High scores
            if len(tops) > 0:
                if window_s:
                    conn.SendTML(f'<WINDOW top=3 bottom={scheight}><CLR><WINDOW>')
                else:
                    conn.SendTML('<CLR>')
                    header()
                conn.SendTML(f'<AT x={(scwidth-10)//2} y=7><LTGREEN>Top Scores<INK c={mcolors.TxtColor}><BR><BR>')
                tmp = dbase.getUsers()
                tmp = [(x[0],x[1]) for x in tmp]
                ulist = dict(tmp)
                j = len(tops) if len(tops)<=10 else 10
                for i in range(j):
                    uname = ulist[int(tops[i][0])]
                    conn.SendTML(f'<CRSRR n=10>{uname}<CRSRR n={17-len(uname)}>{tops[i][1]}<BR>')
                conn.SendTML(f'<AT x={(scwidth-25)//2} y={scheight-2}><GREEN>Press any key to continue')
                conn.Receive(1)
                if window_s:
                    conn.SendTML(f'<WINDOW top=3 bottom={scheight}><CLR><WINDOW>')
                else:
                    conn.SendTML('<CLR>')
                    header()
        elif rec == 'd':
            if window_s:
                conn.SendTML(f'<WINDOW top=3 bottom={scheight}><CLR>')
            else:
                conn.SendTML('<CLR>')
                header()
            conn.SendTML(f'''<FORMAT><INK c={mcolors.TxtColor}>Instructions: You have to guess the hidden word, you have 6 tries.<BR>Each try must be a valid word.<BR><BR>
After each try the color of the characters will change color to show how close you are from guessing the correct word.<BR>
<BR><GREEN> * <INK c={mcolors.TxtColor}>Green means the character exists in the hidden word and is in the correct position<BR>
{cowcolor[0]} * <INK c={mcolors.TxtColor}>{cowcolor[1]} means the character exists in the hidden word but is in the wrong position<BR>
{badcolor[0]} * <INK c={mcolors.TxtColor}>{badcolor[1]} means the character is not present in the hidden word<BR>
<BR>Press any key to continue</FORMAT>''')
            conn.Receive(1)
            conn.SendTML('<CLR><WINDOW>')
            if not window_s:
                header()
        elif rec == 'a':       ##### Daily Mindle
            if window_s:
                conn.SendTML(f'<WINDOW top=3 bottom={scheight}><CLR><WINDOW>')
            else:
                conn.SendTML('<CLR>')
                header()
            score = mindle(conn, mdata['daily'],valid,mcolors)
            if score != -1:
                players.append(conn.userid)
                mdata['players'] = players
                if score < 0:
                    score = 0
                conn.SendTML(f'<AT x=16 y=20>{score} points<PAUSE n=5>')
            mdata['scores'][str(conn.userid)] = mdata['scores'].get(str(conn.userid),0)+score
            table.update(mdata, where('record') == 'mindle')
            tops = sorted(mdata['scores'].items(), key=lambda x:x[1], reverse=True) # Re-Sorted list of top scores
            if window_s:
                conn.SendTML(f'<WINDOW top=3 bottom={scheight}><CLR><WINDOW>')
            else:
                conn.SendTML('<CLR>')
                header()
        else:
            break


###############
# Main game
###############
def mindle(conn:Connection, xword: str, valid, style:bbsstyle):

    scores = [500,400,200,100,50,25,0]
    #_LOG('Mindle - word to guess: '+xword,id=conn.id, v=4)

    ecolors = conn.encoder.colors
    scwidth, scheight = conn.encoder.txt_geo

    wlen = len(xword)  # Word length
    offset = ((scwidth-2)-(wlen+2))//2
    if wlen == 6:
        offset -= 1 # Center playfield

    # Draw playfield
    pfcolor = '<LTBLUE>' if 'LTBLUE' in ecolors else '<BLUE>' if 'BLUE' in ecolors else '<BLACK>'
    conn.SendTML(f'<AT x={offset} y=5><CURSOR enable=False>{pfcolor}<UL-CORNER>')
    for j in range(wlen-1):
        conn.SendTML('<HLINE><H-DOWN>')
    conn.SendTML('<HLINE><UR-CORNER><BR>')
    for i in range(6):
        conn.SendTML(f'<CRSRR n={offset}><VLINE>')
        for j in range(wlen):
            conn.SendTML(' <VLINE>')
        conn.SendTML('<BR>')
        if i == 5:
            break
        conn.SendTML(f'<CRSRR n={offset}><V-RIGHT>')
        for j in range(wlen-1):
            conn.SendTML('<HLINE><CROSS>')
        conn.SendTML('<HLINE><V-LEFT><BR>')
    conn.SendTML(f'<CRSRR n={offset}><LL-CORNER>')
    for j in range(wlen-1):
        conn.SendTML('<HLINE><H-UP>')
    conn.SendTML('<HLINE><LR-CORNER><BR>')

    abcoffset = (scwidth-len(string.ascii_uppercase))/2
    conn.SendTML(f'<AT x={abcoffset} y={scheight-2}><INK c={style.TxtColor}>{string.ascii_uppercase}<BR><RVSON><BACK>Exit<RVSOFF>')

    bulls = []
    cows = []
    bad = []

    if conn.encoder.features['bgcolor'] == 0:
        if '64' in conn.mode:
            badcolor = '<ORANGE>'
        else:
            badcolor = '<PINK>'
    else:
        if conn.mode == 'ATRSTM':
            badcolor = '<RED>'
        else:
            badcolor = '<BLACK>'
    bullcolor = f'<PAPER c={conn.encoder.colors["GREEN"]}><BLACK>' if 'MSX' in conn.mode else '<GREEN>'
    cowcolor =  f'<PAPER c={conn.encoder.colors["YELLOW"]}><BLACK>' if 'MSX' in conn.mode else '<YELLOW>' if conn.mode != 'ATRSTM' else '<BLACK>'
    wincolor = '<GREEN>' if conn.mode in ('VT52','VidTex','ATRSTM') else '<WHITE>'
    null = '' if conn.T56KVer == 0 else '<NULL>'

    t = 0   # Attempt number
    while t<6 and conn.connected:
        guess = ''
        line = 6+(t*2)
        column = offset+1
        t_bulls = []
        t_cows  = []
        t_bad   = []
        conn.SendTML(f'<AT x={column} y={line}>{"<GREY3>" if "PET" in conn.mode else "<PURPLE>"}')
        while conn.connected:   # Receive guess word
            keys = [conn.encoder.bs, conn.encoder.nl, conn.encoder.back]
            if len(guess) < wlen:
                keys.extend(list(string.ascii_letters))
            rec = conn.ReceiveKey(keys)
            if rec == conn.encoder.back: # Quit game
                return -1*(t+1)
            if (len(guess) == wlen) and (rec == conn.encoder.nl):   # A word has been received and return/enter pressed
                break
            elif (len(guess) != 0) and (rec == conn.encoder.bs): # Backspace/delete
                conn.SendTML('<CRSRL n=2> <CRSRL>')
                guess = guess[:-1]
            elif rec in string.ascii_letters:
                conn.SendTML(f'{rec.upper()}<CRSRR>')
                guess += rec
        conn.SendTML('<BR>')
        guess = guess.lower()
        if guess not in valid:
            conn.SendTML(f'<AT x={(scwidth-30)//2} y=19><GREY2>NOT A VALID WORD, try again...<BR><PAUSE n=2>')
            if conn.QueryFeature(TT.LINE_FILL) >= 0x80:
                conn.SendTML(f'<AT x={(scwidth-30)//2} y=19><SPC n=30>')
            else:
                conn.SendTML('<LFILL code=32 row=19>')
            conn.SendTML(f'<AT x={column} y={line}>')
            for i in range(wlen):
                conn.SendTML(' <CRSRR>')
            continue
        if guess == xword:
            conn.SendTML(f'{null}<AT x={column} y={line}><LTGREEN>')
            for c in xword:
                conn.SendTML(f'{c.upper()}<CRSRR>')
            conn.SendTML(f'<AT x={(scwidth-19)//2} y=19>{wincolor}<FLASHON>CONGRATULATIONS !!!<FLASHOFF>')
            break
        else:
            out = ''
            conn.SendTML(f'{null}<AT x={column} y={line}>')
            chars = {}
            for g,x in zip(guess,xword):
                if g == x:
                    continue
                elif x in chars:
                    chars[x] += 1
                else:
                    chars[x] = 1
            for g,x in zip(guess,xword):
                if g == x:
                    out += bullcolor
                    if g in cows:
                        cows.remove(g)
                    t_bulls.append(g)
                elif (g in xword) and (g in chars) and (chars[g] >= 0):
                    out += cowcolor
                    if (g not in bulls) and (g not in cows):
                        t_cows.append(g)
                    chars[g] -= 1
                else:
                    if 'MSX' in conn.mode:
                        out += f'<PAPER c={conn.encoder.colors["GREY"]}>'
                    out += badcolor
                    if g not in (bad+t_bad+t_bulls+t_cows):
                        t_bad.append(g)
                out += g.upper()+'<CRSRR>'
            if 'MSX' in conn.mode:
                out += f'<PAPER c={conn.encoder.colors["GREY"]}>'

            conn.SendTML(out)
            # Update used characters display
            t_bulls.sort()
            t_cows.sort()
            t_bad.sort()
            bulls += t_bulls
            cows += t_cows
            bad += t_bad
            bulls.sort()
            cows.sort()
            bad.sort()
            conn.SendTML(badcolor)
            for c in t_bad:
                conn.SendTML(f'<AT x={abcoffset+string.ascii_lowercase.index(c)} y={scheight-2}>{c.upper()}')
            conn.SendTML(cowcolor)
            for c in t_cows:
                conn.SendTML(f'<AT x={abcoffset+string.ascii_lowercase.index(c)} y={scheight-2}>{c.upper()}')
            conn.SendTML(bullcolor)
            for c in t_bulls:
                conn.SendTML(f'<AT x={abcoffset+string.ascii_lowercase.index(c)} y={scheight-2}>{c.upper()}')
            conn.SendTML(f'<PAPER c={style.BgColor}>')
        t += 1
    if t == 6:
        conn.SendTML(f'<AT x={(scwidth-24)//2} y=19><GREY2>Better luck next time...<BR>')
    conn.SendTML('<CURSOR>')
    return(scores[t])