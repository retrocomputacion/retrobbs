# Tic-Tac-Toe game
# Based on https://www.geeksforgeeks.org/c/tic-tac-toe-game-in-c/

import random
import time
import itertools

from common.connection import Connection
import common.draw as DD
import common.turbo56k as TT

##################
# Plugin setup
##################
def setup():
    fname = "TICTACTOE"    # UPPERCASE function name for config.ini
    parpairs = []   # config.ini Parameter pairs (name,defaultvalue)
    return(fname,parpairs)



#####################
# Plugin function
#####################
def plugFunction(conn:Connection):

    #######################################################
    # Return True if there's an empty space on the board
    #######################################################
    def movesLeft(board):
        for row in board:
            if ' ' in row:
                return True
        return False


    #####################
    # Evaluate winner
    #####################
    def evaluate(board):
        # Checking for Rows for X or O victory.
        for row in board:
            if row[0] == row[1] == row[2]:
                ...
                if row[0] == 'x':   # player
                    return 10
                elif row[0] == '0':   # opponent
                    return -10

        # Checking for Columns for X or o victory.
        for col in range(3):
            if board[0][col] == board[1][col] == board[2][col]:
                if board[0][col] == 'x':
                    return 10
                elif board[0][col] == '0':
                    return -10

        # Checking for Diagonals for X or O victory.
        if board[0][0] == board[1][1] == board[2][2]:
            if board[0][0] == 'x':
                return 10
            elif board[0][0] == '0':
                return -10

        if board[0][2] == board[1][1] == board[2][0]:
            if board[0][2] == 'x':
                return 10
            elif board[0][2] == '0':
                return -10

        # Else if none of them have won then return 0
        return 0

    ####################################################
    # This is the minimax function. It considers all
    # the possible ways the game can go and returns
    # the value of the board
    ####################################################
    def minimax(board, depth, isMax):
        score = evaluate(board)

        # If Maximizer has won the game return his/her
        # evaluated score
        if score == 10:
            # print(*board, sep='\n')
            # print(score)
            return depth-score

        # If Minimizer has won the game return his/her
        # evaluated score
        if score == -10:
            # print(*board, sep='\n')
            # print(score)
            return score-depth

        # If there are no more moves and no winner then
        # it is a tie
        if movesLeft(board) == False:
            return 0

        # If this maximizer's move
        if isMax:
            best = -1000

            # Traverse all cells
            for i,j in moves:
            # for i in range(3):
            #     for j in range(3):
                    # Check if cell is empty
                    if board[i][j] == ' ':
                        # Make the move
                        board[i][j] = 'x'
                        val = minimax(board.copy(), depth + 1, not isMax)
                        if val > best:
                            best = val
                        # Undo the move
                        board[i][j] = ' '
        # If this minimizer's move
        else:
            best = 1000
            # Traverse all cells
            for i,j in moves:
            # for i in range(3):
            #     for j in range(3):
                    # Check if cell is empty
                    if board[i][j] == ' ':
                        # Make the move
                        board[i][j] = '0'
                        # Call minimax recursively and choose
                        val = minimax(board.copy(), depth + 1, not isMax)
                        if val < best:
                            best = val
                        # Undo the move
                        board[i][j] = ' '
        # print(*board, sep='\n')
        # print(best)
        return best

    ############################################################
    # This will return the best possible move for the player
    ############################################################
    def findBestMove(board):
        bestVal = -1000
        # Artificial delay
        if gfxok:
            conn.SendTML('<CLR>')
        else:
            conn.SendTML('<AT x=0 y=23>')
        conn.SendTML('<LTBLUE>Computer is thinking...<PAUSE n=2><DEL n=23>')
        # Traverse all cells, evaluate minimax function for
        # all empty cells. And return the cell with optimal
        # value.
        # for i in range(3):
        #     for j in range(3):
        for i,j in moves:
                # Check if cell is empty
                if board[i][j] == ' ':
                    # Make the move
                    board[i][j] = 'x'

                    # compute evaluation function for this
                    # move.
                    moveVal = abs(minimax(board.copy(), 0, False))
                    # print(*board, sep='\n')
                    # print(moveVal)

                    # Undo the move
                    board[i][j] = ' '

                    # If the value of the current move is
                    # more than the best value, then update
                    # best/
                    if moveVal > bestVal:
                        bestMove = (i,j)
                        bestVal = moveVal
        return bestMove

    def showBoard(board):
        if gfxok:
            conn.SendTML(f'<SCNCLR><CLR><PENCOLOR pen=1 color={pen}><LINE x1={(scwidth//2)-20} y1=30 x2={(scwidth//2)-20} y2=150>')
            conn.SendTML(f'<LINE x1={(scwidth//2)+20} y1=30 x2={(scwidth//2)+20} y2=150>')
            conn.SendTML(f'<LINE x1={(scwidth//2)-60} y1=71 x2={(scwidth//2)+60} y2=71>')
            conn.SendTML(f'<LINE x1={(scwidth//2)-60} y1=111 x2={(scwidth//2)+60} y2=111><PENCOLOR pen=1 color={pen}>')
            for i in range(3):
                DD.vectorText(conn,1,(i*40)+(scwidth//2)-46,20,0,12,f'{i+1}')
            DD.vectorText(conn,1,(scwidth//2)-70,44,0,12,'A')
            DD.vectorText(conn,1,(scwidth//2)-70,84,0,12,'B')
            DD.vectorText(conn,1,(scwidth//2)-70,124,0,12,'C')
        else:
            conn.SendTML('<CLR><CRSRD n=5><WHITE><CRSRR n=12>1 2 3<BR>')
            for row in range(3):
                conn.SendTML(f'<CRSRR n=10><CHR c={65+row}> ')
                for col in range(3):
                    conn.SendTML('<PINK>x' if board[row][col] == 'x' else '<BLUE>o' if board[row][col] == '0' else ' ')
                    if col < 2:
                        conn.SendTML('<WHITE><VLINE>')
                if row < 2:
                    conn.SendTML('<BR><CRSRR n=12><WHITE><HLINE><CROSS><HLINE><CROSS><HLINE><BR>')
            conn.SendTML('<BR>')


    def updateBoard(row,col,side):
        if gfxok:
            if side:
                drawX(row,col)
            else:
                drawO(row,col)
        else:
            conn.SendTML(f'<AT x={12+(col*2)} y={6+(row*2)}>')
            conn.SendTML('<PINK>x' if side else '<BLUE>o')

    def drawX(row,col):
        x = (col*40)+(scwidth//2)-40
        y = (row*40)+50
        conn.SendTML(f'<PENCOLOR pen=1 color ={exs}><LINE pen=1 x1={x-13} y1={y-13} x2={x+13} y2={y+13}><LINE pen=1 x1={x-13} y1={y+13} x2={x+13} y2={y-13}>')
    
    def drawO(row,col):
        x = (col*40)+(scwidth//2)-40
        y = (row*40)+50
        conn.SendTML(f'<PENCOLOR pen=1 color ={os}><CIRCLE pen=1 x={x} y={y} rx=13 ry=13>')

    ### Main ###

    # Check host capabilities
    flist = [TT.SCNCLR,TT.LINE,TT.CIRCLE]

    gfxok = True

    for f in flist:
        if conn.QueryFeature(f) >= 0x80:
            gfxok = False
            break

    moves=list(set(itertools.combinations_with_replacement(range(3),2))|set(itertools.combinations_with_replacement(range(2,-1,-1),2)))

    # Start screen
    border = conn.encoder.colors.get("BLACK",0)
    if gfxok:
        if 'MSX' in conn.mode:
            scwidth = 256
            scheight = 192
        elif 'PET' in conn.mode:
            scwidth = 320
            scheight = 200
        pen = conn.encoder.colors.get("WHITE",0)
        exs = conn.encoder.colors.get("PINK",0)
        os = conn.encoder.colors.get("LTBLUE",0)

        conn.SendTML(f'<SPLIT row={conn.encoder.txt_geo[1]-1} multi=False bgtop={border} bgbottom={border} mode={conn.mode}><PENCOLOR pen=1 color=2><SCNCLR><PENCOLOR pen=1 color={pen}><CLR>')
        DD.vectorText(conn,1,(scwidth//2)-74,80,0,20,"TIC-TAC-TOE")
        drawX(0,1)
        drawX(2,0)
        drawX(2,2)
        drawO(0,0)
        drawO(0,2)
        drawO(2,1)
        conn.SendTML(f'<CLR><WHITE>Press RETURN to play<INKEYS>')
    else:
        conn.SendTML(f'<CLR><AT x={(conn.encoder.txt_geo[0]//2)-5} y=5><YELLOW>TIC-TAC-TOE<BR><BR><BR><WHITE><FLASHON>Press RETURN to play<FLASHOFF><INKEYS>')


    # Main loop
    while True:
        # Initially, the board is empty
        board = [[' ']*3 for i in range(3)]
        random.seed(time.time())
        # Shuffle the moves
        random.shuffle(moves)
        moveIndex = 0
        showBoard(board)
        whoseMove = random.randrange(2) == 1   # False : Computer - True : Human
        if gfxok:
            conn.SendTML('<CLR>')
        else:
            conn.SendTML('<AT x=0 y=23>')
        if whoseMove:
            conn.SendTML('You start...<PAUSE n=2>')
        else:
            conn.SendTML('Computer starts...<PAUSE n=2>')

        # Game loop
        while evaluate(board) == 0 and moveIndex != 9:
            if not whoseMove:
                thisMove = findBestMove(board.copy())
                board[thisMove[0]][thisMove[1]] = '0'
                updateBoard(thisMove[0],thisMove[1],whoseMove)
                moveIndex += 1
                whoseMove = True
            else:
                if gfxok:
                    conn.SendTML('<CLR>')
                else:
                    conn.SendTML('<AT x=0 y=23>')
                conn.SendTML('<YELLOW>Enter move: ')
                while True:
                    row = conn.ReceiveKey(['a','b','c',conn.encoder.back])
                    if row == conn.encoder.back:
                        conn.SendTML(f'<NUL n=2><SPLIT bgbottom={border} mode="_C.mode"><TEXT>')
                        return
                    conn.Sendall(row)
                    row = ord(row)-ord('a')
                    col = conn.ReceiveKey(['1','2','3',conn.encoder.bs])
                    if col != conn.encoder.bs:
                        conn.Sendall(col)
                        col = int(col)-1
                        if board[row][col] != ' ':
                            conn.SendTML('<DEL n=2>Invalid move!<PAUSE n=1><DEL n=13>')
                            continue
                        board[row][col] = 'x'
                        moveIndex += 1
                        conn.SendTML('<DEL n=2>')
                        updateBoard(row,col,whoseMove)
                        # if evaluate(board) != 0:
                        #     break
                            # conn.SendTML('<CLR> YOU WIN!<PAUSE n=2>')
                            # conn.SendTML(f'<NUL n=2><SPLIT bgbottom={border} mode="_C.mode"><TEXT>')
                            # return
                        whoseMove = False
                        break
                    else:
                        conn.SendTML('<DEL>')
        score = evaluate(board)
        if score == 0 and moveIndex == 9:
            conn.SendTML('<CLR> IS A DRAW!<PAUSE n=2>')
        else:
            if score > 0:
                conn.SendTML('<CLR> YOU WIN!<PAUSE n=2>')
            else:
                conn.SendTML('<CLR> COMPUTER WINS!<PAUSE n=2>')
        conn.SendTML('<CLR><KPROMPT t=A>Again or <KPROMPT t=_BACK>Exit')
        c = conn.ReceiveKey(['a',conn.encoder.back])
        if c == conn.encoder.back:
            break
    conn.SendTML(f'<NUL n=2><SPLIT bgbottom={conn.encoder.colors.get("BLACK",0)} mode="_C.mode"><TEXT>')



