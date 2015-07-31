#!/usr/bin/env python
# -*- coding:utf-8 -*-

import logging
import sys
import re
import random
from multiprocessing import Pool, cpu_count

TEAM_WHITES = 1
TEAM_BLACKS = -1
ROOK_DIRECTIONS = [(1, 0), (-1, 0), (0, -1), (0, 1)]
BISHOP_DIRECTIONS = [(-1, 1), (1, 1), (1, -1), (-1, -1)]
QUEEN_DIRECTIONS = ROOK_DIRECTIONS + BISHOP_DIRECTIONS
KNIGHT_MOVES = [
    (-2, -1), (-1, -2), (1, -2), (2, -1), (2, 1), (1, 2), (-1, 2), (-2, 1)]
KING_MOVES = [
    (-1, 0), (-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1)]
CHECK = 1
CHECKMATE = 2


def to_pos(i, j):
    """Convert a coordinate (with 0,0 at bottom left) on the board to the standard representation

       >>> to_pos(0,0)
       'a1'
       >>> to_pos(3,3)
       'd4'
    """
    return 'abcdefgh'[i] + str(j + 1)


def to_coord(pos):
    """Convert a position on the board (standard letter+number representation) to a coordinate

       >>> to_coord('a1')
       (0,0)
       >>> to_coord('g8')
       (6,7)
    """
    return 'abcdefgh'.index(pos[0]), int(pos[1]) - 1


def on_board(i, j):
    """Return True if the location is on board

       >>> on_board(0,0)
       True
       >>> on_board(-1,17)
       False
    """
    return 0 <= i < 8 and 0 <= j < 8


def opponent(team):
    """Given a team, return the opponent team.
       >>>opponent(TEAM_WHITES)
       -1  #=TEAM_BLACKS
       >>>opponent(TEAM_BLACKS)
       1  #=TEAM_WHITES
       >>>opponent(0)
       0
    """
    return -team


class Move:

    """represent a player's action"""

    def __init__(self, _from, to, promotion=None, enpassant=None, castling=False):
        self._from = _from
        self.to = to
        self.promotion = promotion
        self.enpassant = enpassant
        self.castling = castling

    def to_xboard_notation(self):
        m = to_pos(*self._from) + to_pos(*self.to)
        if self.promotion:
            m += self.promotion.lower()
        return m

    def __str__(self):
        s = str(self._from) + ' -> ' + str(self.to)
        attrs = []
        if self.promotion:
            attrs.append('promotion=' + str(self.promotion))
        if self.castling:
            attrs.append('castling=true')
        if self.enpassant:
            attrs.append('enpassant=' + str(self.enpassant))
        if attrs:
            s += ' [' + ', '.join(attrs) + ']'
        return s


