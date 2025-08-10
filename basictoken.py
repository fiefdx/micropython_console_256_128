#! /usr/bin/python

# SPDX-License-Identifier: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Class to represent a token for the BASIC
programming language. A token consists of
three items:

column      Column in which token starts
category    Category of the token
lexeme      Token in string form

"""

from micropython import const
import json


class BASICToken:
    print = None

    """BASICToken categories"""

    EOF             = const(0)   # End of file
    LET             = const(1)   # LET keyword
    LIST            = const(2)   # LIST command
    PRINT           = const(3)   # PRINT command
    RUN             = const(4)   # RUN command
    FOR             = const(5)   # FOR keyword
    NEXT            = const(6)   # NEXT keyword
    IF              = const(7)   # IF keyword
    THEN            = const(8)   # THEN keyword
    ELSE            = const(9)   # ELSE keyword
    ASSIGNOP        = const(10)  # '='
    LEFTPAREN       = const(11)  # '('
    RIGHTPAREN      = const(12)  # ')'
    PLUS            = const(13)  # '+'
    MINUS           = const(14)  # '-'
    TIMES           = const(15)  # '*'
    DIVIDE          = const(16)  # '/'
    NEWLINE         = const(17)  # End of line
    UNSIGNEDINT     = const(18)  # Integer
    NAME            = const(19)  # Identifier that is not a keyword
    EXIT            = const(20)  # Used to quit the interpreter
    DIM             = const(21)  # DIM keyword
    GREATER         = const(22)  # '>'
    LESSER          = const(23)  # '<'
    STEP            = const(24)  # STEP keyword
    GOTO            = const(25)  # GOTO keyword
    GOSUB           = const(26)  # GOSUB keyword
    INPUT           = const(27)  # INPUT keyword
    REM             = const(28)  # REM keyword
    RETURN          = const(29)  # RETURN keyword
    SAVE            = const(30)  # SAVE command
    LOAD            = const(31)  # LOAD command
    NOTEQUAL        = const(32)  # '<>'
    LESSEQUAL       = const(33)  # '<='
    GREATEQUAL      = const(34)  # '>='
    UNSIGNEDFLOAT   = const(35)  # Floating point number
    STRING          = const(36)  # String values
    TO              = const(37)  # TO keyword
    NEW             = const(38)  # NEW command
    EQUAL           = const(39)  # '='
    COMMA           = const(40)  # ','
    STOP            = const(41)  # STOP keyword
    COLON           = const(42)  # ':'
    ON              = const(43)  # ON keyword
    POW             = const(44)  # Power function
    SQR             = const(45)  # Square root function
    ABS             = const(46)  # Absolute value function
    RANDOMIZE       = const(47)  # RANDOMIZE keyword
    RND             = const(48)  # RND keyword
    ATN             = const(49)  # Arctangent function
    COS             = const(50)  # Cosine function
    EXP             = const(51)  # Exponential function
    LOG             = const(52)  # Natural logarithm function
    SIN             = const(53)  # Sine function
    TAN             = const(54)  # Tangent function
    DATA            = const(55)  # DATA keyword
    READ            = const(56)  # READ keyword
    INT             = const(57)  # INT function
    CHR             = const(58)  # CHR$ function
    ASC             = const(59)  # ASC function
    STR             = const(60)  # STR$ function
    MID             = const(61)  # MID$ function
    MODULO          = const(62)  # MODULO operator
    TERNARY         = const(63)  # TERNARY functions
    VAL             = const(64)  # VAL function
    LEN             = const(65)  # LEN function
    UPPER           = const(66)  # UPPER function
    LOWER           = const(67)  # LOWER function
    ROUND           = const(68)  # ROUND function
    MAX             = const(69)  # MAX function
    MIN             = const(70)  # MIN function
    INSTR           = const(71)  # INSTR function
    AND             = const(72)  # AND operator
    OR              = const(73)  # OR operator
    NOT             = const(74)  # NOT operator
    PI              = const(75)  # PI constant
    RNDINT          = const(76)  # RNDINT function
    OPEN            = const(77)  # OPEN keyword
    HASH            = const(78)  # "#"
    CLOSE           = const(79)  # CLOSE keyword
    FSEEK           = const(80)  # FSEEK keyword
    RESTORE         = const(81)  # RESTORE keyword
    APPEND          = const(82)  # APPEND keyword
    OUTPUT          = const(83)  # OUTPUT keyword
    TAB             = const(84)  # TAB function
    SEMICOLON       = const(85)  # SEMICOLON
    LEFT            = const(86)  # LEFT$ function
    RIGHT           = const(87)  # RIGHT$ function

    # Displayable names for each token category
    catnames = ('EOF', 'LET', 'LIST', 'PRINT', 'RUN', 'FOR', 'NEXT', 'IF', 'THEN', 'ELSE',
                'ASSIGNOP', 'LEFTPAREN', 'RIGHTPAREN', 'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'NEWLINE', 'UNSIGNEDINT', 'NAME',
                'EXIT', 'DIM', 'GREATER', 'LESSER', 'STEP', 'GOTO', 'GOSUB', 'INPUT', 'REM', 'RETURN',
                'SAVE', 'LOAD', 'NOTEQUAL', 'LESSEQUAL', 'GREATEQUAL', 'UNSIGNEDFLOAT', 'STRING', 'TO', 'NEW', 'EQUAL',
                'COMMA', 'STOP', 'COLON', 'ON', 'POW', 'SQR', 'ABS', 'RANDOMIZE', 'RND', 'ATN',
                'COS', 'EXP', 'LOG', 'SIN', 'TAN', 'DATA', 'READ', 'INT', 'CHR', 'ASC',
                'STR', 'MID', 'MODULO', 'TERNARY', 'VAL', 'LEN', 'UPPER', 'LOWER', 'ROUND', 'MAX',
                'MIN', 'INSTR', 'AND', 'OR', 'NOT', 'PI', 'RNDINT', 'OPEN', 'HASH', 'CLOSE',
                'FSEEK', 'APPEND', 'OUTPUT', 'RESTORE', 'TAB', 'SEMICOLON', 'LEFT', 'RIGHT')

    smalltokens = {'=': ASSIGNOP, '(': LEFTPAREN, ')': RIGHTPAREN,
                   '+': PLUS, '-': MINUS, '*': TIMES, '/': DIVIDE,
                   '\n': NEWLINE, '<': LESSER,
                   '>': GREATER, '<>': NOTEQUAL,
                   '<=': LESSEQUAL, '>=': GREATEQUAL, ',': COMMA,
                   ':': COLON, '%': MODULO, '!=': NOTEQUAL, '#': HASH,
                   ';': SEMICOLON}


    # Dictionary of BASIC reserved words
    keywords = {'LET': LET, 'LIST': LIST, 'PRINT': PRINT,
                'FOR': FOR, 'RUN': RUN, 'NEXT': NEXT,
                'IF': IF, 'THEN': THEN, 'ELSE': ELSE,
                'EXIT': EXIT, 'DIM': DIM, 'STEP': STEP,
                'GOTO': GOTO, 'GOSUB': GOSUB,
                'INPUT': INPUT, 'REM': REM, 'RETURN': RETURN,
                'SAVE': SAVE, 'LOAD': LOAD, 'NEW': NEW,
                'STOP': STOP, 'TO': TO, 'ON':ON, 'POW': POW,
                'SQR': SQR, 'ABS': ABS,
                'RANDOMIZE': RANDOMIZE, 'RND': RND,
                'ATN': ATN, 'COS': COS, 'EXP': EXP,
                'LOG': LOG, 'SIN': SIN, 'TAN': TAN,
                'DATA': DATA, 'READ': READ, 'INT': INT,
                'CHR$': CHR, 'ASC': ASC, 'STR$': STR,
                'MID$': MID, 'MOD': MODULO,
                'IF$': TERNARY, 'IFF': TERNARY,
                'VAL': VAL, 'LEN': LEN,
                'UPPER$': UPPER, 'LOWER$': LOWER,
                'ROUND': ROUND, 'MAX': MAX, 'MIN': MIN,
                'INSTR': INSTR, 'END': STOP,
                'AND': AND, 'OR': OR, 'NOT': NOT,
                'PI': PI, 'RNDINT': RNDINT, 'OPEN': OPEN,
                'CLOSE': CLOSE, 'FSEEK': FSEEK,
                'APPEND': APPEND, 'OUTPUT':OUTPUT,
                'RESTORE': RESTORE, 'TAB': TAB,
                'LEFT$': LEFT, 'RIGHT$': RIGHT}


    # Functions
    functions = {ABS, ATN, COS, EXP, INT, LOG, POW, RND, SIN, SQR, TAN,
                 CHR, ASC, MID, TERNARY, STR, VAL, LEN, UPPER, LOWER,
                 ROUND, MAX, MIN, INSTR, PI, RNDINT, TAB, LEFT, RIGHT}

    def __init__(self, column, category, lexeme):

        self.column = column      # Column in which token starts
        self.category = category  # Category of the token
        self.lexeme = lexeme      # Token in string form

    def pretty_print(self):
        """Pretty prints the token

        """
        print('Column:', self.column,
              'Category:', self.catnames[self.category],
              'Lexeme:', self.lexeme)

    def print_lexeme(self):
        BASICToken.print(self.lexeme, end=' ')
        
    def __str__(self):
        return json.dumps([self.column, self.category, self.lexeme])
    
    def __repr__(self):
        return self.__str__()
    
    def load(self, s):
        d = json.loads(s)
        self.column = d[0]
        self.category = d[1]
        self.lexeme = d[2]
