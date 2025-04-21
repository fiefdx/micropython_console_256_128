import sys
import uos

from scheduler import Condition, Message
from common import exists, path_join, isfile, isdir, path_split, mkdirs, copy, copyfile, copydir

coroutine = True


def main(*args, **kwargs):
    result = "invalid parameters"
    task = args[0]
    name = args[1]
    args = kwargs["args"]
    shell_id = kwargs["shell_id"]
    canceled = False
    try:
        if len(args) == 2:
            s_path = args[0]
            t_path = args[1]
            cwd = uos.getcwd()
            if s_path.startswith("."):
                s_path = cwd + s_path[1:]
            if t_path.startswith("."):
                t_path = cwd + t_path[1:]
            for output in copy(s_path, t_path):
                yield Condition.get().load(sleep = 0, send_msgs = [
                    Message.get().load({"output_part": output}, receiver = shell_id)
                ])
                msg = task.get_message()
                if msg:
                    c = msg.content["msg"]
                    msg.release()
                    if c == "ES":
                        canceled = True
                        break
            yield Condition.get().load(sleep = 0, send_msgs = [
                Message.get().load({"output": "canceled" if canceled else ""}, receiver = shell_id)
            ])
        else:
            yield Condition.get().load(sleep = 0, send_msgs = [
                Message.get().load({"output": result}, receiver = shell_id)
            ])
    except Exception as e:
        yield Condition.get().load(sleep = 0, send_msgs = [
            Message.get().load({"output": str(sys.print_exception(e))}, receiver = shell_id)
        ])