class BoardState:

    def __init__(self, repr=list('HNBQABNH' + 'P' * 8 + '.' * 32 + 'p' * 8 + 'hnbqabnh'), enpassant_cell=None):
        self._repr = repr
        self.enpassant_cell = enpassant_cell

    def get_part(self, i, j):
        return state[j * 8 + i]

    def is_occupied(self, i, j):
        return self._repr[j * 8 + i] != '.'

    def is_same_team(self, i, j, team):
        possibleparts = 'PRHNBQAZ' if team == TEAM_WHITES else 'prhnbqaz'
        return self._repr[j * 8 + i] in possibleparts

    def get_team(self, i, j):
        p = self._repr[j * 8 + i]
        if p == '.':
            return 0
        elif p in 'PRHNBQAZ':
            return TEAM_WHITES
        else:
            return TEAM_BLACKS

    def is_opponent_team(self, i, j, team):
        return self.is_same_team(i, j, opponent(team))

    def is_rook(self, i, j, team):
        parts = 'RH' if team == TEAM_WHITES else 'rh'
        return self._repr[j * 8 + i] in parts

    def is_knight(self, i, j, team):
        part = 'N' if team == TEAM_WHITES else 'n'
        return self._repr[j * 8 + i] == part

    def is_bishop(self, i, j, team):
        part = 'B' if team == TEAM_WHITES else 'b'
        return self._repr[j * 8 + i] == part

    def is_queen(self, i, j, team):
        part = 'Q' if team == TEAM_WHITES else 'q'
        return self._repr[j * 8 + i] == part

    def is_king(self, i, j, team):
        parts = 'AZ' if team == TEAM_WHITES else 'az'
        return self._repr[j * 8 + i] in parts

    def is_pawn(self, i, j, team):
        part = 'P' if team == TEAM_WHITES else 'p'
        return self._repr[j * 8 + i] == part

    def is_under_attack(self, i, j, team=None):
        if team is None:
            team = self.get_team(i, j)
        opponent_team = team * -1
        # attacks from knights
        for di, dj in KNIGHT_MOVES:
            x, y = i + di, j + dj
            if on_board(x, y) and self.is_knight(x, y, opponent_team):
                return True

        # attacks from pawns
        y = j + team
        for x in [i - 1, i + 1]:
            if on_board(x, y) and self.is_pawn(x, y, opponent_team):
                return True

        # attack from axis (rooks,queens)
        searched = 'RHQ' if opponent_team == TEAM_WHITES else 'rhq'
        if self._explore_threat(i, j, team, ROOK_DIRECTIONS, searched):
            return True

        # attack from diagonals (bishops,queens)
        searched = 'BQ' if opponent_team == TEAM_WHITES else 'bq'
        if self._explore_threat(i, j, team, BISHOP_DIRECTIONS, searched):
            return True

        # attack from kings
        for di, dj in KING_MOVES:
            x, y = i + di, j + dj
            if on_board(x, y) and self.is_king(x, y, opponent_team):
                return True

        return False

    def find_king(self, team):
        parts = 'AZ' if team == TEAM_WHITES else 'az'
        for p in range(64):
            if self._repr[p] in parts:
                return p % 8, p / 8
        return None

    def legal_moves(self, team):
        for j in range(8):
            for i in range(8):
                if self.get_team(i, j) == team:
                    for move in self._moves(i, j, team):
                        board = self.apply_move(move, team)
                        kingpos = board.find_king(team)
                        # avoid to emit moves that would lead to the king being
                        # under attack
                        if kingpos and not board.is_under_attack(*kingpos):
                            yield move

    def _moves(self, i, j, team):
        opponent_team = opponent(team)
        if self.is_rook(i, j, team):
            for m in self._explore_moves(i, j, ROOK_DIRECTIONS, team):
                yield m
        elif self.is_bishop(i, j, team):
            for m in self._explore_moves(i, j, BISHOP_DIRECTIONS, team):
                yield m
        elif self.is_queen(i, j, team):
            for m in self._explore_moves(i, j, QUEEN_DIRECTIONS, team):
                yield m
        elif self.is_knight(i, j, team):
            for di, dj in KNIGHT_MOVES:
                x, y = i + di, j + dj
                if on_board(x, y) and self.get_team(x, y) in [0, opponent_team]:
                    yield Move((i, j), (x, y))
        elif self.is_pawn(i, j, team):
            y = j + team
            # normal move (i.e not capturing)
            if 0 <= y < 8 and self.get_team(i, y) == 0:
                if y in [0, 7]:  # pawn promotion
                    possibleproms = 'NBRQ' if team == TEAM_WHITES else 'nbrq'
                    for p in possibleproms:
                        yield Move((i, j), (i, y), promotion=p)
                else:  # normal case
                    yield Move((i, j), (i, y))

                # initial 2-cells move
                if (j == 1 and team == TEAM_WHITES) or (j == 6 and team == TEAM_BLACKS):
                    row = 3 if team == TEAM_WHITES else 4
                    if self.get_team(i, row) == 0:
                        yield Move((i, j), (i, row), enpassant=(i, y))

            # pawn captures opponent
            for x in [i - 1, i + 1]:
                if on_board(x, y) and (self.get_team(x, y) == opponent_team or (x, y) == self.enpassant_cell):
                    if y in [0, 7]:  # pawn promotion
                        possibleproms = 'NBRQ' if team == TEAM_WHITES else 'nbrq'
                        for p in possibleproms:
                            yield Move((i, j), (x, y), promotion=p)
                    else:
                        yield Move(_from=(i, j), to=(x, y))
        elif self.is_king(i, j, team):
            for di, dj in KING_MOVES:
                x, y = i + di, j + dj
                if on_board(x, y) and self.get_team(x, y) != team:
                    yield Move((i, j), (x, y))
        # castling
        if (i, j) in [(4, 0), (4, 7)]:
            row = 0 if team == TEAM_WHITES else 7
            # left side
            if self._is_castling_possible(team, (4, row), (0, row), [(1, row), (2, row), (3, row)]):
                yield Move(_from=(4, row), to=(2, row), castling=True)
            # right side
            if self._is_castling_possible(team, (4, row), (7, row), [(5, row), (6, row)]):
                yield Move(_from=(4, row), to=(6, row), castling=True)

    def _is_castling_possible(self, team, king_pos, rook_pos, empty_pos):
        expected = 'AH' + '.' * len(empty_pos)
        if team == TEAM_BLACKS:
            expected = expected.lower()
        state = ''.join(
            map(lambda pos: self.part_at(*pos), [king_pos, rook_pos] + empty_pos))
        if state != expected:
            return False
        for pos in [king_pos, rook_pos] + empty_pos:
            if self.is_under_attack(*pos, team=team):
                return False
        return True

    def _explore_threat(self, i, j, team, directions, searched):
        """ for a set of directions provided for a 'slider' part, returns true if a part of that kind is attacking the current position"""
        for di, dj in directions:
            x, y, go = i + di, j + dj, True
            while go:
                go = False
                if on_board(x, y):
                    if self.get_team(x, y) == 0:
                        go = True
                    elif self._repr[y * 8 + x] in searched:
                        return True
                    x += di
                    y += dj
        return False

    def _explore_moves(self, i, j, directions, team):
        for di, dj in directions:
            x, y, go = i + di, j + dj, True
            while go:
                go = False
                if on_board(x, y):
                    cellteam = self.get_team(x, y)
                    if cellteam != team:
                        yield Move((i, j), (x, y))
                    if cellteam == 0:
                        go = True
                    x += di
                    y += dj

    def part_at(self, i, j):
        """Returns the content of the board at this position"""
        return self._repr[j * 8 + i]

    def is_check(self, team):
        """Returns 0 if not check, 1 if check, 2 if checkmate"""
        i, j = self.find_king(team)
        if self.is_under_attack(i, j, team):
            return CHECKMATE if len(list(self.legal_moves(team))) == 0 else CHECK
        return 0

    def apply_move(self, move, team, check_legal=False):
        """modifies the board by applying the move. As BoarState instances are immutable, returns a new instance of BoardState"""
        part = self.part_at(*move._from)
        if check_legal:
            checked = False
            for lm in self.legal_moves(team):
                if lm._from == move._from and lm.to == move.to:
                    checked = True
                    break
            if not checked:
                raise Exception('Illegal move')

        r = self._repr[::]
        i, j = move._from

        # castling
        row = 0 if team == TEAM_WHITES else 7
        if part in 'Aa' and move._from == (4, row):
            if move.to == (2, row) and self._is_castling_possible(team, (4, row), (0, row), [(1, row), (2, row), (3, row)]):
                r[row * 8] = '.'
                r[row * 8 + 3] = 'R' if team == TEAM_WHITES else 'r'
            elif move.to == (6, row) and self._is_castling_possible(team, (4, row), (7, row), [(5, row), (6, row)]):
                r[row * 8 + 7] = '.'
                r[row * 8 + 5] = 'R' if team == TEAM_WHITES else 'r'

        r[j * 8 + i] = '.'  # remove part from original position

        # change rook symbol after first move (prevent castling afterwards)
        if part in 'Hh':
            part = {'H': 'R', 'h': 'r'}[part]
        # change king symbol after first move (prevent castling afterwards)
        elif part in 'Aa':
            part = {'A': 'Z', 'a': 'z'}[part]

        x, y = move.to
        # move to target position
        r[y * 8 + x] = part if not(move.promotion) else move.promotion

        # enpassant rules
        if part in 'Pp':
            # when a pawn make a 2-cells move, remember that the cell behind it
            # is weak for 1 turn
            if abs(j - y) == 2:
                enpassant_row = 2 if team == TEAM_WHITES else 5
                enpassant_cell = (i, enpassant_row)
                return BoardState(repr=r, enpassant_cell=enpassant_cell)

            # a pawn has the right to take the enpassant cell
            if self.enpassant_cell == (x, y):
                pawnrow = 3 if team == TEAM_BLACKS else 4
                r[pawnrow * 8 + x] = '.'

        return BoardState(repr=r)

    def score(self, team):
        """Evaluates the material on the board. the scores for each part are just the ones from Claude Shannon's paper"""
        s, names = ('PBNHRQpbnhrqAZaz.' if team == TEAM_WHITES else 'pbnhrqPBNHRQAZaz.'), [
            1, 3, 3, 5, 5, 9, -1, -3, -3, -5, -5, -9, 0, 0, 0, 0, 0]
        values = dict(zip(s, names))
        score = sum([values[x] for x in self._repr])
        return score

    def count_controlled_cells(self, team):
        count = 0
        opp = opponent(team)
        for i in range(8):
            for j in range(8):
                if not self.is_same_team(i, j, team):
                    if self.is_under_attack(i, j, opp):
                        count += 1
        return count

    def cells_under_attack(self, team):
        for i in range(8):
            for j in range(8):
                if self.is_same_team(i, j, team) and self.is_under_attack(i, j, team):
                    yield i, j

    def __str__(self):
        return '#' * 9 + '\n' + '\n'.join(['#' + ''.join(self._repr[i:i + 8]) for i in range(56, -1, -8)])

    def pretty_str(self, comment=True, unicode=False):
        rep = ''.join(self._repr).replace('a', 'k').replace('A', 'K').replace('z', 'k').replace(
            'Z', 'K').replace('h', 'r').replace('H', 'R').replace('.', ' ')
        if unicode:
            tr = dict(zip('prnbqkPRNBQK', '♟♜♞♝♛♚♙♖♘♗♕♔'))
            rep = ''.join([tr[c] if c in tr else c for c in rep])
        sep = '   ' + '+---' * 8 + '+'
        s = [sep]
        for l in [str(1 + i / 8) + '. | ' + ' | '.join(list(rep[i:i + 8])) + ' |' for i in range(56, -1, -8)]:
            s += [l, sep]
        s += ['     ' + '.  '.join('abcdefgh') + '.']
        if comment:
            return '#    ' + '\n#    '.join(s)
        else:
            return '\n'.join(s)

    def to_FEN(self, team=TEAM_WHITES, halfmoves=0, moves=1):
        """Convert to the standard FEN representation"""
        fen = ''
        for j in range(7, -1, -1):
            fen += self._repr[j * 8:j * 8 + 8] + '/'
        fen = fen[:-1]
        fen = re.sub('a|z', 'k', fen)
        fen = re.sub('A|Z', 'K', fen)
        fen = re.sub('h', 'r', fen)
        fen = re.sub('H', 'R', fen)
        for j in range(8, 0, -1):
            fen = fen.replace(j * '.', str(j))
        fen += ' ' + ['b', 'w'][team == TEAM_WHITES]
        castlings = ''
        if self._repr[4] == 'A':
            if self._repr[7] == 'H':
                castlings += 'K'
            if self._repr[0] == 'H':
                castlings += 'Q'
        if self._repr[60] == 'a':
            if self._repr[63] == 'h':
                castlings += 'k'
            if self._repr[56] == 'h':
                castlings += 'q'
        if castlings == '':
            fen += ' -'
        else:
            fen += ' ' + castlings
        if self.enpassant_cell is None:
            fen += ' -'
        else:
            fen += ' ' + to_pos(*self.enpassant_cell)
        fen += ' ' + str(halfmoves) + ' ' + str(moves)
        return fen

    @classmethod
    def from_FEN(clazz, fen):
        positions, turn, castlings, enpassant, halfmoves, moves = fen.strip().split(
            ' ')
        rep = ''.join(positions.split('/')[::-1])
        for i in range(1, 9):
            rep = rep.replace(str(i), i * '.')
        rep = rep.replace('k', 'z')
        rep = rep.replace('K', 'Z')
        rep = list(rep)
        if 'K' in castlings:
            rep[4] = 'A'
            rep[7] = 'H'
        if 'Q' in castlings:
            rep[4] = 'A'
            rep[0] = 'H'
        if 'k' in castlings:
            rep[60] = 'a'
            rep[63] = 'h'
        if 'q' in castlings:
            rep[60] = 'a'
            rep[56] = 'h'
        board = BoardState(repr=rep, enpassant_cell=None if enpassant == '-' else to_coord(enpassant))
        team = [TEAM_BLACKS, TEAM_WHITES][turn == 'w']
        return board, team

    @classmethod
    def from_repr(clazz, repr):
        """parses a board representation, returning a BoardState instance"""
        repr = [x for x in repr if x in '.PpRHrhNnBbQqAZaz']
        if len(repr) != 64:
            raise Exception('incorrect syntax in board representation')
        else:
            repr = [repr[i:i + 8] for i in range(56, -1, -8)]
            return BoardState(repr=repr)


