import sys
import uos

from scheduler import Condition, Message
from common import exists, path_join, get_size, path_split

coroutine = True


class Explorer(object):
    def __init__(self, path = "/"):
        if len(path) > 1 and path.endswith("/"):
            path = path[:-1]
        self.path = path
        self.pwd = None
        self.current_page = 0
        self.page_size = 16
        self.total_pages = 0
        self.cache = []
        self.files = 0
        self.dirs = 0
        self.total = 0
        self.cursor_row = 0
        self.previous_cursor_row = 0
        self.load()

    def load(self):
        if exists(self.path):
            fs = uos.listdir(self.path)
            if self.pwd != self.path:
                self.files = 0
                self.dirs = 0
                for f in fs:
                    p = path_join(self.path, f)
                    s = uos.stat(p)
                    if s[0] == 16384:
                        self.dirs += 1
                    elif s[0] == 32768:
                        self.files += 1
                self.pwd = self.path
                self.total = self.dirs + self.files
                self.total_pages = round(self.total / self.page_size)
                self.current_page = 0
                self.cache.clear()
            n = 0
            end = False
            self.cache.clear()
            for f in fs:
                p = path_join(self.path, f)
                s = uos.stat(p)
                size = get_size(s[6])
                if s[0] == 16384:
                    n += 1
                    if n > self.current_page * self.page_size:
                        self.cache.append((f, "D", "   0.00B", p))
                    if n == (self.current_page + 1) * self.page_size:
                        end = True
                        break
            if not end:
                for f in fs:
                    p = path_join(self.path, f)
                    s = uos.stat(p)
                    size = get_size(s[6])
                    if s[0] == 32768:
                        n += 1
                        if n > self.current_page * self.page_size:
                            self.cache.append((f, "F", size, p))
                        if n == (self.current_page + 1) * self.page_size:
                            break

    def get_frame(self):
        frame = ["%s T     Size" % ("Name" + " " * 27)]
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
        return {
            "render": (("pointer", "rects"), ("borders", "rects"), ("border_lines", "lines"), ("status", "texts")),
            "frame": frame,
            "pointer": [[1, self.previous_cursor_row * 7 + 7, 254, 8, 0], [1, self.cursor_row * 7 + 7, 254, 8, 1]],
            "borders": [[0, 0, 256, 8, 1], [0, 0, 256, 128, 1], [0, 119, 256, 9, 1]],
            "border_lines": [[191, 0, 191, 119, 1], [203, 0, 203, 119, 1]],
            "status": [{"s": "%s/%s/%s" % (self.current_page + 1, self.total_pages, self.total), "c": " ", "x": 3, "y": 120}]
        }

    def input_char(self, c):
        if c == "UP":
            self.previous_cursor_row = self.cursor_row
            self.cursor_row -= 1
            if self.cursor_row <= 0:
                self.cursor_row = 0
        elif c == "DN":
            self.previous_cursor_row = self.cursor_row
            self.cursor_row += 1
            if self.cursor_row >= self.page_size:
                self.cursor_row = self.page_size - 1
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
        elif c == "\n" or c == "BA":
            f = self.cache[self.cursor_row]
            if f[1] == "D":
                self.path = path_join(self.path, f[0])
                self.load()
                self.pwd = self.path
        elif c == "\b" or c == "BB":
            parent, current = path_split(self.path)
            if parent == "":
                parent = "/"
            if self.path != parent:
                self.path = parent
                self.load()
                self.pwd = self.path



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
        path = uos.getcwd()
        if len(kwargs["args"]) > 0:
            path = kwargs["args"][0]
        if len(path) > 1 and path.endswith("/"):
            path = path[:-1]
        if exists(path):
            explorer = Explorer(path)
            yield Condition.get().load(sleep = 0, wait_msg = True, send_msgs = [
                Message.get().load(explorer.get_frame(), receiver = display_id)
            ])
            msg = task.get_message()
            c = msg.content["msg"]
            while c != "ES":
                explorer.input_char(c)
                msg.release()
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
