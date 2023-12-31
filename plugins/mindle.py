import random
import string
from tinydb import Query, where
from datetime import datetime

from common.connection import Connection
from common.bbsdebug import _LOG
from common.style import KeyLabel

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

    dbase = conn.bbs.database
    table = dbase.db
    dbQ = Query()
    today = datetime.today().timetuple().tm_yday
    dificulty = datetime.today().weekday()
    xwords = []
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

    if conn.mode == 'PET264':
        scolor = 49
    else:
        scolor = 11

    conn.SendTML(f'<TEXT border={scolor} background={scolor}><CLR>')
    conn.SendTML('<WHITE>  <BOTTOM-HASH n=11><GREEN><CHR c=172> <CHR c=172><LTGREEN><CHR c=172>     <CHR c=187><CHR c=187> <YELLOW><CHR c=162> <WHITE><BOTTOM-HASH n=11><BR>')
    conn.SendTML('<GREY3>   <BOTTOM-HASH n=10><GREEN><RVSON><CHR c=161><RVSOFF><CBM-B><RVSON><CHR c=187><RVSOFF><LTGREEN><CHR c=172> <RVSON><CHR c=172><RVSOFF><CBM-B><CHR c=172><RVSON><CHR c=162><RVSOFF><CHR c=161><CHR c=161><YELLOW><RVSON><CHR c=161><RVSOFF><CHR c=162><CHR c=161><GREY3><BOTTOM-HASH n=10><BR>')
    conn.SendTML('<GREY2>    <BOTTOM-HASH n=9><GREEN><RVSON><CHR c=161><CRSRR><CHR c=161><LTGREEN><CHR c=161><RVSOFF><CHR c=187><CHR c=161><RVSON><CHR c=161><RVSOFF><CHR c=188><CHR c=162><CHR c=161><RVSON><CHR c=188><RVSOFF><YELLOW><CHR c=188><CHR c=162><CHR c=187><GREY2><BOTTOM-HASH n=9><BR>')
    while conn.connected:
        keys = b'_BCD'
        conn.SendTML('<AT x=10 y=8>')
        if (conn.userclass != 0) and (conn.userid not in players):
            KeyLabel(conn,'a','Play daily Mindle',True)
            keys += b'A'
        conn.SendTML('<BR><CRSRR n=10>')
        KeyLabel(conn,'b','Free play',False)
        conn.SendTML('<BR><CRSRR n=10>')
        KeyLabel(conn,'c','View High Scores',True)
        conn.SendTML('<BR><CRSRR n=10>')
        KeyLabel(conn,'d','How to play',False)
        conn.SendTML('<BR><CRSRR n=10>')
        KeyLabel(conn,'_','Exit',True)
        rec = conn.ReceiveKey(keys)
        if rec == b'B':     ##### Free play
            conn.SendTML('<WINDOW top=3 bottom=24><CLR><WINDOW>')
            xwords = [] # Include _all_ words for free play
            for wl in wordlist:
                xwords +=wordlist[wl]
            xword = xwords[random.randrange(0,len(xwords))].lower()
            xvalid = [] # Get the valid words for this xword lenght
            with open(f"plugins/mindle_words/valid{str(len(xword))}.txt",'r') as wf:
                xvalid = wf.read().splitlines()
                xvalid += [word for word in xwords if len(word)== len(xword)]
            mindle(conn, xword, xvalid)
            conn.SendTML('<PAUSE n=5><WINDOW top=3 bottom=24><CLR><WINDOW>')
        elif rec == b'C':   # High scores
            if len(tops) > 0:
                conn.SendTML('<WINDOW top=3 bottom=24><CLR><WINDOW>')
                conn.SendTML('<AT x=15 y=7><LTGREEN>Top Scores<GREY3><BR><BR>')
                ulist = dict(dbase.getUsers())
                j = len(tops) if len(tops)<=10 else 10
                for i in range(j):
                    uname = ulist[int(tops[i][0])]
                    conn.SendTML(f'<CRSRR n=10>{uname}<CRSRR n={17-len(uname)}>{tops[i][1]}<BR>')
                conn.SendTML('<AT x=7 y=23><GREEN>Press any key to continue')
                conn.Receive(1)
                conn.SendTML('<WINDOW top=3 bottom=24><CLR><WINDOW>')
        elif rec == b'D':
            conn.SendTML('<WINDOW top=3 bottom=24><CLR><WINDOW>')
            conn.SendTML('<AT y=5><GREY3>Instructions: You have to guess the<BR> hidden word, you have 6 tries.<BR>Each try must be a valid word.<BR><BR>')
            conn.SendTML('After each try the color of the<BR> characters will change color to show<BR> how close you are from guessing the<BR> correct word.<BR>')
            conn.SendTML('<BR><GREEN> * <GREY3>Green means the character exists in<BR>   the hidden word and is in the<BR>   correct position<BR>')
            conn.SendTML('<YELLOW> * <GREY3>Yellow means the character exists in<BR>   the hidden word but is in the wrong<BR>   position<BR>')
            conn.SendTML("<BLACK> * <GREY3>Black means the character is not<BR>   present in the hidden word<BR>")
            conn.SendTML('<BR>       Press any key to continue')
            conn.Receive(1)
            conn.SendTML('<WINDOW top=3 bottom=24><CLR><WINDOW>')
        elif rec == b'A':       ##### Daily Mindle
            conn.SendTML('<WINDOW top=3 bottom=24><CLR><WINDOW>')
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
            conn.SendTML('<WINDOW top=3 bottom=24><CLR><WINDOW>')
        else:
            break


