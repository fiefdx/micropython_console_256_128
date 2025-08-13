import os
import gc
import sys
import time
import random
from math import ceil
from io import StringIO

from listfile import ListFile
from shell import Shell
from scheduler import Condition, Message
from common import exists, path_join, isfile, isdir, ClipBoard

coroutine = True


class EditShell(object):
    def __init__(self, file_path, display_size = (42, 18), cache_size = 17, ram = False):
        self.display_width = display_size[0]
        self.display_height = display_size[1]
        self.offset_col = 0
        self.cache_size = cache_size
        self.cache = [] if ram else ListFile("/.edit_cache.json", shrink_threshold = 1024000) # []
        self.edit_history = [] if ram else ListFile("/.edit_history_cache.json", shrink_threshold = 1024000) # []
        self.edit_redo_cache = [] if ram else ListFile("/.edit_redo_cache.json", shrink_threshold = 1024000) # []
        self.edit_history_max_length = 1000
        self.edit_last_line = None
        self.cursor_color = 1
        self.cursor_row = 0
        self.cursor_col = 0
        self.enable_cursor = True
        self.exit = False
        self.file_path = file_path
        self.total_lines = 0
        self.line_num = 0
        self.display_offset_row = 0
        self.display_offset_col = 0
        if not exists(self.file_path):
            f = open(self.file_path, "w")
            f.close()
        self.file = open(self.file_path, "r")
        self.status = "loading"
        self.mode = "edit"
        self.previous_mode = "edit"
        self.select_start_row = 0
        self.select_start_col = 0
        self.exit_count = 0
        
    def input_char(self, c):
        if self.mode == "edit":
            if len(self.cache) == 0:
                self.cache.append("")
            if c == "\n":
                self.status = "changed"
                self.exit_count = 0
                before_enter = self.cache[self.cursor_row][:self.cursor_col + self.offset_col]
                after_enter = self.cache[self.cursor_row][self.cursor_col + self.offset_col:]
                self.cache[self.cursor_row] = before_enter
                self.edit_last_line = self.cursor_row
                self.cursor_row += 1
                op = None
                if len(self.cache) > self.cursor_row:
                    self.cache.insert(self.cursor_row, after_enter)
                    op = ["insert", self.cursor_row - 1, before_enter, after_enter]
                else:
                    self.cache.append(after_enter)
                    op = ["append", self.cursor_row - 1, before_enter, after_enter]
                self.edit_redo_cache.clear()
                if self.cursor_row > self.display_offset_row + self.cache_size - 1:
                    self.display_offset_row += 1
                self.cursor_col = 0
                self.offset_col = 0
                op.append((self.cursor_col, self.cursor_row, self.display_offset_col, self.display_offset_row, self.offset_col))
                self.edit_history.append(op)
            elif c == "\b":
                self.status = "changed"
                self.exit_count = 0
                op = None
                if len(self.cache[self.cursor_row]) == 0:
                    self.edit_last_line = self.cursor_row
                    self.edit_redo_cache.clear()
                    self.cache.pop(self.cursor_row)
                    self.cursor_move_left()
                    self.edit_history.append(["delete", self.cursor_row, "", (self.cursor_col, self.cursor_row, self.display_offset_col, self.display_offset_row, self.offset_col)])
                else:
                    delete_before = self.cache[self.cursor_row][:self.cursor_col + self.offset_col]
                    if len(delete_before) > 0:
                        self.append_edit_operation()
                        self.cache[self.cursor_row] = self.cache[self.cursor_row][:self.cursor_col + self.offset_col - 1] + self.cache[self.cursor_row][self.cursor_col + self.offset_col:]
                        self.cursor_move_left()
                    else:
                        self.append_edit_operation()
                        if self.cursor_row > 0:
                            self.edit_last_line = self.cursor_row
                            current_line = self.cache.pop(self.cursor_row)
                            op = ["merge", self.cursor_row, current_line, "", (self.cursor_col, self.cursor_row, self.display_offset_col, self.display_offset_row, self.offset_col)]
                            self.edit_redo_cache.clear()
                            self.cursor_move_left()
                            op[3] = self.cache[self.cursor_row]
                            self.cache[self.cursor_row] += current_line
                            self.edit_history.append(op)
            elif c == "UP" or c == "SUP":
                self.cursor_move_up()
            elif c == "DN" or c == "SDN":
                self.cursor_move_down()
            elif c in ("BX"):
                self.page_up()
            elif c in ("BB"):
                self.page_down()
            elif c == "LT":
                self.cursor_move_left()
            elif c == "RT":
                self.cursor_move_right()
            elif c == "BY":
                self.page_left()
            elif c == "BA":
                self.page_right()
            elif c == "SAVE":
                fp = open(self.file_path, "w")
                for line in self.cache:
                    fp.write(line + "\n")
                fp.close()
                self.status = "saved"
            elif c == "Ctrl-A":
                self.redo()
            elif c == "Ctrl-Z":
                self.undo()
            elif c == "Ctrl-B":
                self.mode = "select"
                self.select_start_row = self.cursor_row
                self.select_start_col = self.cursor_col + self.offset_col
            elif c == "Ctrl-V":
                self.paste()
            elif c == "ES":
                if self.status == "saved":
                    self.exit = True
                else:
                    self.exit_count += 1
                    if self.exit_count >= 3:
                        self.exit = True
            elif len(c) == 1:
                self.status = "changed"
                self.exit_count = 0
                self.append_edit_operation()
                self.cache[self.cursor_row] = self.cache[self.cursor_row][:self.cursor_col + self.offset_col] + c + self.cache[self.cursor_row][self.cursor_col + self.offset_col:]
                self.cursor_move_right()
        elif self.mode == "select":
            if c == "UP" or c == "SUP":
                self.cursor_move_up()
            elif c == "DN" or c == "SDN":
                self.cursor_move_down()
            elif c in ("BX"):
                self.page_up()
            elif c in ("BB"):
                self.page_down()
            elif c == "LT":
                self.cursor_move_left()
            elif c == "RT":
                self.cursor_move_right()
            elif c == "BY":
                self.page_left()
            elif c == "BA":
                self.page_right()
            elif c == "Ctrl-C":
                self.previous_mode = self.mode
                self.mode = "edit"
                self.copy_into_clipboard()
            elif c == "Ctrl-X":
                self.previous_mode = self.mode
                self.mode = "edit"
                self.copy_into_clipboard(cut = True)
            elif c == "ES":
                self.previous_mode = self.mode
                self.mode = "edit"

    def append_edit_operation(self):
        if self.cursor_row != self.edit_last_line:
            if self.edit_last_line is not None:
                self.edit_history.append(["edit", self.edit_last_line, self.cache[self.edit_last_line], (self.cursor_col, self.cursor_row, self.display_offset_col, self.display_offset_row, self.offset_col)])
                if len(self.edit_history) > self.edit_history_max_length:
                    self.edit_history.pop(0)
            self.edit_last_line = self.cursor_row
            self.edit_history.append(["edit", self.edit_last_line, self.cache[self.edit_last_line], (self.cursor_col, self.cursor_row, self.display_offset_col, self.display_offset_row, self.offset_col)])
            if len(self.edit_history) > self.edit_history_max_length:
                self.edit_history.pop(0)
        else:
            self.edit_history.append(["edit", self.edit_last_line, self.cache[self.edit_last_line], (self.cursor_col, self.cursor_row, self.display_offset_col, self.display_offset_row, self.offset_col)])
            if len(self.edit_history) > self.edit_history_max_length:
                self.edit_history.pop(0)
        self.edit_redo_cache.clear()
        
    def load_and_calc_total_lines(self):
        n = 0
        self.file.seek(0, 2)
        size = self.file.tell()
        yield 0
        self.file.seek(0)
        pos = self.file.tell()
        line = self.file.readline()
        while line:
            line = line.replace("\r", "")
            line = line.replace("\n", "")
            self.cache.append(line)
            n += 1
            if n % 100 == 0:
                gc.collect()
            pos = self.file.tell()
            line = self.file.readline()
            if n % 10 == 0:
                yield int(pos * 100 / size)
        self.total_lines = n
        self.file.close()
        self.status = "saved"
        yield 100
        
    def exists_line(self, line_num):
        return line_num >= 0 and line_num < self.total_lines

    def get_frame(self):
        data = {
            "frame": self.cache_to_frame(),
            "cursor": self.get_cursor_position(1),
        }
        if self.mode == "select":
            data["render"] = (("clear_lines", "lines"), ("selects", "lines"))
            clears = []
            for i in range(17):
                clears.append([1, i * 7 + 7, 254, i * 7 + 7, 0])
            selects = []
            for l in self.get_select_lines():
                selects.append([l[0][0], l[0][1], l[1][0] - 1, l[1][1], 1])
            data["clear_lines"] = clears
            data["selects"] = selects
        elif self.previous_mode == "select":
            self.previous_mode = self.mode
            data["render"] = (("clear_lines", "lines"), )
            clears = []
            for i in range(17):
                clears.append([1, i * 7 + 7, 254, i * 7 + 7, 0])
            data["clear_lines"] = clears
        return data

    def get_loading_frame(self, p):
        msg = "loading: %s%%" % p
        self.cursor_col = len(msg)
        self.cursor_row = 17
        if p == 100:
            self.cursor_row = 0
            self.cursor_col = 0
        return ["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", msg]
            
    def cache_to_frame(self):
        frame = []
        for line in self.cache[self.display_offset_row: self.display_offset_row + self.cache_size]:
            frame.append(line[self.offset_col: self.offset_col + self.display_width])
        for i in range(self.cache_size - len(frame)):
            frame.append("")
        frame.append("{progress: <27}{mode: >8}{status: >7}".format(
            progress = "%s/%s/%s" % (self.cursor_col + self.offset_col, self.cursor_row + 1, len(self.cache)),
            mode = "% 7s " % self.mode,
            status = self.status)
        )
        return frame
    
    def get_cursor_position(self, c = None):
        return self.cursor_col, self.cursor_row - self.display_offset_row, self.cursor_color if c is None else c
    
    def set_cursor_color(self, c):
        self.cursor_color = c

    def cr2xy(self, col, row):
        return (col * 6 + 3, row * 7 + 7)

    def paste(self):
        n = 0
        insert_col = self.cursor_col + self.offset_col
        insert_row = self.cursor_row
        original_line = self.cache[insert_row]
        for line in ClipBoard.iter_lines():
            if n == 0:
                self.cache[insert_row] = self.cache[insert_row][:insert_col] + line
                if line.endswith("\n"):
                    self.cache[insert_row] = self.cache[insert_row][:-1]
                    self.cache.insert(insert_row + 1, "")
            else:
                self.cache[insert_row + n] = line
                if line.endswith("\n"):
                    self.cache[insert_row + n] = self.cache[insert_row + n][:-1]
                    self.cache.insert(insert_row + n + 1, "")
            n += 1
        if n > 0:
            self.cursor_col = len(self.cache[insert_row + n - 1])
            self.offset_col = int(self.cursor_col / self.display_width) * self.display_width
            self.cursor_col = self.cursor_col % self.display_width
            self.cache[insert_row + n - 1] += original_line[insert_col + 1:]
            self.cursor_row = insert_row + n - 1
            if self.cursor_row - self.display_offset_row >= self.cache_size:
                self.display_offset_row = self.cursor_row - self.cache_size + 1

    def copy_into_clipboard(self, cut = False):
        display_start = self.display_offset_row
        display_end = self.display_offset_row + self.cache_size
        select_start_col = self.select_start_col
        select_start_row = self.select_start_row
        select_end_col = self.cursor_col + self.offset_col
        select_end_row = self.cursor_row
        if select_start_row > select_end_row or (select_start_row == select_end_row and select_start_col > select_end_col):
            select_end_col = self.select_start_col
            select_end_row = self.select_start_row
            select_start_col = self.cursor_col + self.offset_col
            select_start_row = self.cursor_row
        if select_start_row == select_end_row:
            if select_start_col != select_end_col:
                ClipBoard.set(self.cache[select_start_row][select_start_col: select_end_col + 1])
                if cut:
                    self.cache[select_start_row] = self.cache[select_start_row][:select_start_col] + self.cache[select_start_row][select_end_col + 1:]
        else:
            fp = ClipBoard.get_file()
            fp.write(self.cache[select_start_row][select_start_col:] + "\n")
            for row in range(select_start_row + 1, select_end_row):
                fp.write(self.cache[row] + "\n")
            fp.write(self.cache[select_end_row][:select_end_col])
            fp.close()
            if cut:
                self.edit_redo_cache.clear()
                if select_start_col == 0:
                    start_delete = select_start_row
                else:
                    start_delete = select_start_row + 1
                    self.edit_history.append(["edit", select_start_row, self.cache[select_start_row], (self.cursor_col, self.cursor_row, self.display_offset_col, self.display_offset_row, self.offset_col)])
                    self.cache[select_start_row] = self.cache[select_start_row][:select_start_col]
                    self.edit_history.append(["edit", select_start_row, self.cache[select_start_row], (self.cursor_col, self.cursor_row, self.display_offset_col, self.display_offset_row, self.offset_col)])
                for row in range(start_delete, select_end_row):
                    self.edit_history.append(["delete", start_delete, self.cache[start_delete], (self.cursor_col, self.cursor_row, self.display_offset_col, self.display_offset_row, self.offset_col)])
                    self.cache.pop(start_delete)
                self.edit_history.append(["edit", start_delete, self.cache[start_delete], (self.cursor_col, self.cursor_row, self.display_offset_col, self.display_offset_row, self.offset_col)])
                self.cache[start_delete] = self.cache[start_delete][select_end_col:]

    def get_select_lines(self):
        lines = []
        display_start = self.display_offset_row
        display_end = self.display_offset_row + self.cache_size
        select_start_col = self.select_start_col
        select_start_row = self.select_start_row
        select_end_col = self.cursor_col + self.offset_col
        select_end_row = self.cursor_row
        if select_start_row > select_end_row or (select_start_row == select_end_row and select_start_col > select_end_col):
            select_end_col = self.select_start_col
            select_end_row = self.select_start_row
            select_start_col = self.cursor_col + self.offset_col
            select_start_row = self.cursor_row
        if select_start_row >= display_start and select_end_row < display_end:
            if select_start_row == select_end_row:
                if select_start_col != select_end_col:
                    line = []
                    if select_start_col >= self.offset_col:
                        line.append(self.cr2xy(select_start_col - self.offset_col, select_start_row - display_start))
                    else:
                        line.append(self.cr2xy(0, select_start_row - display_start))
                    line.append(self.cr2xy(select_end_col - self.offset_col, select_start_row - display_start))
                    lines.append(line)
            else:
                line = []
                if select_start_col >= self.offset_col:
                    line.append(self.cr2xy(select_start_col - self.offset_col, select_start_row - display_start))
                else:
                    line.append(self.cr2xy(0, select_start_row - display_start))
                line.append(self.cr2xy(self.display_width, select_start_row - display_start))
                lines.append(line)
                for row in range(select_start_row + 1, select_end_row):
                    lines.append([self.cr2xy(0, row - display_start), self.cr2xy(self.display_width, row - display_start)])
                if select_end_col - self.offset_col > 0:
                    line = [self.cr2xy(0, select_end_row - display_start)]
                    line.append(self.cr2xy(select_end_col - self.offset_col, select_end_row - display_start))
                    lines.append(line)
        elif select_start_row >= display_start and select_end_row >= display_end:
            line = []
            if select_start_col >= self.offset_col:
                line.append(self.cr2xy(select_start_col - self.offset_col, select_start_row - display_start))
            else:
                line.append(self.cr2xy(0, select_start_row - display_start))
            line.append(self.cr2xy(self.display_width, select_start_row - display_start))
            lines.append(line)
            for row in range(select_start_row + 1, display_end):
                lines.append([self.cr2xy(0, row - display_start), self.cr2xy(self.display_width, row - display_start)])
        elif select_start_row < display_start and select_end_row >= display_start:
            for row in range(display_start, select_end_row):
                lines.append([self.cr2xy(0, row - display_start), self.cr2xy(self.display_width, row - display_start)])
            if select_end_col - self.offset_col > 0:
                line = [self.cr2xy(0, select_end_row - display_start)]
                line.append(self.cr2xy(select_end_col - self.offset_col, select_end_row - display_start))
                lines.append(line)
        return lines
            
    def cursor_move_up(self):
        self.cursor_row -= 1
        if self.cursor_row < 0:
            self.cursor_row = 0
        if self.cursor_row < self.display_offset_row:
            self.display_offset_row = self.cursor_row
        if len(self.cache[self.cursor_row]) < self.offset_col + self.cursor_col:
            self.cursor_col = len(self.cache[self.cursor_row]) % self.display_width
            self.offset_col = len(self.cache[self.cursor_row]) - self.cursor_col
    
    def cursor_move_down(self):
        self.cursor_row += 1
        if self.cursor_row >= len(self.cache):
            self.cursor_row = len(self.cache) - 1
        if self.cursor_row > self.display_offset_row + self.cache_size - 1:
            self.display_offset_row += 1
        if len(self.cache[self.cursor_row]) < self.offset_col + self.cursor_col:
            self.cursor_col = len(self.cache[self.cursor_row]) % self.display_width
            self.offset_col = len(self.cache[self.cursor_row]) - self.cursor_col
            
    def page_up(self):
        self.display_offset_row -= self.cache_size
        self.cursor_row -= self.cache_size
        if self.display_offset_row < 0:
            self.display_offset_row = 0
        if self.cursor_row < 0:
            self.cursor_row = 0
        if len(self.cache[self.cursor_row]) < self.offset_col + self.cursor_col:
            self.cursor_col = len(self.cache[self.cursor_row]) % self.display_width
            self.offset_col = len(self.cache[self.cursor_row]) - self.cursor_col
    
    def page_down(self):
        self.display_offset_row += self.cache_size
        self.cursor_row += self.cache_size
        if self.cursor_row >= len(self.cache):
            self.cursor_row = len(self.cache) - 1
        if self.display_offset_row > len(self.cache) - self.cache_size:
            self.display_offset_row = len(self.cache) - self.cache_size
        if len(self.cache[self.cursor_row]) < self.offset_col + self.cursor_col:
            self.cursor_col = len(self.cache[self.cursor_row]) % self.display_width
            self.offset_col = len(self.cache[self.cursor_row]) - self.cursor_col
    
    def cursor_move_left(self):
        self.cursor_col -= 1
        if self.cursor_col < 0:
            self.cursor_col = 0
            if self.offset_col > 0:
                self.offset_col -= 1
                self.cache_to_frame()
            else:
                if self.cursor_row > 0:
                    self.cursor_row -= 1
                    self.cursor_col = len(self.cache[self.cursor_row]) % self.display_width
                    self.offset_col = len(self.cache[self.cursor_row]) - self.cursor_col
                else:
                    self.cursor_col = 0
                    self.offset_col = 0
        if self.cursor_row < self.display_offset_row:
            self.display_offset_row = self.cursor_row
        
    def cursor_move_right(self):
        self.cursor_col += 1
        if len(self.cache[self.cursor_row]) >= self.cursor_col + self.offset_col:
            if self.cursor_col > self.display_width:
                self.offset_col += 1
                self.cache_to_frame()
                self.cursor_col = self.display_width
        else:
            self.cursor_col -= 1
            if len(self.cache) - 1 > self.cursor_row:
                self.cursor_row += 1
                self.cursor_col = 0
                self.offset_col = 0
        if self.cursor_row > self.display_offset_row + self.cache_size - 1:
            self.display_offset_row += 1
            
    def page_left(self):
        if self.offset_col >= self.display_width:
            self.offset_col -= self.display_width
            if self.offset_col < 0:
                self.offset_col = 0
            self.cache_to_frame()
    
    def page_right(self):
        if len(self.cache[self.cursor_row]) >= self.offset_col + self.display_width:
            self.offset_col += self.display_width
            if len(self.cache[self.cursor_row]) < self.cursor_col + self.offset_col:
                self.cursor_col = len(self.cache[self.cursor_row]) - self.offset_col
            self.cache_to_frame()

    def undo(self):
        if len(self.edit_history) > 0:
            if len(self.edit_redo_cache) == 0:
                op = self.edit_history[-1]
                if op[0] == "edit":
                    if self.cache[op[1]] != op[2]:
                        self.edit_redo_cache.append(["edit", op[1], self.cache[op[1]], (self.cursor_col, self.cursor_row, self.display_offset_col, self.display_offset_row, self.offset_col)])
            op = self.edit_history.pop(-1)
            if op[0] == "edit":
                self.cache[op[1]] = op[2]
                self.cursor_col, self.cursor_row, self.display_offset_col, self.display_offset_row, self.offset_col = op[3]
            elif op[0] == "insert":
                self.cache[op[1]] = op[2] + op[3]
                self.cache.pop(op[1] + 1)
                self.cursor_col, self.cursor_row, self.display_offset_col, self.display_offset_row, self.offset_col = op[4]
                self.cursor_row -= 1
                self.cursor_col = len(op[2])
            elif op[0] == "append":
                self.cache[op[1]] = op[2] + op[3]
                self.cache.pop(op[1] + 1)
                self.cursor_col, self.cursor_row, self.display_offset_col, self.display_offset_row, self.offset_col = op[4]
                self.cursor_row -= 1
                self.cursor_col = len(op[2])
            elif op[0] == "delete":
                self.cache.insert(op[1], op[2])
                self.cursor_col, self.cursor_row, self.display_offset_col, self.display_offset_row, self.offset_col = op[3]
            elif op[0] == "merge":
                self.cache.insert(op[1], op[2])
                self.cache[op[1] - 1] = op[3]
                self.cursor_col, self.cursor_row, self.display_offset_col, self.display_offset_row, self.offset_col = op[4]
            self.edit_redo_cache.append(op)

    def redo(self):
        if len(self.edit_redo_cache) > 0:
            op = self.edit_redo_cache.pop(-1)
            if op[0] == "edit":
                self.cache[op[1]] = op[2]
                self.cursor_col, self.cursor_row, self.display_offset_col, self.display_offset_row, self.offset_col = op[3]
            elif op[0] == "insert":
                self.cache[op[1]] = op[2]
                self.cache.insert(op[1] + 1, op[3])
                self.cursor_col, self.cursor_row, self.display_offset_col, self.display_offset_row, self.offset_col = op[4]
            elif op[0] == "append":
                self.cache[op[1]] = op[2]
                self.cache.insert(op[1] + 1, op[3])
                self.cursor_col, self.cursor_row, self.display_offset_col, self.display_offset_row, self.offset_col = op[4]
            elif op[0] == "delete":
                self.cache.pop(op[1])
                self.cursor_col, self.cursor_row, self.display_offset_col, self.display_offset_row, self.offset_col = op[3]
            elif op[0] == "merge":
                self.cache.pop(op[1])
                self.cache[op[1] - 1] = op[3] + op[2]
                self.cursor_col, self.cursor_row, self.display_offset_col, self.display_offset_row, self.offset_col = op[4]
            self.edit_history.append(op)
            
    def close(self):
        self.file.close()
        self.cache.clear()
        del self.cache

