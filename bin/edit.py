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
from common import exists, path_join, isfile, isdir

coroutine = True


class EditShell(object):
    def __init__(self, file_path, display_size = (42, 18), cache_size = 17, ram = True):
        self.display_width = display_size[0]
        self.display_height = display_size[1]
        self.offset_col = 0
        self.offset_row = 0
        self.cache_size = cache_size
        self.cache = [] if ram else ListFile("/.edit_cache.json", shrink_threshold = 1024000) # []
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
        self.status = "saved"
        self.exit_count = 0
        
    def input_char(self, c):
        if len(self.cache) == 0:
            self.cache.append("")
        if c == "\n":
            self.status = "changed"
            self.exit_count = 0
            before_enter = self.cache[self.cursor_row][:self.cursor_col + self.offset_col]
            after_enter = self.cache[self.cursor_row][self.cursor_col + self.offset_col:]
            self.cache[self.cursor_row] = before_enter
            self.cursor_row += 1
            if len(self.cache) > self.cursor_row:
                self.cache.insert(self.cursor_row, after_enter)
            else:
                self.cache.append(after_enter)
            if self.cursor_row > self.display_offset_row + self.cache_size - 1:
                self.display_offset_row += 1
            self.cursor_col = 0
            self.offset_col = 0
        elif c == "\b":
            self.status = "changed"
            self.exit_count = 0
            if len(self.cache[self.cursor_row]) == 0:
                self.cache.pop(self.cursor_row)
                self.cursor_move_left()
            else:
                delete_before = self.cache[self.cursor_row][:self.cursor_col + self.offset_col]
                if len(delete_before) > 0:
                    self.cache[self.cursor_row] = self.cache[self.cursor_row][:self.cursor_col + self.offset_col - 1] + self.cache[self.cursor_row][self.cursor_col + self.offset_col:]
                    self.cursor_move_left()
                else:
                    if self.cursor_row > 0:
                        current_line = self.cache.pop(self.cursor_row)
                        self.cursor_move_left()
                        self.cache[self.cursor_row] += current_line
        elif c == "UP":
            self.cursor_move_up()
        elif c == "DN":
            self.cursor_move_down()
        elif c in ("SUP", "BX"):
            self.page_up()
        elif c in ("SDN", "BB"):
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
        elif c == "ES":
            if self.status == "saved":
                self.exit = True
            else:
                self.exit_count += 1
                if self.exit_count >= 3:
                    self.exit = True
        else:
            self.status = "changed"
            self.exit_count = 0
            self.cache[self.cursor_row] = self.cache[self.cursor_row][:self.cursor_col + self.offset_col] + c + self.cache[self.cursor_row][self.cursor_col + self.offset_col:]
            self.cursor_move_right()
        
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
        yield 100
        
    def exists_line(self, line_num):
        return line_num >= 0 and line_num < self.total_lines
            
    def get_display_frame(self):
        return self.cache_to_frame()

    def get_loading_frame(self, p):
        return ["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "loading: %s%%" % p]
            
    def cache_to_frame(self):
        frame = []
        for line in self.cache[self.display_offset_row: self.display_offset_row + self.cache_size]:
            frame.append(line[self.offset_col: self.offset_col + self.display_width])
        for i in range(self.cache_size - len(frame)):
            frame.append("")
        frame.append("{progress: <35}{status: >7}".format(progress = "%s/%s/%s" % (self.cursor_col + self.offset_col, self.cursor_row + 1, len(self.cache)), status = self.status))
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
            ram = True
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
