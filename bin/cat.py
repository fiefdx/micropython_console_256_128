import sys
import uos

from scheduler import Condition, Message
from common import exists, path_join

coroutine = True


def main(*args, **kwargs):
    task = args[0]
    name = args[1]
    result = "invalid parameters"
    args = kwargs["args"]
    shell_id = kwargs["shell_id"]
    try:
        if len(args) > 0:
            path = args[0]
            if exists(path):
                n = 0
                page_size = 18
                with open(path, "r") as fp:
                    line = fp.readline()
                    while line:
                        n += 1
                        line = line.replace("\r", "")
                        line = line.replace("\n", "")
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
                                break
                            msg.release()
                        else:
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