def main(*args, **kwargs):
    #print(kwargs["args"])
    task = args[0]
    name = args[1]
    shell = kwargs["shell"]
    shell_id = kwargs["shell_id"]
    display_id = shell.display_id
    shell.disable_output = True
    width, height = 42, 18
    try:
        if len(kwargs["args"]) > 0:
            file_path = kwargs["args"][0]
            ram = False
            if len(kwargs["args"]) > 1:
                ram = int(kwargs["args"][1]) == 1
            s = EditShell(file_path, ram = ram)
            shell.current_shell = s
            for p in s.load_and_calc_total_lines():
                yield Condition.get().load(sleep = 0, wait_msg = False, send_msgs = [
                    Message.get().load({"frame": s.get_loading_frame(p), "cursor": s.get_cursor_position(1)}, receiver = display_id)
                ])
            yield Condition.get().load(sleep = 0, wait_msg = True, send_msgs = [
                Message.get().load(s.get_frame(), receiver = display_id)
            ])
            msg = task.get_message()
            c = msg.content["msg"]
            msg.release()
            while not s.exit:
                s.input_char(c)
                if s.exit:
                    s.close()
                    break
                yield Condition.get().load(sleep = 0, wait_msg = True, send_msgs = [
                    Message.get().load(s.get_frame(), receiver = display_id)
                ])
                msg = task.get_message()
                c = msg.content["msg"]
                msg.release()
        else:
            yield Condition.get().load(sleep = 0, send_msgs = [
                Message.get().load({"output": "invalid parameters"}, receiver = shell_id)
            ])
        shell.disable_output = False
        shell.current_shell = None
        yield Condition.get().load(sleep = 0, wait_msg = False, send_msgs = [
            Message.get().load({"output": ""}, receiver = shell_id)
        ])
    except Exception as e:
        shell.disable_output = False
        shell.current_shell = None
        buf = StringIO()
        sys.print_exception(e, buf)
        reason = buf.getvalue()
        if reason is None:
            reason = "edit failed"
        yield Condition.get().load(sleep = 0, send_msgs = [
            Message.get().load({"output": str(reason)}, receiver = shell_id)
        ])
