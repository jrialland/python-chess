# -*- coding:utf-8 -*-
import sys
import re
import os

import chess3
from chess3 import *

def xboard_play(board, process_pool, history=[], respond=lambda x: sys.stdout.write(x + '\n')):
    mymove = find_best_move(board, process_pool)
    if mymove:
        respond('move ' + mymove.to_xboard_notation())
        history.append(board)
        board = board.apply_move(mymove)
        respond(board.pretty_str(comment=True))
        check = board.is_check()
        if check == CHECK:
            respond('#check')
        elif check == CHECKMATE:
            respond('#checkmate')
            respond('#result : ' + ['whites win', 'blacks win']
                    [board.team == TEAM_WHITES] + ' {checkmate}')
        else:
            if len(list(board.legal_moves())) == 0:
                respond('#result : draw {stalemate}')
    else:
        if board.is_check():
            respond('resign')
        else:
            respond('#result : draw {stalemate}')
    return board


def xboard_game(command_reader=lambda: input(), output=sys.stdout):
    """plays through the xboard protocol.
       most infos found at http://home.hccnet.nl/h.g.muller/interfacing.txt
    """
    def respond(cmd, comment=False):
        logging.debug('<< ' + cmd)
        output.write(('#' if comment else '') + cmd + '\n')
        output.flush()

    process_pool = None
    # try:
    #    c = cpu_count()
    #    logging.debug('cpu count : %d' % c)
    #    process_pool = Pool(c)
    # except:
    #    logging.debug('process pool is unavailable')
    #    pass
    board = BoardState()
    force_mode = False
    history = []

    if output.isatty():
        respond(
            "#Howdy, type 'new' to start a new game, or 'help' to list supported commands")

    while True:
        try:
            line = command_reader()
        except IOError:
            print('#got IOError')
            continue

        cmd = line.strip()
        logging.debug(">> " + cmd)
        if cmd == 'help':
            respond("""

chess3 supported XBoard commands:
---------------------------------

new			: Starts a new game
setboard <FEN string>	: Setup the board to the given state
force			: Following moves are applied to the board, without playing
go			: Make the engine play next move
undo			: Clears the last half-move
remove			: Clears the last move
show			: Displays the board
fen			: Displays the board in FEN format (non-standard command)
white			: Assign the engine to White
black			: Assign the engine to Black
<MOVE>			: Applies the move in algebric notation (i.e 'd2d4')
quit			: Exits


""")
        elif cmd == 'xboard':
            respond("tellics say     chess3 engine " + chess3.__version__)
            respond(
                "tellics say     (c) Julien Rialland, All rights reserved.")
        # tells your engine to setup the board for a new game, and consider
        # itself playing the side that will not move first, simply awaiting
        # events idly. This means it will start searching and doing a move of
        # its own after it receives an input move.

        elif cmd == 'new':
            board = BoardState()
            history = []
            force_mode = False
            respond(board.pretty_str(comment=True))

        elif cmd == 'protover 2':
            respond('feature myname="Julien\'s chess3 ' + chess3.__version__)
            respond('feature ping=1')
            respond('feature san=0')
            respond('feature sigint=0')
            respond('feature sigterm=0')
            respond('feature setboard=1')
            respond('feature debug=1')
            respond('feature time=0')
            respond('feature done=1')

        elif cmd.startswith('ping'):
            n = cmd.split(' ')[-1]
            respond('pong ' + n)

        elif cmd.startswith('setboard'):
            fen = cmd[9:].strip()
            board = BoardState.from_FEN(fen)

        elif cmd == 'force':  # accept moves and just update the board
            force_mode = True

        elif cmd == 'go':  # start playing
            # tells the engine to start playing for the side that now has the move (regardless of what it was doing before),
            # and keep spontaneously generating moves for that side each thime
            # that side has to move again.
            force_mode = False
            board = xboard_play(board, process_pool, history, respond)

        elif cmd == 'undo':
            if len(history) > 0:
                board = history[-1]
                history = history[:-1]
            else:
                respond('#nothing to undo')

        elif cmd == 'remove':
            if len(history) > 1:
                board = history[-2]
                history = history[:-2]
            else:
                respond('#nothing to remove')

        # not part of xboard protocol, only for debugging purposes
        elif cmd == 'show':
            respond(board.pretty_str())
            respond('# : ' + ['black', 'white']
                    [opponen(board.team) == TEAM_WHITES] + ' to play')
        elif cmd == 'fen':
            respond(board.to_FEN())

        elif cmd == 'quit':
            return
        elif cmd in ('white', 'black'):
            board.trait = cmd[0]
        else:
            if re.match('^[a-h][1-8][a-h][1-8].?$', cmd):
                move = Move(to_coord(cmd[0:2]), to_coord(cmd[2:4]))
                # detect pawn promotions
                if len(cmd) == 5:
                    move.promotion = cmd[-1]
                    if board.team == TEAM_WHITES:
                        move.promotion = move.promotion.upper()
            else:
                move = board.find_move_from_san(cmd)
            # received a move from the opponent
            if move:
                try:
                    board = board.apply_move(move, check_legal=True)
                    # update the board
                    history.append(board)
                    # prompt user
                    respond('# you (' + team_str(opponent(board.team)) +
                            ') moved : ' + str(move))
                except Exception:
                    logging.exception('illegal move: ' + cmd)
                    respond('illegal move: ' + cmd)
                    continue
                # evaluate what to play
                if not force_mode:
                    board = xboard_play(board, process_pool, history, respond)
            else:
                respond("#ignored command : '" + cmd + "'")


if __name__ == '__main__':
    if '--debug' in sys.argv:
        logging.basicConfig(level=logging.DEBUG)
    bookfile = './Most_played_2mlj_base.bin'
    if os.path.exists(bookfile):
        openingsBook.read(bookfile)
    else:
        pass
        # logging.warn('# openings book ' + bookfile + ' not found !')
    xboard_game()
