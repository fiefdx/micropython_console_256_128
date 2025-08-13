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
            elif c == "UP":
                self.cursor_move_up()
            elif c == "DN":
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
                self.select_start_col = self.cursor_col
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
            if c == "UP":
                self.cursor_move_up()
            elif c == "DN":
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
                self.mode = "copy"
                ClipBoard.set("")
            elif c == "Ctrl-X":
                self.mode = "cut"
                ClipBoard.set("")
            elif c == "ES":
                self.mode = "edit"
        elif self.mode == "copy" or self.mode == "cut":
            if c == "UP":
                self.cursor_move_up()
            elif c == "DN":
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
            elif c == "Ctrl-V":
                self.mode = "edit"
            elif c == "ES":
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
            
    def get_display_frame(self):
        return self.cache_to_frame()

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
                Message.get().load({"frame": s.get_display_frame(), "cursor": s.get_cursor_position(1)}, receiver = display_id)
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
                    Message.get().load({"frame": s.get_display_frame(), "cursor": s.get_cursor_position(1)}, receiver = display_id)
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
