import sys

import uftpd

from scheduler import Condition, Message
from common import exists, path_join


def main(*args, **kwargs):
    result = "invalid parameters"
    args = kwargs["args"]
    shell_id = kwargs["shell_id"]
    try:
        if len(args) > 0:
            if args[0] == "start":
                r = uftpd.start(splash = False)
                yield Condition(sleep = 0, send_msgs = [
                    Message({"output": r}, receiver = shell_id)
                ])
            elif args[0] == "stop":
                r = uftpd.stop()
                yield Condition(sleep = 0, send_msgs = [
                    Message({"output": r}, receiver = shell_id)
                ])
            elif args[0] == "restart":
                r = uftpd.restart(splash = False)
                yield Condition(sleep = 0, send_msgs = [
                    Message({"output": r}, receiver = shell_id)
                ])
            else:
                yield Condition(sleep = 0, send_msgs = [
                    Message({"output": "Usage: ftpd start|stop|restart"}, receiver = shell_id)
                ])
        else:
            yield Condition(sleep = 0, send_msgs = [
                Message({"output": "Usage: ftpd start|stop|restart"}, receiver = shell_id)
            ])
    except Exception as e:
        yield Condition(sleep = 0, send_msgs = [
            Message({"output": str(sys.print_exception(e))}, receiver = shell_id)
        ])
