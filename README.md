# python-chess

[![Build Status](https://travis-ci.org/jrialland/python-chess.svg)](https://travis-ci.org/jrialland/python-chess)

A small chess library in python, and a toy chess engine.

When used as a library, it may help doing some analysis-related tasks

* Parsing a FEN-string

```python
>>> from chess3 import BoardState
>>> board = BoardState.from_FEN('rnbq1rk1/p4pbp/3p1np1/2pP4/Pp2P3/1P4P1/1B3PBP/RN1QK1NR w KQ - 3 11')
>>> print(board.pretty_str(utf=True))
#       +---+---+---+---+---+---+---+---+
#    8. | ♜ | ♞ | ♝ | ♛ |   | ♜ | ♚ |   |
#       +---+---+---+---+---+---+---+---+
#    7. | ♟ |   |   |   |   | ♟ | ♝ | ♟ |
#       +---+---+---+---+---+---+---+---+
#    6. |   |   |   | ♟ |   | ♞ | ♟ |   |
#       +---+---+---+---+---+---+---+---+
#    5. |   |   | ♟ | ♙ |   |   |   |   |
#       +---+---+---+---+---+---+---+---+
#    4. | ♙ | ♟ |   |   | ♙ |   |   |   |
#       +---+---+---+---+---+---+---+---+
#    3. |   | ♙ |   |   |   |   | ♙ |   |
#       +---+---+---+---+---+---+---+---+
#    2. |   | ♗ |   |   |   | ♙ | ♗ | ♙ |
#       +---+---+---+---+---+---+---+---+
#    1. | ♖ | ♘ |   | ♕ | ♔ |   | ♘ | ♖ |
#       +---+---+---+---+---+---+---+---+
#         a.  b.  c.  d.  e.  f.  g.  h.
```

* Listing legal moves
```python
>>> list(board.legal_moves())
[a1a2, a1a3, b1d2, b1c3, b1a3, d1c1, d1d2, d1d3, d1d4, d1c2, d1e2, d1f3, d1g4, d1h5, e1f1, e1e2, e1d2, g1h3, g1f3, g1e2, b2a3, b2c3, b2d4, b2e5, b2f6, b2c1, f2f3, f2f4, g2f3, g2h3, g2f1, h2h3, h2h4, g3g4, a4a5, e4e5]
```

* Applying a move
```python
>>> board = board.apply_move( next(board.legal_moves()) )
>>> print(board)
#########
#rnbq.rz.
#p....pbp
#...p.np.
#..pP....
#Pp..P...
#.P....P.
#RB...PBP
#.N.QA.NH
```

* Computing [Zobrist hash](https://en.wikipedia.org/wiki/Zobrist_hashing)

```python
>>> board.zobrist_hash
13393703368026546567

>>> import struct
>>> struct.pack('>Q', board.zobrist_hash)
b'\xb9\xdf\xfe@\x16,\xe1\x87'
```

Representation
--------------

The board is internally represented as a string. Piece names follow the standard letter convention, except that
it uses different letters for marking king and rooks, in order to detect if castling is legal (castling only applies if the involved pieces have stayed on their initial positions)

Then the representation is :

|character| meaning
|------- |---------------------------------------------------------------- |
| .      | an empty cell                                                   |
| *      | an empty cell that is a target for en 'en-passant' pawn capture.|
| H or h | rook at initial position                                        |
| R or r | rook that have moved                                            |
| N or n | knight                                                          |
| B or b | bishop                                                          |
| Q or q | queen                                                           |
| P or p | pawn                                                            |
| A or a | king at initial position                                        |
| Z or z | king after it has moved (preferred over k)                      |
---------------------------------------------------------------------------

i.e The initial board (at the beginning og the game) representation is `"HNBQABNHPPPPPPPP................................pppppppphnbqabnh"`

"Engine"
--

This is a dumb [negamax](https://en.wikipedia.org/wiki/Negamax)-based best move search with [Alpha/Beta pruning](https://en.wikipedia.org/wiki/Alpha%E2%80%93beta_pruning). search depth is 4, and going deeper would not allow reasonable execution times.

You should definitively use a plain chess engine if you're doing serious things.

You may use it from code :

```python
>>> print(board)
#########
#rnbq.rz.
#p....pbp
#...p.np.
#..pP....
#Pp..P...
#.P....P.
#RB...PBP
#.N.QA.NH
>>> chess3.find_best_move(board)
f6d7
```


How to play
-----------

Supporting the good'ol XBoard protocol, you can run XBoard (or any XBoard/WinBoard -compatible UI, pychess works well too), and choose chess3.py as opponent.

* You can run :

```sh
xboard -cp -fcp "python3 chess3.py" -scp "python3 chess3.py" # or 'python -m chess3' if installed as library
```
and play against it, or type crtl-T to see it play against itself, which is quite disappointing.

* You can also run it directly in a terminal : `./chess3.py`

