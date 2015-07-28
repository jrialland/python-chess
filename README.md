# python-chess

chess3 is a really simple chess engine, written in python, mainly for fun..
It knows all rules and can apply them : castling, en-passant, pawn promotion.

Representation
--------------

chess3 is a board-centric engine, (contrary to my former chess2 engine which was part-centric).
The board state is viewed as a 64-bytes array. Part names follow the standard letter convention, except that
it uses a different letter to distinguish between parts on their initial positions and part that have moved, when necessary.
 (castling only applies if involved parts have stayed on their initial positions)

Then the representation is :

|character| signification
|-------|-----------------------------------------------------------------|
| .   | an empty cell                                                   |
| *   | an empty cell that is a target for en 'en-passant' pawn attack. |
| H or h | rook at initial position                                        |
| R or r | rook that have moved                                            |
| N or n | knight                                                          |
| B or b | bishop                                                          |
| Q or q | queen                                                           |
| P or p | pawn                                                            |
| A or a | king at initial position                                        |
| Z or z | king after it has moved                                         |
---------------------------------------------------------------------------

The initial board state representation is :
```
HNBQABNHPPPPPPPP................................pppppppphnbqabnh
```

Which corresponds to the following chess board :
```
#########
#hnbqabnh  <-- black side
#pppppppp
#........
#........
#........
#........
#PPPPPPPP
#HNBQABNH  <-- white side
```


IA
--

The IA is a basic "negamax", with alpha/beta simplification
By default it searches 4 moves beyond, which takes some time, especially in python :(

it is more compact an understandable that my old 'chess2' engine, that I had written in java some years ago

It plays well enough to beat me ('less-than-average' player), but always looses against fairymax, for example.


How to play
-----------

It uses XBoard. run XBoard (or any XBoard/WinBoard -compatible UI), and choose chess3.py as opponent engine.

You can run :

```sh
xboard -debugMode true -cp -fcp "python chess3.py" -scp "python chess3.py"
```

A typical xboard session : 
```
(XBoard UI)                   (chess3)
xboard
                              tellics say     chess3 engine 0.1
                              tellics say     (c) Julien Rialland, All rights reserved.
new
d2d4
                              move e7e6
                              #########
                              #hnbqabnh
                              #pppp.ppp
                              #....p...
                              #........
                              #...P....
                              #........
                              #PPP.PPPP
                              #HNBQABNH
```
