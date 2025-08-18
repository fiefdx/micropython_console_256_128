import sys
import uos
from math import ceil
from micropython import const

# from listfile import ListFile
from scheduler import Condition, Task, Message
from common import exists, path_join, isfile, isdir


class Shell(object):
    def __init__(self, display_size = (20, 8), cache_size = (-1, 50), history_length = 100, prompt_c = ">", scheduler = None, display_id = None, storage_id = None, history_file_path = "/.history", bin_path = "/bin"):
        self.display_width = const(display_size[0])
        self.display_height = const(display_size[1])
        self.display_width_with_prompt = const(display_size[0] + len(prompt_c))
        self.history_length = const(history_length)
        self.prompt_c = const(prompt_c)
        self.history = [] # ListFile("./shell_history_cache.json", shrink_threshold = 10240) # 86.86k free for [], 88.05k for ListFile
        self.cache_width = const(cache_size[0])
        self.cache_lines = const(cache_size[1])
        self.cache = [] # ListFile("./shell_cache.json", shrink_threshold = 10240)
        self.cursor_color = 1
        self.current_row = 0
        self.current_col = 0
        self.scheduler = scheduler
        self.display_id = const(display_id)
        self.storage_id = const(storage_id)
        self.cursor_row = 0
        self.cursor_col = 0
        self.cursor_id = None
        self.history_idx = 0
        self.scroll_row = 0
        self.frame_history = [] # ListFile("./shell_frame_history_cache.json", shrink_threshold = 10240) # 90.81k for ListFile
        self.session_task_id = None
        self.disable_output = False
        self.current_shell = None
        self.enable_cursor = True
        self.history_file_path = const(history_file_path)
        self.bin_path = const(bin_path)
        self.stats = ""
        self.loading = True
        self.load_history()
    
    def load_history(self):
        if exists(self.history_file_path):
            history_file = open(self.history_file_path, "r")
            history_lines = 0
            line = history_file.readline()
            while line:
                line = line.strip()
                self.history.append(line)
                if len(self.history) > self.history_length:
                    self.history.pop(0)
                history_lines += 1
                line = history_file.readline()
            history_file.close()
            if history_lines > self.history_length:
                tmp_file_path = self.history_file_path + ".tmp"
                if exists(tmp_file_path):
                    uos.remove(tmp_file_path)
                uos.rename(self.history_file_path, tmp_file_path)
                tmp_file = open(tmp_file_path, "r")
                history_file = open(self.history_file_path, "w")
                l = 0
                line = tmp_file.readline()
                while line:
                    l += 1
                    if l > (history_lines - self.history_length):
                        history_file.write(line)
                    line = tmp_file.readline()
                tmp_file.close()
                history_file.close()
                uos.remove(tmp_file_path)
        self.history_file = open(self.history_file_path, "a")
        self.history_idx = len(self.history)
        
    def write_history(self, line):
        if line[-1] != "\n":
            line += "\n"
        self.history_file.write(line)
        self.history_file.flush()
    
    def help_commands(self):
        result = ""
        fs = uos.listdir("/bin")
        line = ""
        for f in fs:
            if f not in ("__init__.py", ):
                cmd = f.split(".")[0]
                if len(line + cmd + ", ") > self.display_width:
                    result += line + "\n"
                    line = cmd + ", "
                else:
                    line += cmd + ", "
        if line != "":
            result += line
        if result.endswith(", "):
            result = result[:-2]
        elif result.endswith("\n"):
            result = result[:-1]
        return result
        
    def get_display_frame(self):
        data = {}
        frame = self.cache_to_frame()[-self.display_height:]
        frame.append(self.stats)
        data["frame"] = frame
        data["cursor"] = self.get_cursor_position(1)
        if self.loading:
            data["render"] = (("borders", "rects"),)
            data["borders"] = [[0, 0, 256, 127, 1], [0, 119, 256, 8, 1]]
            self.loading = False
        return data
    
    def cache_to_frame_history(self):
        self.frame_history.clear()
        for n, line in enumerate(self.cache[:-1]):
            for i in range(ceil(len(line) / self.display_width_with_prompt)):
                self.frame_history.append(line[i*self.display_width_with_prompt:(i+1)*self.display_width_with_prompt])
                
    def history_to_frame(self, last_lines, scroll_row):
        frame = []
        total_lines = len(self.frame_history) + len(last_lines)
        end_idx = total_lines + scroll_row - 1
        start_idx = total_lines + scroll_row - self.display_height
        if start_idx < 0:
            start_idx = 0
            end_idx = start_idx + self.display_height - 1
            self.scroll_row = self.display_height - total_lines
        if end_idx >= total_lines:
            end_idx = total_lines - 1
        if start_idx >= 0 and start_idx < len(self.frame_history):
            if end_idx >= 0 and end_idx < len(self.frame_history):
                for i in range(start_idx, end_idx + 1):
                    frame.append(self.frame_history[i])
            else:
                for i in range(start_idx, len(self.frame_history)):
                    frame.append(self.frame_history[i])
                for i in range(0, end_idx - len(self.frame_history) + 1):
                    frame.append(last_lines[i])
        else:
            for i in range(start_idx - len(self.frame_history), end_idx - len(self.frame_history) + 1):
                frame.append(last_lines[i])
        return frame
    
    def cache_to_frame(self):
        frame = []
        self.cursor_row = 0
        self.cursor_col = 0
        row = -1
        if self.scroll_row == 0:
            lines = self.cache[-self.display_height:]
            for n, line in enumerate(lines):
                if len(line) > 0:
                    for i in range(ceil(len(line) / self.display_width_with_prompt)):
                        frame.append(line[i*self.display_width_with_prompt:(i+1)*self.display_width_with_prompt])
                        row += 1
                        if len(frame) > self.display_height:
                            frame.pop(0)
                            row -= 1
                        if n == len(lines) - 1: # last line in cache
                            if ceil(self.current_col / self.display_width_with_prompt) == (i + 1): # cursor in current line
                                self.cursor_row = row
                                self.cursor_col = self.current_col % self.display_width_with_prompt
                                if self.cursor_col == 0:
                                    self.cursor_col = 42
                                #print("cursor_row: ", row, "cursor_col: ", self.cursor_col)
                            elif ceil(self.current_col / self.display_width_with_prompt) < (i + 1):
                                if len(frame) >= self.display_height:
                                    self.cursor_row -= 1
                else:
                    frame.append(line)
                    row += 1
                    self.cursor_row = row
        else:
            frame_lines = []
            line = self.cache[-1]
            for i in range(ceil(len(line) / self.display_width_with_prompt)):
                frame_lines.append(line[i*self.display_width_with_prompt:(i+1)*self.display_width_with_prompt])
            frame = self.history_to_frame(frame_lines, self.scroll_row)
        if self.cursor_row >= self.display_height:
            self.cursor_row = self.display_height - 1
        while len(frame) < self.display_height:
            frame.append("")
        return frame
        
    def get_cursor_position(self, c = None):
        #print("get_cursor_position:", self.cursor_col, self.cursor_row)
        if self.current_shell:
            return self.current_shell.get_cursor_position(c)
        if self.enable_cursor:
            return self.cursor_col, self.cursor_row, self.cursor_color if c is None else c
        else:
            return self.cursor_col, self.cursor_row, 0
    
    def set_cursor_position(self, col, row):
        #print("set_cursor_position:", col, row)
        self.cursor_col, self.cursor_row = col, row
    
    def set_cursor_color(self, c):
        if self.current_shell:
            self.current_shell.set_cursor_color(c)
        self.cursor_color = c
    
    def get_cursor_cache_position(self, c = None):
        return self.current_col, self.current_row if self.current_row <= (self.display_height - 1) else (self.display_height - 1), self.cursor_color if c is None else c
    
    def write_char(self, c):
        if c == "\n":
            self.cache.append(self.prompt_c)
        elif len(c) == 1:
            self.cache[-1] += c
            if len(self.cache[-1]) > self.display_width_with_prompt:
                self.cache.append(" " + self.cache[-1][self.display_width_with_prompt:])
                self.cache[-2] = self.cache[-2][:self.display_width_with_prompt]
                
        if len(self.cache) > self.cache_lines:
            self.cache.pop(0)
        self.current_row = len(self.cache) - 1
        self.current_col = len(self.cache[-1])

    def update_stats(self, d):
        self.stats = "C%3d%% R%3d%%|%.2fK|%.2fK D %3dK|%3dK" % (d[1], d[2], d[3] / 1024, d[4] / 1024, d[6] / 1024, d[7] / 1024)
        if hasattr(self.current_shell, "update_stats"):
            self.current_shell.update_stats(d)
    
    def input_char(self, c):
        try:
            if self.session_task_id is not None and self.scheduler.exists_task(self.session_task_id):
                self.scheduler.add_task(Task.get().load(self.send_session_message, c, condition = Condition.get(), kwargs = {})) # execute cmd
            else:
                if c == "\n":
                    cmd = self.cache[-1][len(self.prompt_c):].strip()
                    if len(cmd) > 0:
                        if self.session_task_id is not None and self.scheduler.exists_task(self.session_task_id):
                            self.scheduler.add_task(Task.get().load(self.send_session_message, self.cache[-1].strip(), condition = Condition.get(), kwargs = {})) # execute cmd
                        else:
                            self.history.append(self.cache[-1][len(self.prompt_c):])
                            self.write_history(self.cache[-1][len(self.prompt_c):])
                            command = cmd.split(" ")[0].strip()
                            self.scheduler.add_task(Task.get().load(self.run_coroutine, cmd, condition = Condition.get(), kwargs = {})) # execute cmd
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
                elif c in ("ES", "SAVE"):
                    pass
                elif len(c) == 1:
                    self.cache[-1] = self.cache[-1][:self.current_col] + c + self.cache[-1][self.current_col:]
                    self.cursor_move_right()
                    
            if len(self.cache) > self.cache_lines:
                self.cache.pop(0)
            self.current_row = len(self.cache)
            #self.current_col = len(self.cache[-1])
        except Exception as e:
            print(sys.print_exception(e))
            
    def write_line(self, line):
        self.cache.append(line)
        if len(self.cache) > self.cache_lines:
            self.cache.pop(0)
        self.current_row = len(self.cache) - 1
        self.current_col = len(self.cache[-1])
        self.cache_to_frame_history()
    
    def write_lines(self, lines, end = False):
        lines = lines.split("\n")
        for line in lines:
            #if len(line) > 0:
            line = line.replace("\r", "")
            line = line.replace("\n", "")
            self.cache.append(line)
            if len(self.cache) > self.cache_lines:
                self.cache.pop(0)
            self.current_row = len(self.cache) - 1
            self.current_col = len(self.cache[-1])
        if end:
            self.write_char("\n")
        self.cache_to_frame_history()
            
    def write(self, s):
        line_width = self.display_width_with_prompt
        d = s[:line_width]
        s = s[line_width:]
        while len(d) > 0:
            self.cache.append(d)
            if len(self.cache) > self.cache_lines:
                self.cache.pop(0)
            self.current_row = len(self.cache) - 1
            self.current_col = len(self.cache[-1])
            d = s[:line_width]
            s = s[line_width:]
        self.write_char("\n")
        self.cache_to_frame_history()
            
    def run(self, task, cmd):
        yield Condition.get().load(sleep = 0, send_msgs = [
            Message.get().load({"cmd": cmd}, receiver = self.storage_id)
        ])
        
    def send_session_message(self, task, msg):
        #print("send_session_message:", msg, self.session_task_id)
        yield Condition.get().load(sleep = 0, send_msgs = [
            Message.get().load({"msg": msg}, receiver = self.session_task_id)
        ])
        
    def run_coroutine(self, task, cmd):
        #print("run_coroutine: ", task, cmd)
        #import bin
        args = cmd.split(" ")
        module = args[0].split(".")[0]
        #if "/sd/usr" not in sys.path:
        #    sys.path.insert(0, "/sd/usr")
        #import bin
        if module not in sys.modules:
            #import_str = "from bin import %s" % module
            import_str = "import %s; sys.modules['%s'] = %s" % (module, module, module)
            exec(import_str)
        if sys.modules[module].coroutine:
            #bin.__dict__[]
            #self.session_task_id = self.scheduler.add_task(Task(bin.__dict__[module].main, cmd, kwargs = {"args": args[1:], "shell_id": self.scheduler.shell_id, "shell": self}, need_to_clean = [bin.__dict__[module]])) # execute cmd
            self.session_task_id = self.scheduler.add_task(
                Task.get().load(sys.modules[module].main, cmd, condition = Condition.get(), kwargs = {"args": args[1:],
                                                                                           "shell_id": self.scheduler.shell_id,
                                                                                           "shell": self}, need_to_clean = [sys.modules[module]])
            ) # execute cmd
        else:
            yield Condition.get().load(sleep = 0, send_msgs = [
                Message.get().load({"cmd": cmd}, receiver = self.storage_id)
            ])
    
    def cursor_move_left(self):
        if self.current_col > len(self.prompt_c):
            self.current_col -= 1
        #print("current_col: ", self.current_col)
    
    def cursor_move_right(self):
        if self.current_col < len(self.cache[-1]):
            self.current_col += 1
        #print("current_col: ", self.current_col)
        
    def scroll_up(self):
        self.scroll_row -= 18
        #print("scroll_row:", self.scroll_row)
        
    def scroll_down(self):
        self.scroll_row += 18
        if self.scroll_row >= 0:
            self.scroll_row = 0
        #print("scroll_row:", self.scroll_row)
    
    def history_previous(self):
        self.history_idx -= 1
        if self.history_idx <= 0:
            self.history_idx = 0
        #print("history:", self.history, self.history_idx)
        if len(self.history) > 0:
            #if self.history_idx > len(self.history) - 1:
            #    self.history_idx = len(self.history) - 1
            #print("history:", self.history, self.history_idx)
            self.cache[-1] = self.prompt_c + self.history[self.history_idx]
            self.current_row = len(self.cache) - 1
            self.current_col = len(self.cache[-1])
        
    def history_next(self):
        self.history_idx += 1
        if self.history_idx > len(self.history) - 1:
            self.history_idx = len(self.history)
        #print("history:", self.history, self.history_idx)
        if len(self.history) > 0:
            if self.history_idx > len(self.history) - 1:
                self.cache[-1] = self.prompt_c
            else:
                self.cache[-1] = self.prompt_c + self.history[self.history_idx]
            #print("history:", self.history, self.history_idx)
            self.current_row = len(self.cache) - 1
            self.current_col = len(self.cache[-1])