def negamax_alphabeta(board, team, a=-sys.maxint, b=sys.maxint, depth=3):
    if depth == 0:
        return board.score(team)
    else:
        bestscore, bestmove = -sys.maxint, None
        for childmove in board.legal_moves(team):
            score = - \
                negamax_alphabeta(
                    board.apply_move(childmove, team), opponent(team), -b, -a, depth - 1)
            if score > bestscore:
                bestscore = score
                if bestscore > a:
                    a = bestscore
                    if a >= b:
                        return bestscore
        return bestscore


def _eval_move(args):
    board, move, team = args
    boardafter = board.apply_move(move, team)
    score = -negamax_alphabeta(boardafter, opponent(team))
    return score, move, boardafter


def find_best_move(process_pool, board, my_team):
    """scan the best possible move for my_team, using minimax."""
    
    moves = process_pool.map(_eval_move, [(board, m, my_team) for m in board.legal_moves(my_team)])
    #moves = map(_eval_move, [(board, m, my_team) for m in board.legal_moves(my_team)])
    
    boardsafter = {move: boardafter for score, move, boardafter in moves}

    if len(moves) > 0:
        opponent_team = opponent(my_team)
        maxscore, maxmove, boardafter = max(moves, key=lambda x: x[0])
        if len(moves) > 1:
            kept = [
                move for score, move, boardafter in moves if score == maxscore]

            # always prefer the one that put the opponent in check
            for move in kept:
                boardafter = boardsafter[move]
                if boardafter.is_check(opponent_team):
                    return move

            # if there is still a choice to make, choose any
            return random.choice(kept)
        return maxmove
    else:
        return None


