import random
import string
from tinydb import Query, where
from datetime import datetime

from common.connection import Connection
from common.bbsdebug import _LOG
from common.style import KeyLabel
from common.style import bbsstyle

wordlist = {0:[],1:[],2:[],3:[],4:[],5:[],6:[]}

###############
# Plugin setup
###############
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
    fname = "MINDLE" #UPPERCASE function name for config.ini
    parpairs = [] #config.ini Parameter pairs (name,defaultvalue)
    return(fname,parpairs)



###################################
# Plugin function
###################################
def plugFunction(conn:Connection):

    ecolors = conn.encoder.colors
    mcolors = bbsstyle(ecolors)
    mcolors.OoddBack = ecolors['BLACK']
    if 'MSX' in conn.mode:
        mcolors.ToddColor = ecolors['DARK_RED']
        mcolors.TevenColor = ecolors['BLUE']
    mcolors.OevenBack = ecolors['BLACK']
    mcolors.BgColor = ecolors['DARK_GREY']
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

    # if conn.mode == 'PET264':
    # scolor = ecolors['DARK_GREY']
    # else:
    #     scolor = 11

    conn.SendTML(f'<TEXT border={mcolors.BgColor} background={mcolors.BgColor}><CLR>')
    if 'PET' in conn.mode:
        conn.SendTML('<WHITE>  <BOTTOM-HASH n=11><GREEN><LR-QUAD> <LR-QUAD><LTGREEN><LR-QUAD>     <LL-QUAD><LL-QUAD> <YELLOW><B-HALF> <WHITE><BOTTOM-HASH n=11><BR>')
        conn.SendTML('<GREY3>   <BOTTOM-HASH n=10><GREEN><RVSON><L-HALF><RVSOFF><UL-LR-QUAD><RVSON><LL-QUAD><RVSOFF><LTGREEN><LR-QUAD> <RVSON><LR-QUAD><RVSOFF><UL-LR-QUAD><LR-QUAD><RVSON><B-HALF><RVSOFF><L-HALF><L-HALF><YELLOW><RVSON><L-HALF><RVSOFF><B-HALF><L-HALF><GREY3><BOTTOM-HASH n=10><BR>')
        conn.SendTML('<GREY2>    <BOTTOM-HASH n=9><GREEN><RVSON><L-HALF><CRSRR><L-HALF><LTGREEN><L-HALF><RVSOFF><LL-QUAD><L-HALF><RVSON><L-HALF><RVSOFF><UR-QUAD><B-HALF><L-HALF><RVSON><UR-QUAD><RVSOFF><YELLOW><UR-QUAD><B-HALF><LL-QUAD><GREY2><BOTTOM-HASH n=9><BR>')
    else:
        conn.SendTML('<PINK>  <LL-QUAD><B-HALF N=6><DGREEN><LR-QUAD> <LR-QUAD><GREEN><LR-QUAD>     <LL-QUAD><LL-QUAD> <YELLOW><B-HALF><PINK> <B-HALF N=6><LR-QUAD><BR>')
        conn.SendTML('<RED>   <LL-QUAD><B-HALF N=5><DGREEN><RVSON><L-HALF><RVSOFF><UL-LR-QUAD><RVSON><LL-QUAD><RVSOFF><GREEN><LR-QUAD> <RVSON><LR-QUAD><RVSOFF><UL-LR-QUAD><LR-QUAD><RVSON><B-HALF><RVSOFF><L-HALF><L-HALF><YELLOW><RVSON><L-HALF><RVSOFF><B-HALF><L-HALF><RED><B-HALF N=5><LR-QUAD><BR>')
        conn.SendTML('<DRED>    <LL-QUAD><B-HALF N=4><DGREEN><RVSON><L-HALF><CRSRR><L-HALF><GREEN><L-HALF><RVSOFF><LL-QUAD><L-HALF><RVSON><L-HALF><RVSOFF><UR-QUAD><B-HALF><L-HALF><RVSON><UR-QUAD><RVSOFF><YELLOW><UR-QUAD><B-HALF><LL-QUAD><DRED><B-HALF N=4><LR-QUAD><BR>')
    xc = scwidth//4
    while conn.connected:
        keys = '_bcd'
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
            conn.SendTML(f'<WINDOW top=3 bottom={scheight-1}><CLR><WINDOW>')
            xwords = [] # Include _all_ words for free play
            for wl in wordlist:
                xwords +=wordlist[wl]
            xword = xwords[random.randrange(0,len(xwords))].lower()
            xvalid = [] # Get the valid words for this xword lenght
            with open(f"plugins/mindle_words/valid{str(len(xword))}.txt",'r') as wf:
                xvalid = wf.read().splitlines()
                xvalid += [word for word in xwords if len(word)== len(xword)]
            score = mindle(conn, xword, xvalid)
            if  score >= 0:
                conn.SendTML('<PAUSE n=5>')
            conn.SendTML(f'<WINDOW top=3 bottom={scheight}><CLR><WINDOW>')
        elif rec == 'c':   # High scores
            if len(tops) > 0:
                conn.SendTML(f'<WINDOW top=3 bottom={scheight}><CLR><WINDOW>')
                conn.SendTML(f'<AT x={(scwidth-10)//2} y=7><LTGREEN>Top Scores<GREY3><BR><BR>')
                ulist = dict(dbase.getUsers())
                j = len(tops) if len(tops)<=10 else 10
                for i in range(j):
                    uname = ulist[int(tops[i][0])]
                    conn.SendTML(f'<CRSRR n=10>{uname}<CRSRR n={17-len(uname)}>{tops[i][1]}<BR>')
                conn.SendTML(f'<AT x={(scwidth-25)//2} y={scheight-2}><GREEN>Press any key to continue')
                conn.Receive(1)
                conn.SendTML(f'<WINDOW top=3 bottom={scheight}><CLR><WINDOW>')
        elif rec == 'd':
            conn.SendTML(f'<WINDOW top=3 bottom={scheight}><CLR><WINDOW>')
            conn.SendTML('<AT y=5><GREY3>Instructions: You have to guess the<BR> hidden word, you have 6 tries.<BR>Each try must be a valid word.<BR><BR>')
            conn.SendTML('After each try the color of the<BR> characters will change color to show<BR> how close you are from guessing the<BR> correct word.<BR>')
            conn.SendTML('<BR><GREEN> * <GREY3>Green means the character exists in<BR>   the hidden word and is in the<BR>   correct position<BR>')
            conn.SendTML('<YELLOW> * <GREY3>Yellow means the character exists in<BR>   the hidden word but is in the wrong<BR>   position<BR>')
            conn.SendTML("<BLACK> * <GREY3>Black means the character is not<BR>   present in the hidden word<BR>")
            conn.SendTML('<BR>       Press any key to continue')
            conn.Receive(1)
            conn.SendTML(f'<WINDOW top=3 bottom={scheight}><CLR><WINDOW>')
        elif rec == 'a':       ##### Daily Mindle
            conn.SendTML(f'<WINDOW top=3 bottom={scheight}><CLR><WINDOW>')
            score = mindle(conn, mdata['daily'],valid)
            if score != -1:
                players.append(conn.userid)
                mdata['players'] = players
                if score < 0:
                    score = 0
                conn.SendTML(f'<AT x=16 y=20>{score} points<PAUSE n=5>')
            mdata['scores'][str(conn.userid)] = mdata['scores'].get(str(conn.userid),0)+score
            table.update(mdata, where('record') == 'mindle')
            tops = sorted(mdata['scores'].items(), key=lambda x:x[1], reverse=True) # Re-Sorted list of top scores
            conn.SendTML(f'<WINDOW top=3 bottom={scheight}><CLR><WINDOW>')
        else:
            break


