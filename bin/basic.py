import os
import sys
import time
from math import ceil
from io import StringIO

from basictoken import BASICToken as Token
from lexer import Lexer
from program import Program

from shell import Shell
from scheduler import Scheluder, Condition, Task, Message
from common import exists, path_join, isfile, isdir, path_split

print_original = None

class BasicShell(Shell):
    def __init__(self, display_size = (19, 9), cache_size = (-1, 50), history_length = 50, prompt_c = ">", scheduler = None, display_id = None, storage_id = None, history_file_path = "/.basic_history", ram = False):
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
        self.load_history()
        self.clear()
        self.lexer = Lexer()
        Program.print = self.print
        self.program = Program(ram = ram)
        self.run_program_id = None
        self.wait_for_input = False
        self.input_start = None
        self.ram = ram
        #Shell.__init__(self, display_size = display_size, cache_size = cache_size, history_length = history_length, prompt_c = prompt_c, scheduler = scheduler, display_id = display_id, storage_id = storage_id)
        #self.session_task_id = None
        #self.exit = False
        #self.current_shell = None
        
    def clear(self):
        self.term = StringIO()
        os.dupterm(self.term)
        
    def exec_script(self, script, args = []):
        try:
            # exec(script, {"args": args})
            pass
        except Exception as e:
            print(sys.print_exception(e))
        self.term.seek(0)
        lines = self.term.read().strip()
        lines = lines.replace("\r", "")
        self.clear()
        return lines
        
    def input_char(self, c):
        if c == "\n":
            cmd = self.cache[-1].strip()
            if cmd.startswith(self.prompt_c):
                cmd = cmd[len(self.prompt_c):]
            if len(cmd) > 0:
                if cmd == "exit":
                    self.history.append(self.cache[-1][len(self.prompt_c):])
                    self.write_history(self.cache[-1][len(self.prompt_c):])
                    self.exit = True
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
                                print("")

                            # Delete a statement from the program
                            elif tokenlist[0].category == Token.UNSIGNEDINT \
                                    and len(tokenlist) == 1:
                                self.program.delete_statement(int(tokenlist[0].lexeme))
                                print("")

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
                                 print("")

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
                                print("")

                            # Unrecognised input
                            else:
                                print("Unrecognised input", end = "")
                                for token in tokenlist:
                                    token.print_lexeme()
                                print("")
                            if len(lines) > 0:
                                print(lines)
                    except Exception as e:
                        print(sys.print_exception(e))
                        print(e)
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
        elif c == "Ctrl-C":
            self.kill_program()
        else:
            if self.wait_for_input and self.input_start is None:
                self.input_start = len(self.cache[-1])
            self.cache[-1] = self.cache[-1][:self.current_col] + c + self.cache[-1][self.current_col:]
            self.cursor_move_right()
                
        if len(self.cache) > self.cache_lines:
            self.cache.pop(0)
        self.current_row = len(self.cache)
        
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
        
    def print(self, *objects, sep = ' ', end = '\n', file = None, flush = True):
        lines = ""
        for i, o in enumerate(objects):
            lines += str(o).replace("\r", "")
            if i < len(objects) - 1:
                lines += sep # '\n' if sep == '' else sep
        self.write_lines(lines, end = True if end == '\n' else False)
        
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

    def release(self):
        self.history.clear()
        self.cache.clear()
        self.frame_history.clear()
        del self.lexer
        self.program.delete()


def diff_frame(f1, f2):
    if len(f1) != len(f2):
        return True
    for i in range(len(f1)):
        if f1[i] != f2[i]:
            return True
    return False


def main(*args, **kwargs):
    task = args[0]
    name = args[1]
    shell = kwargs["shell"]
    shell_id = kwargs["shell_id"]
    shell.disable_output = True
    global print, print_original
    print_original = print
    try:
        ram = False
        if len(kwargs["args"]) > 0:
            ram = int(kwargs["args"][0])
            ram = True if ram == 1 else False
        if len(kwargs["args"]) > 1:
            file_path = kwargs["args"][0]
            result = []
            if exists(file_path):
                with open(file_path, "r") as fp:
                    content = fp.read()
                    s = BasicShell(display_size = (41, 18), ram = ram)
                    result = s.exec_script(content, args = kwargs["args"][1:])
                shell.disable_output = False
                shell.current_shell = None
                yield Condition.get().load(sleep = 0, wait_msg = False, send_msgs = [
                    Message.get().load({"output": result}, receiver = shell_id)
                ])
            else:
                raise Exception("file[%s] not exists!" % file_path)
        else:
            s = BasicShell(display_size = (41, 18), ram = ram)
            s.scheduler = shell.scheduler
            print = s.print
            Token.print = s.print
            shell.current_shell = s
            s.write_line("   Welcome to PyBasic")
            s.write_char("\n")
            frame_previous = None
            frame = s.get_display_frame()
            yield Condition.get().load(sleep = 0, wait_msg = True, send_msgs = [
                Message.get().load({"frame": frame, "cursor": s.get_cursor_position(1)}, receiver = shell_id)
            ])
            frame_previous = frame
            msg = task.get_message()
            c = msg.content["msg"]
            msg.release()
            while not s.exit:
                # print("char:", c)
                if c != "":
                    s.input_char(c)
                    if not s.exit:
                        frame = s.get_display_frame()
                        if diff_frame(frame, frame_previous):
                            yield Condition.get().load(sleep = 0, wait_msg = False, send_msgs = [
                                Message.get().load({"frame": frame, "cursor": s.get_cursor_position(1)}, receiver = shell_id)
                            ])
                            frame_previous = frame
                        else:
                            yield Condition.get().load(sleep = 0, wait_msg = False)
                    c = ""
                if not s.exit:
                    frame = s.get_display_frame()
                    if diff_frame(frame, frame_previous):
                        yield Condition.get().load(sleep = 0, wait_msg = False, send_msgs = [
                            Message.get().load({"frame": frame, "cursor": s.get_cursor_position(None)}, receiver = shell_id)
                        ])
                        frame_previous = frame
                    else:
                        yield Condition.get().load(sleep = 0, wait_msg = False)
                    msg = task.get_message()
                    if msg:
                        c = msg.content["msg"]
                        msg.release()
            shell.disable_output = False
            shell.current_shell = None
            s.release()
            print = print_original
            yield Condition.get().load(sleep = 0, wait_msg = False, send_msgs = [
                Message.get().load({"output": "quit from PyBasic"}, receiver = shell_id)
            ])
    except Exception as e:
        print = print_original
        print(e)
        shell.disable_output = False
        shell.current_shell = None
        yield Condition.get().load(sleep = 0, send_msgs = [
            Message.get().load({"output": str(e)}, receiver = shell_id)
        ])
