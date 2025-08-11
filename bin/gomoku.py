import os
import gc
import sys
import time
import random
from math import ceil
from io import StringIO

from shell import Shell
from scheduler import Condition, Message
from common import exists, path_join, isfile, isdir, ticks_ms

coroutine = True


class Game(object):
    def __init__(self, think_games = 100, mode = "2Ps"):
        self.white = 70
        self.black = 71
        self.empty = 72
        self.table = [[self.empty for x in range(15)] for y in range(15)]
        self.turn = self.black
        self.discs_counter = 0
        self.over = False
        self.win = self.empty
        self.think_games = think_games
        self.think_use_time = 0
        self.mode = mode
        self.cx = 7
        self.cy = 7
        self.think = {self.black: 0, self.white: 0, self.empty: 0}
        self.stats = {self.black: 0, self.white: 0, self.empty: 0}
        self.g = None

    def is_full(self):
        return self.discs_counter >= 256

    def available_place(self, x, y):
        return self.table[y][x] == self.empty

    def place_disc(self, x, y, color):
        if self.available_place(x, y):
            self.table[y][x] = color
            self.discs_counter += 1
            return True
        return False

    def move_cursor(self, key):
        dx = 0
        dy = 0
        if key == "LT":
            dx = -1
        elif key == "RT":
            dx = 1
        elif key == "UP":
            dy = -1
        elif key == "DN":
            dy = 1
        self.cx += dx
        if self.cx <= 0:
            self.cx = 0
        elif self.cx >= 14:
            self.cx = 14
        self.cy += dy
        if self.cy <= 0:
            self.cy = 0
        elif self.cy >= 14:
            self.cy = 14

    def is_line5(self, v1, v2, v3, v4, v5):
        return v1 != self.empty and v1 == v2 == v3 == v4 == v5

    def check_status(self, x, y):
        directions = [
            (1, 0),  # vertical
            (0, 1),  # horizontal
            (1, 1),  # diagonal \
            (1, -1), # diagonal /
        ]
        color = self.table[y][x]
        for dx, dy in directions:
            count = 1
            # Check one direction
            i = 1
            while 0 <= x + dx*i < 15 and 0 <= y + dy*i < 15 and self.table[y + dy*i][x + dx*i] == color:
                count += 1
                i += 1
            # Check the opposite direction
            i = 1
            while 0 <= x - dx*i < 15 and 0 <= y - dy*i < 15 and self.table[y - dy*i][x - dx*i] == color:
                count += 1
                i += 1
            if count >= 5:
                return color
        return self.empty

    def turn_place_disc(self, x, y):
        if self.place_disc(x, y, self.turn):
            if self.turn == self.black:
                self.turn = self.white
            else:
                self.turn = self.black
            win = self.check_status(x, y)
            if win != self.empty:
                self.over = True
                self.win = win
                self.stats[self.win] += 1
            if self.is_full():
                if not self.over:
                    self.over = True
                    self.win = self.empty
                    self.stats[self.win] += 1
            return True
        return False

    def near_first_disc(self):
        directions = [
            (1, 0),  # vertical
            (0, 1),  # horizontal
            (1, 1),  # diagonal \
            (1, -1), # diagonal /
        ]
        places = []
        for y in range(15):
            for x in range(15):
                p = self.table[y][x]
                if p != self.empty:
                    for dx, dy in directions:
                        if self.table[y + dy][x + dx] == self.empty:
                            places.append([y + dy, x + dx])
                        if self.table[y - dy][x - dx] == self.empty:
                            places.append([y - dy, x - dx])
                    return random.choice(places)

    def place_score(self, x, y, color):
        directions = [
            (1, 0),  # vertical
            (0, 1),  # horizontal
            (1, 1),  # diagonal \
            (1, -1), # diagonal /
        ]
        values = {5: 1000000, 42: 200000, 4: 25000, 32: 5000, 3: 5000, 2: 1000, 1: 200}
        flags = {}
        score = 0
        for dx, dy in directions:
            count = 1
            sides = 0
            # Check one direction
            i = 1
            while 0 <= x + dx*i < 15 and 0 <= y + dy*i < 15 and self.table[y + dy*i][x + dx*i] == color:
                count += 1
                i += 1
            if 0 <= x + dx*i < 15 and 0 <= y + dy*i < 15 and self.table[y + dy*i][x + dx*i] == self.empty:
                sides += 1
            # Check the opposite direction
            i = 1
            while 0 <= x - dx*i < 15 and 0 <= y - dy*i < 15 and self.table[y - dy*i][x - dx*i] == color:
                count += 1
                i += 1
            if 0 <= x - dx*i < 15 and 0 <= y - dy*i < 15 and self.table[y - dy*i][x - dx*i] == self.empty:
                sides += 1
            if count >= 5:
                count = 5
                if count in flags:
                    flags[count] += 1
                else:
                    flags[count] = 1
                score += values[count]
            else:
                if sides > 0:
                    if count == 4 and sides == 2:
                        count = 42
                    if count == 3 and sides == 2:
                        count = 32
                    if count in flags:
                        flags[count] += 1
                    else:
                        flags[count] = 1
                    score += values[count]
        if (32 in flags and (4 in flags or 42 in flags)) or (4 in flags and flags[4] > 1):
            score = 200000
        return score

    def turn_random_place_disc(self):
        opponent = self.black if self.turn == self.white else self.white
        t = ticks_ms()
        moves = [[] for i in range(5)]
        scores = [-1 for i in range(5)]
        for y in range(15):
            for x in range(15):
                p = self.table[y][x]
                if p == self.empty:
                    score = self.place_score(x, y, opponent)
                    if score >= 200000:
                        score = 1000000
                    min_score = min(scores)
                    if score > min_score:
                        i = scores.index(min_score)
                        scores[i] = score
                        moves[i] = [x, y]
                    score = self.place_score(x, y, self.turn)
                    min_score = min(scores)
                    if score > min_score:
                        i = scores.index(min_score)
                        scores[i] = score
                        moves[i] = [x, y]
        count = 0
        for s in scores:
            if s >= 0:
                count += 1
        x, y = random.choice(moves[:count])
        return self.turn_place_disc(x, y)

    def choose_best_move_sim(self):
        opponent = self.black if self.turn == self.white else self.white
        t = ticks_ms()
        if self.discs_counter < 1:
            return 7, 7
        elif self.discs_counter < 2:
            return self.near_first_disc()
        moves = [[] for i in range(10)]
        scores = [-1 for i in range(10)]
        max_score = -1
        best_x = 0
        best_y = 0
        for y in range(15):
            for x in range(15):
                p = self.table[y][x]
                if p == self.empty:
                    score = self.place_score(x, y, opponent)
                    if score >= 200000:
                        max_score = 1000000
                        score = 1000000
                        best_x = x
                        best_y = y
                    min_score = min(scores)
                    if score > min_score:
                        i = scores.index(min_score)
                        scores[i] = score
                        moves[i] = [x, y]
                    score = self.place_score(x, y, self.turn)
                    min_score = min(scores)
                    if score > min_score:
                        i = scores.index(min_score)
                        scores[i] = score
                        moves[i] = [x, y]
                    if score > max_score:
                        max_score = score
                        best_x = x
                        best_y = y
        stats = {}
        i = 0
        max_win = -1
        best_i = 0
        for p in range(len(moves)):
            s = scores[p]
            if s >= 0:
                x, y = moves[p]
                stats[i] = {self.black: 0, self.white: 0, self.empty: 0}
                for j in range(self.think_games):
                    self.g.copy_from(self)
                    self.g.turn_place_disc(x, y)
                    while not self.g.over:
                        self.g.turn_random_place_disc()
                    stats[i][self.g.win] += 1
                if stats[i][self.turn] > max_win:
                    max_win = stats[i][self.turn]
                    best_x = x
                    best_y = y
                    best_i = i
            else:
                break
            i += 1
        self.think[self.black] = stats[best_i][self.black]
        self.think[self.white] = stats[best_i][self.white]
        self.think[self.empty] = stats[best_i][self.empty]
        self.think_use_time = (ticks_ms() - t) / 1000.0
        return best_x, best_y

    def choose_best_move(self):
        opponent = self.black if self.turn == self.white else self.white
        t = ticks_ms()
        if self.discs_counter < 1:
            return 7, 7
        elif self.discs_counter < 2:
            return self.near_first_disc()
        win_moves = []
        offensive_moves = [[] for i in range(10)]
        offensive_scores = [-1 for i in range(10)]
        defensive_moves = [[] for i in range(10)]
        defensive_scores = [-1 for i in range(10)]
        max_score = -1
        best_x = 0
        best_y = 0
        for y in range(15):
            for x in range(15):
                p = self.table[y][x]
                if p == self.empty:
                    score = self.place_score(x, y, opponent)
                    min_score = min(defensive_scores)
                    if score > min_score:
                        i = defensive_scores.index(min_score)
                        defensive_scores[i] = score
                        defensive_moves[i] = [x, y]
                    score = self.place_score(x, y, self.turn)
                    if score >= 1000000:
                        win_moves.append([x, y])
                    else:
                        min_score = min(offensive_scores)
                        if score > min_score:
                            i = offensive_scores.index(min_score)
                            offensive_scores[i] = score
                            offensive_moves[i] = [x, y]
        if len(win_moves) > 0:
            best_x, best_y = win_moves[0]
        else:
            max_defensive_score = max(defensive_scores)
            i_defensive = defensive_scores.index(max_defensive_score)
            max_offensive_score = max(offensive_scores)
            i_offensive = offensive_scores.index(max_offensive_score)
            if max_defensive_score >= 200000 and max_defensive_score > max_offensive_score:
                moves = []
                for i, score in enumerate(defensive_scores):
                    if score == max_defensive_score:
                        moves.append(defensive_moves[i])
                best_x, best_y = random.choice(moves)
            else:
                moves = []
                for i, score in enumerate(offensive_scores):
                    if score == max_offensive_score:
                        moves.append(offensive_moves[i])
                best_x, best_y = random.choice(moves)
        self.think_use_time = (ticks_ms() - t) / 1000.0
        return best_x, best_y

    def restart(self):
        self.turn = self.black
        self.discs_counter = 0
        self.table = [[self.empty for x in range(15)] for y in range(15)]
        self.over = False
        self.win = self.empty
        self.think[self.black] = 0
        self.think[self.white] = 0
        self.think[self.empty] = 0
        self.think_use_time = 0

    def release(self):
        del self.table

    def copy_from(self, game):
        self.turn = game.turn
        self.discs_counter = game.discs_counter
        self.table = [list(row) for row in game.table]
        self.over = game.over
        self.win = game.win

    def get_frame(self):
        offset_x = 9
        offset_y = 5
        lines = []
        for i in range(15):
            lines.append([offset_x + 3 + i * 8, offset_y, offset_x + 3 + i * 8, 123, True])
            lines.append([offset_x, offset_y + 3 + i * 8, offset_x + 118, offset_y + 3 + i * 8, True])
        turn = "-turn"
        if self.mode == "black" and self.turn == self.white:
            turn = "-thinking"
        elif self.mode == "white" and self.turn == self.black:
            turn = "-thinking"
        black_info = {"s": "P1(black)" + (turn if self.turn == self.black else "         "), "c": " ", "x": 136, "y": 25}
        white_info = {"s": "P2(white)" + (turn if self.turn == self.white else "         "), "c": " ", "x": 136, "y": 33}
        if self.over:
            if self.win == self.black:
                black_info["s"] = "P1(black)-WIN     "
            elif self.win == self.white:
                white_info["s"] = "P2(white)-WIN     "
            else:
                black_info["s"] = "P1(black)-TIE     "
                white_info["s"] = "P2(white)-TIE     "
        texts = [{"s": "Status", "c": " ", "x": 172, "y": 10},
                 black_info,
                 white_info,
                 {"s": "black won: %d  " % self.stats[self.black], "c": " ", "x": 136, "y": 41},
                 {"s": "white won: %d  " % self.stats[self.white], "c": " ", "x": 136, "y": 49},
                 {"s": "tie:       %d  " % self.stats[self.empty], "c": " ", "x": 136, "y": 57},
                 {"s": "Think", "c": " ", "x": 175, "y": 75},
                 {"s": "time:  %.3fs   " % self.think_use_time, "c": " ", "x": 136, "y": 90},]
                 # {"s": "black: %d/%d  " % (self.think[self.black], self.think_games), "c": " ", "x": 136, "y": 98},
                 # {"s": "white: %d/%d  " % (self.think[self.white], self.think_games), "c": " ", "x": 136, "y": 106},
                 # {"s": "tie:   %d/%d  " % (self.think[self.empty], self.think_games), "c": " ", "x": 136, "y": 114},]
        cursor = [int(offset_x + self.cx * 8), int(offset_y + self.cy * 8), 7, 7]
        rects = [[8, 4, 121, 121],
                 [5, 1, 246, 127],
                 [131, 4, 117, 63],
                 [131, 4, 117, 18],
                 [131, 69, 117, 56],
                 [131, 69, 117, 18]]
        return {
            "render": (("rects", "rects"), ("lines", "lines"), ("tiles", "tiles"), ("texts", "texts"), ("pointer", "rects")),
            "tiles": {
                "data": self.table,
                "width": 15,
                "height": 15,
                "size_w": 8,
                "size_h": 8,
                "offset_x": 9,
                "offset_y": 5,
            },
            "lines": lines,
            "rects": rects,
            "texts": texts,
            "pointer": [cursor]
        }
        


