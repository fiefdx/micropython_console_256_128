import os
import sys
import uos
import gc
import time
import machine
from math import ceil
from io import StringIO
from machine import Pin, I2C
from micropython import const

from basictoken import BASICToken as Token
from lexer import Lexer
from program import Program

from shell import Shell
from listfile import ListFile
from scheduler import Scheluder, Condition, Task, Message
from common import exists, path_join, isfile, isdir, path_split, mkdirs, copy, get_size, copyfile, copydir, rmtree
from ds3231 import ds3231


class BasicShell(Shell):
    def __init__(self, display_size = (19, 9), cache_size = (-1, 50), history_length = 50, prompt_c = ">", scheduler = None, display_id = None, storage_id = None, history_file_path = "/.history_basic", bin_path = "/bin", ram = False):
        self.display_width = const(display_size[0])
        self.display_height = const(display_size[1])
        self.display_width_with_prompt = const(display_size[0] + len(prompt_c))
        self.history_length = const(history_length)
        self.prompt_c = const(prompt_c)
        self.history = []
        self.cache_width = const(cache_size[0])
        self.cache_lines = const(cache_size[1])
        self.cache = []
        self.cursor_color = 1
        self.current_row = 0
        self.current_col = 0
        self.scheduler = scheduler
        self.display_id = const(display_id)
        self.storage_id = const(storage_id)
        self.cursor_row = 0
        self.cursor_col = 0
        self.history_idx = 0
        self.scroll_row = 0
        self.frame_history = []
        self.session_task_id = None
        self.disable_output = False
        self.current_shell = None
        self.enable_cursor = True
        self.history_file_path = const(history_file_path)
        self.bin_path = const(bin_path)
        self.load_history()
        self.lexer = Lexer()
        Program.print = self.print
        self.program = Program(ram = ram)
        self.run_program_id = None
        self.wait_for_input = False
        self.input_start = None
        self.ram = ram
        self.input_counter = 0
        #Shell.__init__(self, display_size = display_size, cache_size = cache_size, history_length = history_length, prompt_c = prompt_c, scheduler = scheduler, display_id = display_id, storage_id = storage_id)
        #self.session_task_id = None
        #self.exit = False
        #self.current_shell = None
        
    def input_char(self, c):
        if c == "\n":
            cmd = self.cache[-1].strip()
            if cmd.startswith(self.prompt_c):
                cmd = cmd[len(self.prompt_c):]
            if len(cmd) > 0:
                if cmd.lower() == "exit":
                    self.history.append(self.cache[-1][len(self.prompt_c):])
                    self.write_history(self.cache[-1][len(self.prompt_c):])
                    if exists("/main.basic.py"):
                        uos.rename("/main.py", "/main.shell.py")
                        uos.rename("/main.basic.py", "/main.py")
                        machine.soft_reset()
                    elif exists("/main.shell.py"):
                        uos.rename("/main.py", "/main.basic.py")
                        uos.rename("/main.shell.py", "/main.py")
                        machine.soft_reset()
                elif cmd.startswith("ls"):
                    self.history.append(self.cache[-1][len(self.prompt_c):])
                    self.write_history(self.cache[-1][len(self.prompt_c):])
                    p = cmd.replace("ls", "").strip()
                    args = [p] if len(p) > 0 else []
                    self.print(self.ls(args))
                elif cmd.startswith("cd"):
                    self.history.append(self.cache[-1][len(self.prompt_c):])
                    self.write_history(self.cache[-1][len(self.prompt_c):])
                    p = cmd.replace("cd", "").strip()
                    args = [p] if len(p) > 0 else []
                    self.print(self.cd(args))
                elif cmd.startswith("pwd"):
                    self.history.append(self.cache[-1][len(self.prompt_c):])
                    self.write_history(self.cache[-1][len(self.prompt_c):])
                    self.print(self.pwd())
                elif cmd.startswith("rm"):
                    self.history.append(self.cache[-1][len(self.prompt_c):])
                    self.write_history(self.cache[-1][len(self.prompt_c):])
                    p = cmd.replace("rm", "").strip()
                    args = [p] if len(p) > 0 else []
                    self.print(self.rm(args))
                elif cmd.startswith("mkdir"):
                    self.history.append(self.cache[-1][len(self.prompt_c):])
                    self.write_history(self.cache[-1][len(self.prompt_c):])
                    p = cmd.replace("mkdir", "").strip()
                    args = [p] if len(p) > 0 else []
                    self.print(self.mkdir(args))
                elif cmd.startswith("free"):
                    self.history.append(self.cache[-1][len(self.prompt_c):])
                    self.write_history(self.cache[-1][len(self.prompt_c):])
                    self.print(self.free())
                elif cmd.startswith("reboot"):
                    self.history.append(self.cache[-1][len(self.prompt_c):])
                    self.write_history(self.cache[-1][len(self.prompt_c):])
                    self.print(self.reboot())
                elif cmd.startswith("shutdown"):
                    self.history.append(self.cache[-1][len(self.prompt_c):])
                    self.write_history(self.cache[-1][len(self.prompt_c):])
                    self.print(self.shutdown())
                elif self.run_program_id != None:
                    self.send_input_hook(self.cache[-1])
                    self.print("")
                else:
                    self.history.append(self.cache[-1][len(self.prompt_c):])
                    self.write_history(self.cache[-1][len(self.prompt_c):])
                    try:
                        lines = ""
                        tokenlist = self.lexer.tokenize(cmd)

                        # Execute commands directly, otherwise
                        # add program statements to the stored
                        # BASIC program

                        if len(tokenlist) > 0:

                            # Add a new program statement, beginning
                            # a line number
                            if tokenlist[0].category == Token.UNSIGNEDINT\
                                 and len(tokenlist) > 1:
                                self.program.add_stmt(tokenlist)
                                self.print("")

                            # Delete a statement from the program
                            elif tokenlist[0].category == Token.UNSIGNEDINT \
                                    and len(tokenlist) == 1:
                                self.program.delete_statement(int(tokenlist[0].lexeme))
                                self.print("")

                            # Execute the program
                            elif tokenlist[0].category == Token.RUN:
                                self.run_program_id = self.scheduler.add_task(
                                    Task.get().load(self.program.execute,
                                         "basic-execute",
                                         condition = Condition.get(),
                                         kwargs = {"execute_print": self.execute_print, "shell": self}
                                    )
                                )
                                self.print("")

                            # List the program
                            elif tokenlist[0].category == Token.LIST:
                                 if len(tokenlist) == 2:
                                     self.program.list(int(tokenlist[1].lexeme),int(tokenlist[1].lexeme))
                                 elif len(tokenlist) == 3:
                                     # if we have 3 tokens, it might be LIST x y for a range
                                     # or LIST -y or list x- for a start to y, or x to end
                                     if tokenlist[1].lexeme == "-":
                                         self.program.list(None, int(tokenlist[2].lexeme))
                                     elif tokenlist[2].lexeme == "-":
                                         self.program.list(int(tokenlist[1].lexeme), None)
                                     else:
                                         self.program.list(int(tokenlist[1].lexeme),int(tokenlist[2].lexeme))
                                 elif len(tokenlist) == 4:
                                     # if we have 4, assume LIST x-y or some other
                                     # delimiter for a range
                                     self.program.list(int(tokenlist[1].lexeme),int(tokenlist[3].lexeme))
                                 else:
                                     self.program.list()
                                 self.print("")

                            # Save the program to disk
                            elif tokenlist[0].category == Token.SAVE:
                                self.program.save(tokenlist[1].lexeme)
                                lines += "Program written to file\n"

                            # Load the program from disk
                            elif tokenlist[0].category == Token.LOAD:
                                self.program.load(tokenlist[1].lexeme)
                                lines += "Program read from file\n"

                            # Delete the program from memory
                            elif tokenlist[0].category == Token.NEW:
                                self.program.delete()
                                self.print("")                                

                            # Unrecognised input
                            else:
                                self.print("Unrecognised input", end = "")
                                for token in tokenlist:
                                    token.print_lexeme()
                                self.print("")
                            if len(lines) > 0:
                                self.print(lines)
                    except Exception as e:
                        self.print(e)
            else:
                self.cache.append(self.prompt_c)
                self.cache_to_frame_history()
            if len(self.history) > self.history_length:
                self.history.pop(0)
            self.history_idx = len(self.history)
            self.input_counter += 1
        elif c == "\b":
            if len(self.cache[-1][:self.current_col]) > len(self.prompt_c):
                self.cache[-1] = self.cache[-1][:self.current_col-1] + self.cache[-1][self.current_col:]
                self.cursor_move_left()
                self.input_counter += 1
        elif c == "BX":
            self.scroll_up()
            self.input_counter += 1
        elif c == "BB":
            self.scroll_down()
            self.input_counter += 1
        elif c == "UP":
            self.history_previous()
            self.input_counter += 1
        elif c == "DN":
            self.history_next()
            self.input_counter += 1
        elif c == "LT":
            self.cursor_move_left()
            self.input_counter += 1
        elif c == "RT":
            self.cursor_move_right()
            self.input_counter += 1
        elif c == "ES":
            pass
        elif c == "Ctrl-C":
            self.kill_program()
        elif len(c) == 1:
            if self.wait_for_input and self.input_start is None:
                self.input_start = len(self.cache[-1])
            self.cache[-1] = self.cache[-1][:self.current_col] + c + self.cache[-1][self.current_col:]
            self.cursor_move_right()
                
        if len(self.cache) > self.cache_lines:
            self.cache.pop(0)
        self.current_row = len(self.cache)

    def free(self):
        gc.collect()
        ram_free = gc.mem_free()
        ram_used = gc.mem_alloc()
        message = "R%6.2f%%|F%7.2fk/%d|U%7.2fk/%d\n" % (100.0 - (ram_free * 100 / (264 * 1024)),
                                                        ram_free / 1024,
                                                        ram_free,
                                                        ram_used / 1024,
                                                        ram_used)
        message += "Message[%s/%s] Condition[%s/%s] Task[%s/%s]" % (
            Message.remain(), len(Message.pool),
            Condition.remain(), len(Condition.pool),
            Task.remain(), len(Task.pool)
        )
        return message

    def ls(self, args = []):
        files = []
        dirs = []
        path = uos.getcwd()
        if len(args) > 0:
            path = args[0]
        if len(path) > 1 and path.endswith("/"):
            path = path[:-1]
        fs = uos.listdir(path)
        for f in fs:
            p = path_join(path, f)
            s = uos.stat(p)
            if s[0] == 16384:
                dirs.append("D:" + f)
            elif s[0] == 32768:
                files.append("F:" + f)
        result = "\n".join(dirs) + "\n" + "\n".join(files)
        return result

    def pwd(self):
        return uos.getcwd()

    def cd(self, args = []):
        result = "path invalid"
        path = "/sd"
        if len(args) > 0:
            path = args[0]
        if exists(path) and uos.stat(path)[0] == 16384:
            uos.chdir(path)
            result = path
        return result

    def rm(self, args = []):
        result = "invalid parameters"
        if len(args) == 1:
            t_path = args[0]
            cwd = uos.getcwd()
            if t_path.startswith("."):
                t_path = cwd + t_path[1:]
            n = 1
            result = ""
            for output in rmtree(t_path):
                n += 1
                result += output + "\n"
            result = result[:-1]
        return result

    def mkdir(self, args = []):
        result = "already exists!"
        cwd = uos.getcwd()
        if len(args) > 0:
            path = args[0]
            if path.startswith("."):
                path = cwd + path[1:]
            if path.endswith("/"):
                path = path[:-1]
            if not exists(path):
                mkdirs(path)
                result = path
        return result

    def reboot(self):
        i2c = I2C(1, scl=Pin(27), sda=Pin(26), freq=100000)
        ups = ds3231(i2c)
        ups.reboot()

    def shutdown(self):
        i2c = I2C(1, scl=Pin(27), sda=Pin(26), freq=100000)
        ups = ds3231(i2c)
        ups.power_off()
        
    def kill_task(self, task, name):
        yield Condition.get().load(sleep = 0, send_msgs = [Message.get().load({"msg": "Ctrl-C"}, receiver = self.run_program_id)])
        self.run_program_id = None
        
    def kill_program(self):
        if self.run_program_id != None:
            #self.run_program_id = None
            self.scheduler.add_task(Task.get().load(self.kill_task, "kill", condition = Condition.get(), kwargs = {}))
            
    def send_input(self, task, name, msg = ""):
        yield Condition.get().load(sleep = 0, send_msgs = [Message.get().load({"msg": msg}, receiver = self.run_program_id)])
    
    def send_input_hook(self, line):
        self.scheduler.add_task(Task.get().load(self.send_input, "send_input", condition = Condition.get(), kwargs = {"msg": line[self.input_start:]}))
        self.wait_for_input = False
        self.input_start = None
        
    def write_char(self, c, terminated = False):
        if c == "\n":
            if self.run_program_id is None or terminated:
                self.cache.append(self.prompt_c)
            else:
                self.cache.append("")
        else:
            self.cache[-1] += c
            if len(self.cache[-1]) > self.display_width_with_prompt:
                self.cache.append(" " + self.cache[-1][self.display_width_with_prompt:])
                self.cache[-2] = self.cache[-2][:display_width_with_prompt]
                
        if len(self.cache) > self.cache_lines:
            self.cache.pop(0)
        self.current_row = len(self.cache) - 1
        self.current_col = len(self.cache[-1])
        self.input_counter += 1
        
    def print(self, *objects, sep = ' ', end = '\n', file = None, flush = True):
        lines = ""
        for i, o in enumerate(objects):
            lines += str(o).replace("\r", "")
            if i < len(objects) - 1:
                lines += sep # '\n' if sep == '' else sep
        self.write_lines(lines, end = True if end == '\n' else False)
        self.input_counter += 1
        
    def write_lines(self, lines, end = True):
        lines = lines.split("\n")
        for line in lines:
            if len(line) > 0:
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
        
    def execute_print(self, *objects, sep = ' ', end = '', file = None, flush = True, terminated = False):
        lines = ""
        for i, o in enumerate(objects):
            lines += str(o).replace("\r", "").replace("\t", " ")
            if i < len(objects) - 1:
                lines += sep # '\n' if sep == '' else sep
        self.execute_write_lines(lines, end = True if end == '\n' else False, terminated = terminated)
        self.input_counter += 1
        
    def execute_write_lines(self, lines, end = True, terminated = False):
        #lines = lines.split("\n")
        lines = [lines]
        for line in lines:
            if len(line) > 0:
                line = line.replace("\r", "")
                line = line.replace("\n", "")
                if self.wait_for_input:
                    self.cache[-1] += line
                else:
                    #if line.endswith("\n"):
                    #    self.cache[-1] += line
                    #    self.cache.append("")
                    #else:
                    self.cache[-1] += line
                    #self.cache.append(line)
                if len(self.cache) > self.cache_lines:
                    self.cache.pop(0)
                self.current_row = len(self.cache) - 1
                self.current_col = len(self.cache[-1])
        if end:
            self.write_char("\n", terminated = terminated)
        self.cache_to_frame_history()

    def diff_frame(self, f1, f2):
        if f1 is None or f2 is None:
            return True
        elif len(f1) != len(f2):
            return True
        for i in range(len(f1)):
            if f1[i] != f2[i]:
                return True
        return False