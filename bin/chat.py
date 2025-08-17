import os
import sys
import time
from math import ceil
from io import StringIO

from shell import Shell
from scheduler import Condition, Message
from ollama import Chat
from common import exists, path_join, isfile, isdir, path_split

coroutine = True


class ChatShell(Shell):
    def __init__(self, display_size = (19, 9), cache_size = (-1, 50), history_length = 100, host = "", port = 11434, model = "llama:3.2", stream = False, prompt_c = ">", scheduler = None, display_id = None, storage_id = None, history_file_path = "/.chat_history"):
        self.display_width = display_size[0]
        self.display_height = display_size[1]
        self.display_width_with_prompt = display_size[0] + len(prompt_c)
        self.history_length = history_length
        self.prompt_c = prompt_c
        self.history = []
        self.cache_width = cache_size[0]
        self.cache_lines = cache_size[1]
        self.cache = []
        self.cursor_color = 1
        self.current_row = 0
        self.current_col = 0
        self.scheduler = scheduler
        self.display_id = display_id
        self.storage_id = storage_id
        self.cursor_row = 0
        self.cursor_col = 0
        self.history_idx = 0
        self.scroll_row = 0
        self.frame_history = []
        self.session_task_id = None
        self.exit = False
        self.current_shell = None
        self.enable_cursor = True
        self.history_file_path = history_file_path
        self.stats = ""
        self.loading = True
        self.chat = Chat(host = host, port = port, model = model, stream = stream)
        self.load_history()
        # self.clear()
        
    # def clear(self):
    #     self.term = StringIO()
    #     os.dupterm(self.term)
        
    def input_char(self, c):
        if c == "\n":
            cmd = self.cache[-1][len(self.prompt_c):].strip()
            if len(cmd) > 0:
                self.history.append(self.cache[-1][len(self.prompt_c):])
                self.write_history(self.cache[-1][len(self.prompt_c):])
                if cmd == "exit" or cmd == "quit":
                    self.exit = True
                elif cmd == "clear" or cmd == "new":
                    self.chat.clear()
                    self.write_lines("new chat", end = True)
                else:
                    try:
                        success, content = self.chat.chat(cmd)
                        if success:
                            self.write_lines(content, end = True)
                        else:
                            self.write_lines("fail reason: %s" % content.decode(), end = True)
                    except Exception as e:
                        self.write_lines(str(e), end = True)
            else:
                self.cache.append(self.prompt_c)
                self.cache_to_frame_history()
            if len(self.history) > self.history_length:
                self.history.pop(0)
            self.history_idx = len(self.history)
        elif c == "\b":
            if len(self.cache[-1][:self.current_col]) > len(self.prompt_c):
                self.cache[-1] = self.cache[-1][:self.current_col-1] + self.cache[-1][self.current_col:]
                self.cursor_move_left()
        elif c == "BX":
            self.scroll_up()
        elif c == "BB":
            self.scroll_down()
        elif c == "UP":
            self.history_previous()
        elif c == "DN":
            self.history_next()
        elif c == "LT":
            self.cursor_move_left()
        elif c == "RT":
            self.cursor_move_right()
        elif c == "ES":
            pass
        elif len(c) == 1:
            self.cache[-1] = self.cache[-1][:self.current_col] + c + self.cache[-1][self.current_col:]
            self.cursor_move_right()
                
        if len(self.cache) > self.cache_lines:
            self.cache.pop(0)
        self.current_row = len(self.cache)
        
    def write_char(self, c):
        if c == "\n":
            self.cache.append(self.prompt_c)
        else:
            self.cache[-1] += c
            if len(self.cache[-1]) > self.display_width_with_prompt:
                self.cache.append(" " + self.cache[-1][self.display_width_with_prompt:])
                self.cache[-2] = self.cache[-2][:display_width_with_prompt]
                
        if len(self.cache) > self.cache_lines:
            self.cache.pop(0)
        self.current_row = len(self.cache) - 1
        self.current_col = len(self.cache[-1])

    def update_stats(self, d):
        self.stats = "C%3d%% R%3d%%|%.2fK|%.2fK D %3dK|%3dK" % (d[1], d[2], d[3] / 1024, d[4] / 1024, d[6] / 1024, d[7] / 1024)

    def get_display_frame(self, c = None):
        data = {}
        frame = self.cache_to_frame()[-self.display_height:]
        frame.append(self.stats)
        data["frame"] = frame
        data["cursor"] = self.get_cursor_position(c)
        if self.loading:
            data["render"] = (("borders", "rects"),)
            data["borders"] = [[0, 0, 256, 127, 1], [0, 119, 256, 8, 1]]
            self.loading = False
        return data


def main(*args, **kwargs):
    task = args[0]
    name = args[1]
    shell = kwargs["shell"]
    shell_id = kwargs["shell_id"]
    shell.disable_output = True
    try:
        model = "llama3.2"
        host = "192.168.4.30"
        port = 11434
        stream = False
        if len(kwargs["args"]) > 0:
            model = kwargs["args"][0]
        if len(kwargs["args"]) > 1:
            host = kwargs["args"][1]
        if len(kwargs["args"]) > 2:
            port = kwargs["args"][2]
        if len(kwargs["args"]) > 3:
            stream = True if int(kwargs["args"][3]) == 1 else False
        s = ChatShell(display_size = (39, 17), host = host, port = port, model = model, stream = stream)
        shell.current_shell = s
        s.write_line("              Welcome to Chat")
        s.write_char("\n")
        yield Condition.get().load(sleep = 0, wait_msg = False, send_msgs = [
            Message.get().load(s.get_display_frame(), receiver = shell_id)
        ])
        c = ""
        msg = task.get_message()
        if msg:
            c = msg.content["msg"]
            msg.release()
        while not s.exit:
            #print("char:", c)
            s.input_char(c)
            if not s.exit:
                yield Condition.get().load(sleep = 50, wait_msg = False, send_msgs = [
                    Message.get().load(s.get_display_frame(1 if c != "" else None), receiver = shell_id)
                ])
                c = ""
                msg = task.get_message()
                if msg:
                    c = msg.content["msg"]
                    msg.release()
        shell.disable_output = False
        shell.current_shell = None
        shell.loading = True
        yield Condition.get().load(sleep = 0, wait_msg = False, send_msgs = [
            Message.get().load({"output": "quit from chat"}, receiver = shell_id)
        ])
    except Exception as e:
        shell.disable_output = False
        shell.current_shell = None
        shell.loading = True
        yield Condition.get().load(sleep = 0, send_msgs = [
            Message.get().load({"output": str(e)}, receiver = shell_id)
        ])
