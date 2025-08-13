import os
import sys
from math import ceil

from scheduler import Condition, Message
from common import exists, path_join, get_size, path_split, mkdirs, rmtree, copy
from bin.edit import EditShell

coroutine = True


class Explorer(object):
    def __init__(self, path = "/", shell = None):
        if len(path) > 1 and path.endswith("/"):
            path = path[:-1]
        self.path = path
        self.shell = shell
        self.pwd = None
        self.current_page = 0
        self.page_size = 16
        self.total_pages = 0
        self.cache = []
        self.files = 0
        self.dirs = 0
        self.total = 0
        self.pointer_row = 0
        self.previous_pointer_row = 0
        self.cursor_x = 0
        self.cursor_y = 1
        self.mode = ""
        self.new_name = ""
        self.name_length_limit = 42
        self.cursor_color = 1
        self.warning = ""
        self.status = ""
        self.copied_item = None
        self.quit = 0
        self.editor = None
        self.load()

    def load(self, force = False):
        if exists(self.path):
            fs = os.ilistdir(self.path)
            if self.pwd != self.path or force:
                self.files = 0
                self.dirs = 0
                for f in fs:
                    p = path_join(self.path, f[0])
                    if f[1] == 16384:
                        self.dirs += 1
                    elif f[1] == 32768:
                        self.files += 1
                self.pwd = self.path
                self.total = self.dirs + self.files
                self.total_pages = ceil(self.total / self.page_size)
                if not force:
                    self.current_page = 0
                    self.previous_pointer_row = self.pointer_row
                    self.pointer_row = 0
                self.cache.clear()
            n = 0
            end = False
            self.cache.clear()
            fs = os.ilistdir(self.path)
            for f in fs:
                p = path_join(self.path, f[0])
                if f[1] == 16384:
                    n += 1
                    if n > self.current_page * self.page_size:
                        self.cache.append((f[0], "D", "   0.00B", p))
                    if n == (self.current_page + 1) * self.page_size:
                        end = True
                        break
            if not end:
                fs = os.ilistdir(self.path)
                for f in fs:
                    p = path_join(self.path, f[0])
                    if f[1] == 32768:
                        size = get_size(f[3])
                        n += 1
                        if n > self.current_page * self.page_size:
                            self.cache.append((f[0], "F", size, p))
                        if n == (self.current_page + 1) * self.page_size:
                            break

    def create_file(self):
        if self.mode == "":
            self.mode = "cf"
            self.new_name = ""
            self.cursor_x = 0
            self.shell.enable_cursor = True

    def create_dir(self):
        if self.mode == "":
            self.mode = "cd"
            self.new_name = ""
            self.cursor_x = 0
            self.shell.enable_cursor = True

    def remove(self):
        if len(self.cache) > self.pointer_row:
            if self.mode == "":
                self.mode = "rm"
        else:
            self.warning = "nothing to delete"

    def copy(self):
        self.status = "copied"
        self.copied_item = (self.cache[self.pointer_row], self.path)

    def cut(self):
        self.status = "cutted"
        self.copied_item = (self.cache[self.pointer_row], self.path)

    def paste(self):
        if self.mode == "" and (self.status == "copied" or self.status == "cutted"):
            self.mode = "paste"
            self.new_name = self.copied_item[0][0]
            self.cursor_x = len(self.new_name)
            self.shell.enable_cursor = True

    def rename(self):
        if self.mode == "":
            self.mode = "rename"
            self.new_name = self.cache[self.pointer_row][0]
            self.cursor_x = len(self.new_name)
            self.shell.enable_cursor = True

    def edit(self, file_path):
        if self.mode == "":
            self.mode = "edit"
            self.editor = EditShell(file_path)
            self.shell.enable_cursor = True
            
    def get_editor_loading_frame(self, p):
        frame = self.editor.get_loading_frame(p)
        frame[0] = " " * 14 + "Editor Opening"
        data = {
            "render": (("clean_pointer", "rects"), ("border_lines", "lines"), ("borders", "rects")),
            "frame": frame,
            "cursor": self.editor.get_cursor_position(1),
            "clean_pointer": [[1, self.previous_pointer_row * 7 + 7, 254, 8, 0], [1, self.pointer_row * 7 + 7, 254, 8, 0]],
            "border_lines": [[188, 8, 188, 118, 0], [206, 8, 206, 118, 0], [2, 1, 2, 125, 0]],
            "borders": [[0, 0, 256, 8, 1], [0, 0, 256, 127, 1], [0, 119, 256, 8, 1]],
        }
        return data

    def get_frame(self):
        path = self.path
        if len(path) > 42:
            n = len(path) - 42 + 3
            path = self.path[:22 - ceil(n/2)] + "..." + self.path[22 + int(n/2):]
        frame = [path]
        contents = []
        borders = [[0, 0, 256, 8, 1], [0, 0, 256, 127, 1], [0, 119, 256, 8, 1]]
        status = [
            {"s": "%s/%s/%s         " % (self.current_page + 1, self.total_pages, self.total), "c": " ", "x": 3, "y": 120},
            {"s": "% 20s" % self.warning, "c": " ", "x": 135, "y": 120}
        ]
        if self.mode == "":
            for f in self.cache:
                name = f[0]
                if len(name) > 31:
                    ext = name.split(".")[-1]
                    if len(ext) > 0:
                        ext = "." + ext
                        name = name[:-len(ext)]
                        name = name[:-(len(name) - (31 - len(ext)) + 3)] + "..." + ext
                else:
                    name += " " * (31 - len(name))
                frame.append("%31s %s %s" % (name, f[1], f[2]))
            border_lines = [[188, 8, 188, 118, 1], [206, 8, 206, 118, 1], [2, 1, 2, 125, 0]]
            clean_pointer = [[1, self.previous_pointer_row * 7 + 7, 254, 8, 0], [0, 7, 256, 8, 0]]
            pointer = [[1, self.pointer_row * 7 + 7, 254, 8, 1]]
        elif self.mode == "edit":
            frame = self.editor.get_display_frame()
            border_lines = [[188, 8, 188, 118, 0], [206, 8, 206, 118, 0], [2, 1, 2, 125, 0]]
            clean_pointer = [[1, self.previous_pointer_row * 7 + 7, 254, 8, 0], [1, self.pointer_row * 7 + 7, 254, 8, 0]]
            borders[0] = [0, 0, 256, 8, 0]
            pointer = []
            status = []
        elif self.mode == "cf":
            for i in range(self.page_size):
                frame.append("")
            frame[0] = " " * 17 + "New File"
            frame[1] = self.new_name
            border_lines = [[188, 8, 188, 118, 0], [206, 8, 206, 118, 0], [2, 1, 2, 125, 0]]
            clean_pointer = [[1, self.previous_pointer_row * 7 + 7, 254, 8, 0], [1, self.pointer_row * 7 + 7, 254, 8, 0]]
            pointer = [[0, 7, 256, 8, 1]]
        elif self.mode == "cd":
            for i in range(self.page_size):
                frame.append("")
            frame[0] = " " * 16 + "New Folder"
            frame[1] = self.new_name
            border_lines = [[188, 8, 188, 118, 0], [206, 8, 206, 118, 0], [2, 1, 2, 125, 0]]
            clean_pointer = [[1, self.previous_pointer_row * 7 + 7, 254, 8, 0], [1, self.pointer_row * 7 + 7, 254, 8, 0]]
            pointer = [[0, 7, 256, 8, 1]]
        elif self.mode == "rm":
            for i in range(self.page_size):
                frame.append("")
            target = self.cache[self.pointer_row]
            if target[1] == "F":
                frame[0] = " " * 15 + "Delete File"
            else:
                frame[0] = " " * 14 + "Delete Folder"
            border_lines = [[188, 8, 188, 118, 0], [206, 8, 206, 118, 0], [2, 1, 2, 125, 0]]
            clean_pointer = [[1, self.previous_pointer_row * 7 + 7, 254, 8, 0], [1, self.pointer_row * 7 + 7, 254, 8, 0]]
            pointer = [[0, 7, 256, 8, 1]]
            contents.append({"s": "Are you sure you want to delete it? [y/n]", "c": " ", "x": 3, "y": 15})
            contents.append({"s": target[0], "c": " ", "x": 3, "y": 8})
        elif self.mode == "paste":
            for i in range(self.page_size):
                frame.append("")
            frame[0] = " " * 18 + "Paste"
            frame[1] = self.new_name
            border_lines = [[188, 8, 188, 118, 0], [206, 8, 206, 118, 0], [2, 1, 2, 125, 0]]
            clean_pointer = [[1, self.previous_pointer_row * 7 + 7, 254, 8, 0], [1, self.pointer_row * 7 + 7, 254, 8, 0]]
            pointer = [[0, 7, 256, 8, 1]]
            contents.append({"s": self.new_name, "c": " ", "x": 3, "y": 8})
        elif self.mode == "rename":
            for i in range(self.page_size):
                frame.append("")
            frame[0] = " " * 17 + "Rename"
            frame[1] = self.new_name
            border_lines = [[188, 8, 188, 118, 0], [206, 8, 206, 118, 0], [2, 1, 2, 125, 0]]
            clean_pointer = [[1, self.previous_pointer_row * 7 + 7, 254, 8, 0], [1, self.pointer_row * 7 + 7, 254, 8, 0]]
            pointer = [[0, 7, 256, 8, 1]]
            contents.append({"s": self.new_name, "c": " ", "x": 3, "y": 8})
        data = {
            "render": (("clean_pointer", "rects"), ("border_lines", "lines"), ("borders", "rects"), ("status", "texts"), ("pointer", "rects"), ("contents", "texts")),
            "frame": frame,
            "clean_pointer": clean_pointer,
            "pointer": pointer,
            "borders": borders,
            "border_lines": border_lines,
            "contents": contents,
            "status": status,
        }
        if self.shell.enable_cursor:
            data["cursor"] = self.get_cursor_position(1)
        return data

    def get_cursor_position(self, c = None):
        if self.mode == "edit":
            return self.editor.get_cursor_position(c)
        else:
            return self.cursor_x, self.cursor_y, self.cursor_color if c is None else c

    def set_cursor_color(self, c):
        if self.mode == "edit":
            self.editor.set_cursor_color(c)
        self.cursor_color = c

    def edit_new_name(self, c):
        if c == "\b":
            delete_before = self.new_name[:self.cursor_x]
            if len(delete_before) > 0:
                self.new_name = self.new_name[:self.cursor_x - 1] + self.new_name[self.cursor_x:]
                self.cursor_x -= 1
        elif c == "LT":
            self.cursor_x -= 1
            if self.cursor_x <= 0:
                self.cursor_x = 0
        elif c == "RT":
            self.cursor_x += 1
            if self.cursor_x >= len(self.new_name):
                self.cursor_x = len(self.new_name)
        elif c == "BB" or c == "ES":
            self.mode = ""
            self.shell.enable_cursor = False
        else:
            if len(c) == 1:
                if len(self.new_name) < self.name_length_limit:
                    self.new_name = self.new_name[:self.cursor_x] + c + self.new_name[self.cursor_x:]
                    self.cursor_x += 1
                    if self.cursor_x >= self.name_length_limit:
                        self.cursor_x = self.name_length_limit

    def input_char(self, c):
        if self.mode == "":
            self.warning = ""
            if c == "UP" or c == "SUP":
                self.previous_pointer_row = self.pointer_row
                self.pointer_row -= 1
                if self.pointer_row <= 0:
                    self.pointer_row = 0
            elif c == "DN" or c == "SDN":
                self.previous_pointer_row = self.pointer_row
                self.pointer_row += 1
                if self.pointer_row >= len(self.cache):
                    self.pointer_row = len(self.cache) - 1
                    if self.pointer_row <= 0:
                        self.pointer_row = 0
            elif c == "LT":
                self.previous_current_page = self.current_page
                self.current_page -= 1
                if self.current_page <= 0:
                    self.current_page = 0
                if self.previous_current_page != self.current_page:
                    self.load()
            elif c == "RT":
                self.previous_current_page = self.current_page
                self.current_page += 1
                if self.current_page >= self.total_pages:
                    self.current_page = self.total_pages - 1
                if self.previous_current_page != self.current_page:
                    self.load()
                    if self.pointer_row >= len(self.cache):
                        self.previous_pointer_row = self.pointer_row
                        self.pointer_row = len(self.cache) - 1
            elif c == "\n" or c == "BA":
                if len(self.cache) > self.pointer_row:
                    f = self.cache[self.pointer_row]
                    if f[1] == "D":
                        self.path = path_join(self.path, f[0])
                        self.load()
                        self.pwd = self.path
                    elif f[1] == "F":
                        file_path = path_join(self.path, f[0])
                        self.edit(file_path)
            elif c == "\b" or c == "BB":
                parent, current = path_split(self.path)
                if parent == "":
                    parent = "/"
                if self.path != parent:
                    self.path = parent
                    self.load()
                    self.pwd = self.path
            elif c == "f":
                self.create_file()
            elif c == "d":
                self.create_dir()
            elif c == "r":
                self.remove()
            elif c == "Ctrl-C":
                self.copy()
            elif c == "Ctrl-X":
                self.cut()
            elif c == "Ctrl-V":
                self.paste()
            elif c == "n":
                self.rename()
        elif self.mode == "cf" or self.mode == "cd":
            if c == "\n" or c == "BA":
                new_name = self.new_name.strip()
                if self.mode == "cf" and new_name != "":
                    path = path_join(self.path, new_name)
                    if not exists(path):
                        with open(path, "w") as fp:
                            pass
                        self.mode = ""
                        self.load(force = True)
                        self.shell.enable_cursor = False
                    else:
                        self.warning = "file exists"
                elif self.mode == "cd" and new_name != "":
                    path = path_join(self.path, new_name)
                    if not exists(path):
                        mkdirs(path)
                        self.mode = ""
                        self.load(force = True)
                        self.shell.enable_cursor = False
                    else:
                        self.warning = "folder exists"
            else:
                self.edit_new_name(c)
        elif self.mode == "rm":
            if c == "y":
                if len(self.cache) > self.pointer_row:
                    target = self.cache[self.pointer_row]
                    path = path_join(self.path, target[0])
                    n = 0
                    if exists(path):
                        for p in rmtree(path):
                            n += 1
                        self.warning = "delete %s items" % n
                        self.load(force = True)
                        if len(self.cache) == 0:
                            self.previous_pointer_row = self.pointer_row
                            self.pointer_row = 0
                        elif len(self.cache) < self.pointer_row:
                            self.previous_pointer_row = self.pointer_row
                            self.pointer_row = len(self.cache) - 1
                        elif len(self.cache) == self.pointer_row:
                            self.previous_pointer_row = self.pointer_row
                            self.pointer_row = len(self.cache) - 1
                self.mode = ""
            elif c == "n":
                self.mode = ""
        elif self.mode == "paste":
            if c == "\n" or c == "BA":
                new_name = self.new_name.strip()
                if new_name != "":
                    n = 0
                    source = path_join(self.copied_item[1], self.copied_item[0][0])
                    target = path_join(self.path, new_name)
                    if exists(source):
                        if not exists(target):
                            for i in copy(source, target):
                                n += 1
                            if self.status == "cutted":
                                for i in rmtree(source):
                                    pass
                            self.mode = ""
                            self.load(force = True)
                            self.shell.enable_cursor = False
                            self.warning = "paste %s items" % n
                        else:
                            self.warning = "target exists"
                    else:
                        self.warning = "source not exists"
                else:
                    self.warning = "invalid name"
            else:
                self.edit_new_name(c)
        elif self.mode == "rename":
            if c == "\n" or c == "BA":
                new_name = self.new_name.strip()
                if new_name != "":
                    source = path_join(self.path, self.cache[self.pointer_row][0])
                    target = path_join(self.path, new_name)
                    if exists(source):
                        if not exists(target):
                            os.rename(source, target)
                            self.mode = ""
                            self.load(force = True)
                            self.shell.enable_cursor = False
                        else:
                            self.warning = "name exists"
                    else:
                        self.warning = "source not exists"
                else:
                    self.warning = "invalid name"
            else:
                self.edit_new_name(c)
        elif self.mode == "edit":
            self.editor.input_char(c)
            if self.editor.exit:
                self.mode = ""
                self.shell.enable_cursor = False
                self.editor.close()
                self.editor = None


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
    try:
        path = os.getcwd()
        if len(kwargs["args"]) > 0:
            path = kwargs["args"][0]
        if len(path) > 1 and path.endswith("/"):
            path = path[:-1]
        if exists(path):
            explorer = Explorer(path, shell)
            shell.current_shell = explorer
            yield Condition.get().load(sleep = 0, wait_msg = True, send_msgs = [
                Message.get().load(explorer.get_frame(), receiver = display_id)
            ])
            msg = task.get_message()
            c = msg.content["msg"]
            while explorer.quit < 3:
                if c == "ES" and explorer.mode != "edit":
                    explorer.quit += 1
                    if explorer.quit == 3:
                        break
                else:
                    explorer.quit = 0
                explorer.input_char(c)
                msg.release()
                if explorer.mode == "edit":
                    if explorer.editor.status != "loading":
                        yield Condition.get().load(sleep = 0, wait_msg = True, send_msgs = [
                            Message.get().load(explorer.get_frame(), receiver = display_id)
                        ])
                    else:
                        for p in explorer.editor.load_and_calc_total_lines():
                            yield Condition.get().load(sleep = 0, wait_msg = False, send_msgs = [
                                Message.get().load(explorer.get_editor_loading_frame(p), receiver = display_id)
                            ])
                        yield Condition.get().load(sleep = 0, wait_msg = True, send_msgs = [
                            Message.get().load(explorer.get_frame(), receiver = display_id)
                        ])
                else:
                    yield Condition.get().load(sleep = 0, wait_msg = True, send_msgs = [
                        Message.get().load(explorer.get_frame(), receiver = display_id)
                    ])
                msg = task.get_message()
                c = msg.content["msg"]
            msg.release()
        else:
            yield Condition.get().load(sleep = 0, send_msgs = [
                Message.get().load({"output": result}, receiver = shell_id)
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