def main(*args, **kwargs):
    task = args[0]
    name = args[1]
    shell = kwargs["shell"]
    shell_id = kwargs["shell_id"]
    display_id = shell.display_id
    cursor_id = shell.cursor_id
    shell.disable_output = True
    shell.enable_cursor = False
    shell.scheduler.keyboard.scan_rows = 5
    tiles = [
        {"id": 70, "body": {
            "tile": [
                0b00111000,
                0b01000100,
                0b10000010,
                0b10000010,
                0b10000010,
                0b01000100,
                0b00111000],
            "width": 7, "height": 7
        }},
        {"id": 71, "body": {
            "tile": [
                0b00111000,
                0b01111100,
                0b11111110,
                0b11111110,
                0b11111110,
                0b01111100,
                0b00111000],
            "width": 7, "height": 7
        }},
        {"id": 72, "body": {
            "tile": [
                0b00010000,
                0b00010000,
                0b00010000,
                0b11111110,
                0b00010000,
                0b00010000,
                0b00010000],
            "width": 7, "height": 7
        }},
    ]
    try:
        game_mode = "2Ps"
        think_games = 51
        if len(kwargs["args"]) >= 0:
            if len(kwargs["args"]) > 0:
                if kwargs["args"][0] == "1":
                    game_mode = "black"
                else:
                    game_mode = "white"
            if len(kwargs["args"]) > 1:
                think_games = int(kwargs["args"][1])
            offset_x = 97
            offset_y = 7
            width = 10
            height = 20
            size = 6
            frame_interval = 30
            yield Condition.get().load(sleep = 0, send_msgs = [
                Message.get().load({"clear": True}, receiver = display_id)
            ])
            yield Condition.get().load(sleep = 0, send_msgs = [
                Message.get().load({"update_tiles": tiles}, receiver = display_id)
            ])
            yield Condition.get().load(sleep = 0, send_msgs = [
                Message.get().load({"enabled": False}, receiver = cursor_id)
            ])
            game = Game(think_games, game_mode)
            game.g = Game()
            yield Condition.get().load(sleep = frame_interval, wait_msg = False, send_msgs = [
                Message.get().load(game.get_frame(), receiver = display_id)
            ])
            if game_mode == "white":
                x, y = game.choose_best_move()
                game.turn_place_disc(x, y)
                yield Condition.get().load(sleep = frame_interval, wait_msg = False, send_msgs = [
                    Message.get().load(game.get_frame(), receiver = display_id)
                ])
            
            c = None
            msg = task.get_message()
            if msg:
                c = msg.content["msg"]
                msg.release()
            while c != "ES":
                if not game.over:
                    if c == "BA":
                        if game_mode == "2Ps" or (game_mode == "black" and game.turn == game.black) or (game_mode == "white" and game.turn == game.white):
                            game.turn_place_disc(game.cx, game.cy)
                            yield Condition.get().load(sleep = frame_interval, wait_msg = False, send_msgs = [
                                Message.get().load(game.get_frame(), receiver = display_id)
                            ])
                            if not game.over and (game_mode == "black" or game_mode == "white"):
                                x, y = game.choose_best_move()
                                game.turn_place_disc(x, y)
                                yield Condition.get().load(sleep = frame_interval, wait_msg = False, send_msgs = [
                                    Message.get().load(game.get_frame(), receiver = display_id)
                                ])
                    elif c == "c":
                        x, y = game.choose_best_move()
                        game.turn_place_disc(x, y)
                        yield Condition.get().load(sleep = frame_interval, wait_msg = False, send_msgs = [
                            Message.get().load(game.get_frame(), receiver = display_id)
                        ])
                if c in ["LT", "RT", "UP", "DN"]:
                    game.move_cursor(c)
                    yield Condition.get().load(sleep = frame_interval, wait_msg = False, send_msgs = [
                        Message.get().load(game.get_frame(), receiver = display_id)
                    ])
                elif c == "r":
                    game.restart()
                    yield Condition.get().load(sleep = frame_interval, wait_msg = False, send_msgs = [
                        Message.get().load(game.get_frame(), receiver = display_id)
                    ])
                    if game_mode == "white":
                        x, y = game.choose_best_move()
                        game.turn_place_disc(x, y)
                        yield Condition.get().load(sleep = frame_interval, wait_msg = False, send_msgs = [
                            Message.get().load(game.get_frame(), receiver = display_id)
                        ])
                msg = task.get_message()
                if msg:
                    c = msg.content["msg"]
                    msg.release()
                else:
                    c = None
                yield Condition.get().load(sleep = 0)
        else:
            yield Condition.get().load(sleep = 0, send_msgs = [
                Message.get().load({"output": "invalid parameters"}, receiver = shell_id)
            ])
        yield Condition.get().load(sleep = 0, send_msgs = [
            Message.get().load({"clear": True}, receiver = display_id)
        ])
        yield Condition.get().load(sleep = 0, send_msgs = [
            Message.get().load({"enabled": True}, receiver = cursor_id)
        ])
        shell.disable_output = False
        shell.enable_cursor = True
        shell.current_shell = None
        shell.scheduler.keyboard.scan_rows = 5
        yield Condition.get().load(sleep = 0, wait_msg = False, send_msgs = [
            Message.get().load({"output": ""}, receiver = shell_id)
        ])
    except Exception as e:
        yield Condition.get().load(sleep = 0, send_msgs = [
            Message.get().load({"clear": True}, receiver = display_id)
        ])
        yield Condition.get().load(sleep = 0, send_msgs = [
            Message.get().load({"enabled": True}, receiver = cursor_id)
        ])
        shell.disable_output = False
        shell.enable_cursor = True
        shell.current_shell = None
        shell.scheduler.keyboard.scan_rows = 5
        reason = sys.print_exception(e)
        if reason is None:
            reason = "render failed"
        yield Condition.get().load(sleep = 0, send_msgs = [
            Message.get().load({"output": str(reason)}, receiver = shell_id)
        ])
