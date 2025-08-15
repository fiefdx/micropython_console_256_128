import os
import sys
from io import StringIO

from scheduler import Condition, Message
from common import exists, path_join, get_size

coroutine = True


def main(*args, **kwargs):
    task = args[0]
    name = args[1]
    result = "invalid parameters"
    shell_id = kwargs["shell_id"]
    files_total = 0
    dirs_total = 0
    path = os.getcwd()
    if len(kwargs["args"]) > 0:
        path = kwargs["args"][0]
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    try:
        if exists(path):
            fs = os.ilistdir(path)
            max_length = 0
            for f in fs:
                p = path_join(path, f[0])
                size = get_size(f[3]) if len(f) > 3 else ""
                if len(f[0]) + len(size) + 3 > max_length:
                    max_length = len(f[0]) + len(size) + 3
                if f[1] == 16384:
                    dirs_total += 1
                elif f[1] == 32768:
                    files_total += 1
            result = ""
            format_string = "%s|%s|%s"
            if max_length <= 42:
                max_length = 42
            line = format_string % ("Name" + " " * (max_length - 11 - 4), "T", "    Size")
            yield Condition.get().load(sleep = 0, send_msgs = [
                Message.get().load({"output_part": line}, receiver = shell_id)
            ])
            line = "-" * max_length
            yield Condition.get().load(sleep = 0, send_msgs = [
                Message.get().load({"output_part": line}, receiver = shell_id)
            ])
            page_size = 17
            exit = False
            n = 2
            fs = os.ilistdir(path)
            for f in fs:
                p = path_join(path, f[0])
                if f[1] == 16384:
                    line = format_string % (f[0] + " " * (max_length - 11 - len(f[0])), "D", "   0.00B")
                    n += 1
                    if n == page_size:
                        n = 0
                        yield Condition.get().load(sleep = 0, wait_msg = True, send_msgs = [
                            Message.get().load({"output_part": line}, receiver = shell_id)
                        ])
                        msg = task.get_message()
                        while msg.content["msg"] != "ES":
                            if msg.content["msg"] == "\n":
                                break
                            msg.release()
                            yield Condition.get().load(sleep = 0, wait_msg = True)
                            msg = task.get_message()
                        if msg.content["msg"] == "ES":
                            exit = True
                            break
                        msg.release()
                    else:
                        yield Condition.get().load(sleep = 0, send_msgs = [
                            Message.get().load({"output_part": line}, receiver = shell_id)
                        ])
            if not exit:
                fs = os.ilistdir(path)
                for f in fs:
                    p = path_join(path, f[0])
                    size = get_size(f[3]) if len(f) > 3 else ""
                    if f[1] == 32768:
                        line = format_string % (f[0] + " " * (max_length - 11 - len(f[0])), "F", size)
                        n += 1
                        if n == page_size:
                            n = 0
                            yield Condition.get().load(sleep = 0, wait_msg = True, send_msgs = [
                                Message.get().load({"output_part": line}, receiver = shell_id)
                            ])
                            msg = task.get_message()
                            while msg.content["msg"] != "ES":
                                if msg.content["msg"] == "\n":
                                    break
                                msg.release()
                                yield Condition.get().load(sleep = 0, wait_msg = True)
                                msg = task.get_message()
                            if msg.content["msg"] == "ES":
                                exit = True
                                break
                            msg.release()
                        else:
                            yield Condition.get().load(sleep = 0, send_msgs = [
                                Message.get().load({"output_part": line}, receiver = shell_id)
                            ])
            if not exit:
                line = "-" * max_length
                yield Condition.get().load(sleep = 0, send_msgs = [
                    Message.get().load({"output_part": line}, receiver = shell_id)
                ])
                line = "Total: %s, Dirs: %s, Files: %s" % (dirs_total + files_total, dirs_total, files_total)
                yield Condition.get().load(sleep = 0, send_msgs = [
                    Message.get().load({"output": line}, receiver = shell_id)
                ])
            else:
                yield Condition.get().load(sleep = 0, send_msgs = [
                    Message.get().load({"output": ""}, receiver = shell_id)
                ])
        else:
            yield Condition.get().load(sleep = 0, send_msgs = [
                Message.get().load({"output": result}, receiver = shell_id)
            ])
    except Exception as e:
        buf = StringIO()
        sys.print_exception(e, buf)
        yield Condition.get().load(sleep = 0, send_msgs = [
            Message.get().load({"output": buf.getvalue()}, receiver = shell_id)
        ])
