import json
import urllib.request
from random import randrange,shuffle
import re

from common import turbo56k as TT
from common.style import bbsstyle, RenderMenuTitle
from common import filetools as FT
from common.helpers import formatX, crop, text_displayer
from common.connection import Connection
from common.bbsdebug import _LOG


##################
# Plugin setup
##################
def setup():
    fname = "WORDFIT"
    parpairs = []
    return(fname,parpairs)

##############################
# Plugin callable function
##############################
def plugFunction(conn:Connection):
# def plugFunction(conn):

    rep = 0
    data = None
    while True:
        try:
            # Brute random date, just retry if invalid date
            with urllib.request.urlopen(f'https://raw.githubusercontent.com/doshea/nyt_crosswords/master/{randrange(1976,2017)}/{randrange(1,12):02d}/{randrange(1,31):02d}.json') as url:
                data = json.loads(url.read().decode())
                if data != None:
                    # TODO: check if there's enough words for a game set
                    break
        except:
            rep += 1
            if rep > 3:
                conn.SendTML('<CLR><RED>ERROR - Could not fetch data<BR><PAUSE n=4>')
                return
    
    if data != None:
        words = data['answers']['across']+data['answers']['down']
        clues = data['clues']['across']+data['answers']['down']
        # Reformat clue string
        clues = [i.split('.')[1:] for i in clues]
        clues = ['.'.join(i)[1:] for i in clues]
        # Remove clues and words that may reference to other words
        t_clues = []
        t_words = []
        for i,c in enumerate(clues):
            if (not any(char.isdigit() for char in c)) and len(c) > 0:
                t_clues.append(c)
                t_words.append(words[i])
        clues = t_clues
        words = t_words
        
        # Game Loop
        while True:
            # Generate game set
            game = {'words':[],'clues':[],'soup':[]}
            order = list(range(len(clues)))
            shuffle(order)
            for i in range(6):
                game['words'].append(words[order[i]])
                game['clues'].append(clues[order[i]])
                w = list(words[order[i]].lower())
                shuffle(w)
                game['soup'].append(w)
            score = 0
            parms = {}
            conn.SendTML(conn.templates.GetTemplate('wordfit/title',**parms))
            conn.SendTML('<AT x=0 y=10><WHITE><FORMAT>Solve each of the six clues by typing the available characters in the correct order.</FORMAT>')
            conn.SendTML('<FORMAT>You have ten lives, and lose one each time you type the incorrect character.')
            conn.SendTML('<BR><BR><GREEN><FLASHON>PRESS -RETURN- TO START<FLASHOFF><BR><BR><BACK> to exit')
            if conn.ReceiveKey([conn.encoder.nl,conn.encoder.back]) == conn.encoder.back:
                return
            lives = 10
            for i in range(6):
                secret = '-'*len(game['words'][i])
                soup = game['soup'][i]
                t_soup = ''.join(soup).upper()
                soup = [s.lower() for s in soup]
                pos = 0
                parms = {'secret':list(secret), 'clue':game['clues'][i], 'soup':None, 'lives':lives, 'count':i, 'redraw':True}
                conn.SendTML(conn.templates.GetTemplate('wordfit/gamefield',**parms))
                while True:
                    parms = {'secret':list(secret), 'clue':None, 'soup':t_soup, 'lives':None, 'count':i, 'redraw':False}
                    conn.SendTML(conn.templates.GetTemplate('wordfit/gamefield',**parms))
                    if len(soup) == 0:
                        conn.SendTML('<BELL><PAUSE n=2>')
                        break
                    k = conn.ReceiveKey(soup+[conn.encoder.back])
                    if k == conn.encoder.back:
                        return
                    if k.upper() != game['words'][i][pos]:    # Wrong order
                        lives -= 1
                        parms = {'secret':None, 'clue':None, 'soup':None, 'lives':lives, 'count':i, 'redraw':False}
                        conn.SendTML(conn.templates.GetTemplate('wordfit/gamefield',**parms))
                        score -= 50/len(secret)
                        if lives == 0:
                            break
                    else:
                        score += 100/len(secret)
                        secret = secret[0:pos]+k.upper()+secret[pos+1:]   # Build answer
                        pos += 1
                        t_soup = t_soup.replace(k.upper(),'-',1)         # Remove char from soup display
                        for c in range(len(soup)):                      # Remove char from soup list
                            if soup[c] == k:
                                soup.pop(c)
                                break
                if lives == 0:
                    break
            ### Game completed or lost
            if lives > 0:
                conn.SendTML('<CLR><BR><BR><GREEN>CONGRATULATIONS!!!')
                conn.SendTML(f'<BR><BR><YELLOW>Your score: <WHITE>{int(score)}/600<PAUSE n=3>')
            else:
                conn.SendTML('<CLR><BR><BR><RED>GAME OVER...<PAUSE n=3>')