###################################
# Main game
###################################
def mindle(conn:Connection, xword: str, valid):

    scores = [500,400,200,100,50,25,0]
    #_LOG('Mindle - word to guess: '+xword,id=conn.id, v=4)

    scwidth, scheight = conn.encoder.txt_geo

    wlen = len(xword)  # Word lenght
    offset = ((scwidth-2)-(wlen+2))//2
    if wlen == 6:
        offset -= 1 # Center playfield

    # Draw playfield
    conn.SendTML(f'<AT x={offset} y=5><CURSOR enable=False><LTBLUE><UL-CORNER>')   # <HLINE><CHR c=178><HLINE><CHR c=178><HLINE><CHR c=178><HLINE><CHR c=178><HLINE><CHR c=174><BR>')
    for j in range(wlen-1):
        conn.SendTML('<HLINE><H-DOWN>')
    conn.SendTML('<HLINE><UR-CORNER><BR>')
    for i in range(6):
        conn.SendTML(f'<CRSRR n={offset}><VLINE>') # <VLINE> <VLINE> <VLINE> <VLINE> <VLINE><BR>')
        for j in range(wlen):
            conn.SendTML(' <VLINE>')
        conn.SendTML('<BR>')
        if i == 5:
            break
        conn.SendTML(f'<CRSRR n={offset}><V-RIGHT>') # <HLINE><CROSS><HLINE><CROSS><HLINE><CROSS><HLINE><CROSS><HLINE><CHR c=179><BR>')
        for j in range(wlen-1):
            conn.SendTML('<HLINE><CROSS>')
        conn.SendTML('<HLINE><V-LEFT><BR>')
    conn.SendTML(f'<CRSRR n={offset}><LL-CORNER>') # <HLINE><CHR c=177><HLINE><CHR c=177><HLINE><CHR c=177><HLINE><CHR c=177><HLINE><CHR c=189>')
    for j in range(wlen-1):
        conn.SendTML('<HLINE><H-UP>')
    conn.SendTML('<HLINE><LR-CORNER><BR>')

    abcoffset = (scwidth-len(string.ascii_uppercase))/2
    conn.SendTML(f'<AT x={abcoffset} y={scheight-2}><GREY3>{string.ascii_uppercase}<BR><RVSON><BACK>Exit<RVSOFF>')

    bulls = []
    cows = []
    bad = []

    t = 0   # Attempt number
    while t<6 and conn.connected:
        # conn.SendTML(f'<GREY3>Attempt #{t}: ')
        # guess = conn.ReceiveStr(bytes(string.ascii_letters,'ascii'),5).lower()
        guess = ''
        line = 6+(t*2)
        column = offset+1
        conn.SendTML(f'<AT x={column} y={line}>{"<GREY3>" if "PET" in conn.mode else "<PURPLE>"}')
        while conn.connected:   # Receive guess word
            keys = conn.encoder.bs + conn.encoder.nl + conn.encoder.back
            if len(guess) < wlen:
                keys += string.ascii_letters
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
            conn.SendTML('<LFILL code=32 row=19>')
            conn.SendTML(f'<AT x={column} y={line}>') # <CRSRR> <CRSRR> <CRSRR> <CRSRR> ')
            for i in range(wlen):
                conn.SendTML(' <CRSRR>')
            continue
        if guess == xword:
            conn.SendTML(f'<NULL><AT x={column} y={line}><LTGREEN>')
            for c in xword:
                conn.SendTML(f'{c.upper()}<CRSRR>')
            conn.SendTML(f'<AT x={(scwidth-19)//2} y=19><WHITE><FLASHON>CONGRATULATIONS !!!<FLASHOFF>')
            break
        else:
            out = ''
            conn.SendTML(f'<NULL><AT x={column} y={line}>')
            # xtemp = xword
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
                    if 'PET' in conn.mode:
                        out += '<GREEN>'
                    else:
                        out += f'<PAPER c={conn.encoder.colors["GREEN"]}><BLACK>'
                    if g in cows:
                        cows.remove(g)
                    if g not in bulls:
                        bulls.append(g)
                elif (g in xword) and (g in chars) and (chars[g] >= 0):
                    if 'PET' in conn.mode:
                        out += '<YELLOW>'
                    else:
                        out += f'<PAPER c={conn.encoder.colors["YELLOW"]}><BLACK>'
                    if (g not in bulls) and (g not in cows):
                        cows.append(g)
                    chars[g] -= 1
                else:
                    if 'PET' not in conn.mode:
                        out += f'<PAPER c={conn.encoder.colors["GREY"]}>'
                    out += '<BLACK>'
                    if g not in bad:
                        bad.append(g)
                out += g.upper()+'<CRSRR>'
            if 'PET' not in conn.mode:
                out += f'<PAPER c={conn.encoder.colors["GREY"]}>'

            # for i,c in enumerate(guess):
            #     if xtemp[i] == c:
            #         out += '<GREEN>'
            #         xtemp = xtemp[:i]+'-'+xtemp[i+1:]  # Replace fully matching character with an invalid one
            #                         # so it doesnt match again if the guess word has repeated characters 
            #     elif c in xtemp:
            #         out += '<YELLOW>'
            #         x = xtemp.find(c)
            #         xtemp = xtemp[:x]+'-'+xtemp[x+1:] # Replace partially matching character so it doesnt match again for repeated characters
            #     else:
            #         out += '<BLACK>'
            #     out += c.upper()+'<CRSRR>'
            #     print(xtemp)
            conn.SendTML(out)
            # Update used characters display
            bulls.sort()
            cows.sort()
            bad.sort()
            conn.SendTML('<BLACK>')
            for c in bad:
                conn.SendTML(f'<AT x={abcoffset+string.ascii_lowercase.index(c)} y={scheight-2}>{c.upper()}')
            conn.SendTML('<GREEN>')
            for c in bulls:
                conn.SendTML(f'<AT x={abcoffset+string.ascii_lowercase.index(c)} y={scheight-2}>{c.upper()}')
            conn.SendTML('<YELLOW>')
            for c in cows:
                conn.SendTML(f'<AT x={abcoffset+string.ascii_lowercase.index(c)} y={scheight-2}>{c.upper()}')
        t += 1
    if t == 6:
        conn.SendTML(f'<AT x={(scwidth-24)//2} y=19><GREY2>Better luck next time...<BR>')
    conn.SendTML('<CURSOR>')
    return(scores[t])