def _play(board, my_team, process_pool, history=[], respond=lambda x: sys.stdout.write(x + '\n')):
    mymove = find_best_move(process_pool, board, my_team)
    playing_now = my_team
    if mymove:
        respond('move ' + mymove.to_xboard_notation())
        history.append(board)
        board = board.apply_move(mymove, playing_now)
        respond(board.pretty_str(comment=True))
        playing_now = opponent(my_team)
        check = board.is_check(playing_now)
        if check == CHECK:
            respond('#check')
        elif check == CHECKMATE:
            respond('#checkmate')
            respond('result ' + ['0-1', '1-0']
                    [playing_now == TEAM_WHITES] + ' {checkmate}')
        else:
            if len(list(board.legal_moves(playing_now))) == 0:
                respond('result 1/2-1/2 {stallmate}')
    else:
        if board.is_check(my_team):
            respond('resign')
        else:
            respond('result 1/2-1/2 {stallmate}')
    return board, playing_now


def xboard_game(input=sys.stdin, output=sys.stdout):
    """plays through the xboard protocol.
       most infos found at http://home.hccnet.nl/h.g.muller/interfacing.txt
    """
    def respond(cmd):
        logging.debug('<< ' + cmd)
        output.write(cmd + '\n')
        output.flush()

    process_pool = Pool(cpu_count())

    board = BoardState()
    playing_now = TEAM_WHITES
    my_team = TEAM_BLACKS

    force_mode = False
    history = []

    if output.isatty():
        respond(
            "#Howdy, type 'new' to start a new game, or 'help' to list supported commands")

    while True:

        line = input.readline()
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
            respond("tellics say     chess3 engine 0.1")
            respond(
                "tellics say     (c) Julien Rialland, All rights reserved.")

        # tells your engine to setup the board for a new game, and consider
        # itself playing the side that will not move first, simply awaiting
        # events idly. This means it will start searching and doing a move of
        # its own after it receives an input move.
        elif cmd == 'new':
            board = BoardState()
            history = []
            playing_now = TEAM_WHITES
            my_team = TEAM_BLACKS
            respond(board.pretty_str(comment=True))

        elif cmd == 'protover 2':
            respond('feature myname="Julien\'s chess3 0.1"')
            respond('feature ping=1')
            respond('feature sigint=0')
            respond('feature sigterm=0')
            respond('feature setboard=1')
            respond('feature debug=1')
            respond('feature done=1')

        elif cmd.startswith('ping'):
            n = cmd.split(' ')[-1]
            respond('pong ' + n)

        elif cmd.startswith('setboard'):
            fen = cmd[9:].strip()
            board, playing_now = BoardState.from_FEN(fen)

        elif cmd == 'force':  # accept moves and just update the board
            force_mode = True

        elif cmd == 'go':  # start playing
            # tells the engine to start playing for the side that now has the move (regardless of what it was doing before),
            # and keep spontaneously generating moves for that side each thime
            # that side has to move again.
            force_mode = False
            my_team = playing_now
            board, playing_now = _play(
                board, my_team, process_pool, history, respond)

        elif cmd == 'undo':
            if len(history) > 0:
                board = history[-1]
                history = history[:-1]
                playing_now = opponent(playing_now)
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
            respond('#MY_TEAM : ' + ['black', 'white'][my_team == TEAM_WHITES])
            respond(
                '#PLAYING : ' + ['black', 'white'][playing_now == TEAM_WHITES])

        elif cmd == 'fen':
            respond(
                board.to_FEN(team=playing_now, halfmoves=0, moves=len(history)))

        elif cmd == 'white':
            my_team = TEAM_WHITES
            respond('#Playing white')

        elif cmd == 'black':
            my_team = TEAM_BLACKS
            respond('#Playing black')

        elif cmd == 'quit':
            return

        elif cmd.startswith('accepted ') or cmd.startswith('time ') or cmd.startswith('otim'):
            # silently ignore some commands
            pass

        else:
            if re.match('^[a-h][1-8][a-h][1-8].?$', cmd):
                # receive a move from the opponent
                move = Move(to_coord(cmd[0:2]), to_coord(cmd[2:4]))
                opponent_team = opponent(my_team)
                playing_now = opponent_team

                # detect pawn promotions
                if len(cmd) == 5:
                    move.promotion = cmd[-1]
                    if playing_now == TEAM_WHITES:
                        move.promotion = move.promotion.upper()

                # update the board
                history.append(board)
                try:
                    board = board.apply_move(move, playing_now, check_legal=True)
                except Exception:
                    respond('illegal move: ' + cmd)
                    continue

                playing_now = my_team
                # evaluate what to play
                if not force_mode:
                    board, playing_now = _play(
                        board, my_team, process_pool, history, respond)
            else:
                respond("#ignored command : '" + cmd + "'")


#b = BoardState()
#for m in b.legal_moves(TEAM_WHITES):
#    print m
    
if __name__ == '__main__':
    # logging.basicConfig(
    #    filename=re.sub('py$', 'log', sys.argv[0]), level=logging.DEBUG)
    xboard_game()
