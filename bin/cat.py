import sys
import uos

from scheduler import Condition, Message
from common import exists, path_join


def main(*args, **kwargs):
    result = "invalid parameters"
    args = kwargs["args"]
    shell_id = kwargs["shell_id"]
    try:
        if len(args) > 0:
            path = args[0]
            if exists(path):
                with open(path, "r") as fp:
                    line = fp.readline()
                    while line:
                        line = line.replace("\r", "")
                        line = line.replace("\n", "")
                        yield Condition.get().load(sleep = 0, send_msgs = [
                            Message.get().load({"output_part": line}, receiver = shell_id)
                        ])
                        line = fp.readline()
                    yield Condition.get().load(sleep = 0, send_msgs = [
                        Message.get().load({"output": ""}, receiver = shell_id)
                    ])
            else:
                yield Condition.get().load(sleep = 0, send_msgs = [
                    Message.get().load({"output": result}, receiver = shell_id)
                ])
        else:
            yield Condition.get().load(sleep = 0, send_msgs = [
                Message.get().load({"output": result}, receiver = shell_id)
            ])
    except Exception as e:
        yield Condition.get().load(sleep = 0, send_msgs = [
            Message.get().load({"output": sys.print_exception(e)}, receiver = shell_id)
        ])
