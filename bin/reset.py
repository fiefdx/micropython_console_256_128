import sys
import uos
import time
from math import ceil

from scheduler import Condition, Message
from common import exists, path_join, isfile, isdir

coroutine = True


def main(*args, **kwargs):
    task = args[0]
    name = args[1]
    result = "invalid parameters"
    shell = kwargs["shell"]
    shell_id = kwargs["shell_id"]
    display_id = shell.display_id
    try:
        lines = [" "*42 for i in range(50)]
        yield Condition.get().load(sleep = 0, send_msgs = [
            Message.get().load({"clear": True, "output": "\n".join(lines)}, receiver = shell_id)
        ])
    except Exception as e:
        yield Condition.get().load(sleep = 0, send_msgs = [
            Message.get().load({"output": sys.print_exception(e)}, receiver = shell_id)
        ])


