import time

from wifi import WIFI
from scheduler import Condition, Message


def main(*args, **kwargs):
    task = args[0]
    name = args[1]
    shell_id = kwargs["shell_id"]
    try:
        WIFI.active(True)
        yield Condition.get().load(sleep = 0, send_msgs = [
            Message.get().load({"output_part": "connect to: %s" % WIFI.ssid}, receiver = shell_id)
        ])
        WIFI.reconnect()
        s = time.time()
        while not WIFI.is_connect():
            yield Condition.get().load(sleep = 1000, send_msgs = [
                Message.get().load({"output_part": "connecting ..."}, receiver = shell_id)
            ])
            ss = time.time()
            if ss - s >= 10:
                yield Condition.get().load(sleep = 1000, send_msgs = [
                    Message.get().load({"output_part": "connecting too long, check ifconfig later!"}, receiver = shell_id)
                ])
                break
        if WIFI.is_connect():
            yield Condition.get().load(sleep = 1000, send_msgs = [
                Message.get().load({"output": "\n".join(WIFI.ifconfig())}, receiver = shell_id)
            ])
        else:
            yield Condition.get().load(sleep = 0, send_msgs = [
                Message.get().load({"output": "connect to %s failed" % WIFI.ssid}, receiver = shell_id)
            ])
    except Exception as e:
        yield Condition.get().load(sleep = 0, send_msgs = [
            Message.get().load({"output": sys.print_exception(e)}, receiver = shell_id)
        ])