###################################
# Main game
###################################
def mindle(conn:Connection, xword: str, valid):

    scores = [500,400,200,100,50,25,0]
    #_LOG('Mindle - word to guess: '+xword,id=conn.id, v=4)

    wlen = len(xword)  # Word lenght
    offset = (38-(wlen+2))//2
    if wlen == 6:
        offset -= 1 # Center playfield

    # Draw playfield
    conn.SendTML(f'<AT x={offset} y=5><CURSOR enable=False><LTBLUE><CHR c=176>')   # <HLINE><CHR c=178><HLINE><CHR c=178><HLINE><CHR c=178><HLINE><CHR c=178><HLINE><CHR c=174><BR>')
    for j in range(wlen-1):
        conn.SendTML('<HLINE><CHR c=178>')
    conn.SendTML('<HLINE><CHR c=174><BR>')
    for i in range(6):
        conn.SendTML(f'<CRSRR n={offset}><VLINE>') # <VLINE> <VLINE> <VLINE> <VLINE> <VLINE><BR>')
        for j in range(wlen):
            conn.SendTML(' <VLINE>')
        conn.SendTML('<BR>')
        if i == 5:
            break
        conn.SendTML(f'<CRSRR n={offset}><CHR c=171>') # <HLINE><CROSS><HLINE><CROSS><HLINE><CROSS><HLINE><CROSS><HLINE><CHR c=179><BR>')
        for j in range(wlen-1):
            conn.SendTML('<HLINE><CROSS>')
        conn.SendTML('<HLINE><CHR c=179><BR>')
    conn.SendTML(f'<CRSRR n={offset}><CHR c=173>') # <HLINE><CHR c=177><HLINE><CHR c=177><HLINE><CHR c=177><HLINE><CHR c=177><HLINE><CHR c=189>')
    for j in range(wlen-1):
        conn.SendTML('<HLINE><CHR c=177>')
    conn.SendTML('<HLINE><CHR c=189><BR>')

    conn.SendTML(f'<AT x=7 y=23><GREY3>{string.ascii_uppercase}<BR><RVSON><LARROW>Exit<RVSOFF>')

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
        conn.SendTML(f'<AT x={column} y={line}><GREY3>')
        while conn.connected:   # Receive guess word
            keys = bytes(conn.encoder.bs + conn.encoder.nl,'ascii')+b'_'
            if len(guess) < wlen:
                keys += bytes(string.ascii_letters,'ascii')
            rec = conn.ReceiveKey(keys)
            if rec == b'_': # Quit game
                return -1*(t+1)
            if (len(guess) == wlen) and (rec == bytes(conn.encoder.nl,'ascii')):   # A 5 letter word has been received and return/enter pressed
                break
            elif (len(guess) != 0) and (rec == bytes(conn.encoder.bs,'ascii')): # Backspace/delete
                conn.SendTML('<CRSRL n=2> <CRSRL>')
                guess = guess[:-1]
            elif chr(rec[0]) in string.ascii_letters:
                conn.SendTML(f'{chr(rec[0]).upper()}<CRSRR>')
                guess += chr(rec[0])
        conn.SendTML('<BR>')
        guess = guess.lower()
        if guess not in valid:
            conn.SendTML('<AT x=6 y=19><GREY2>NOT A VALID WORD, try again...<BR><PAUSE n=2>')
            conn.SendTML('<LFILL code=32 row=19>')
            conn.SendTML(f'<AT x={column} y={line}>') # <CRSRR> <CRSRR> <CRSRR> <CRSRR> ')
            for i in range(wlen):
                conn.SendTML(' <CRSRR>')
            continue
        if guess == xword:
            conn.SendTML(f'<AT x={column} y={line}><LTGREEN>')
            for c in xword:
                conn.SendTML(f'{c.upper()}<CRSRR>')
            conn.SendTML(f'<AT x=11 y=19><WHITE><FLASHON>CONGRATULATIONS !!!<FLASHOFF>')
            break
        else:
            out = ''
            conn.SendTML(f'<AT x={column} y={line}>')
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
                    out += '<GREEN>'
                    if g in cows:
                        cows.remove(g)
                    if g not in bulls:
                        bulls.append(g)
                elif (g in xword) and (g in chars) and (chars[g] >= 0):
                    out += '<YELLOW>'
                    if (g not in bulls) and (g not in cows):
                        cows.append(g)
                    chars[g] -= 1
                else:
                    out += '<BLACK>'
                    if g not in bad:
                        bad.append(g)
                out += g.upper()+'<CRSRR>'

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
                conn.SendTML(f'<AT x={7+string.ascii_lowercase.index(c)} y=23>{c.upper()}')
            conn.SendTML('<GREEN>')
            for c in bulls:
                conn.SendTML(f'<AT x={7+string.ascii_lowercase.index(c)} y=23>{c.upper()}')
            conn.SendTML('<YELLOW>')
            for c in cows:
                conn.SendTML(f'<AT x={7+string.ascii_lowercase.index(c)} y=23>{c.upper()}')
        t += 1
    if t == 6:
        conn.SendTML('<AT x=6 y=19><GREY2>Better luck next time...<BR><PAUSE n=5>')
    conn.SendTML('<CURSOR>')
    return(scores[t])