import sys
from machine import Pin, I2C

from scheduler import Condition, Message
from common import exists, path_join
from ds3231 import ds3231


def main(*args, **kwargs):
    result = "invalid parameters"
    args = kwargs["args"]
    shell_id = kwargs["shell_id"]
    try:
        i2c = I2C(1, scl=Pin(27), sda=Pin(26), freq=100000)
        ups = ds3231(i2c)
        if len(args) > 0:
            ups.set_time(" ".join(args))
            yield Condition(sleep = 0, send_msgs = [
                Message({"output": ups.read_time()}, receiver = shell_id)
            ])
        else:
            yield Condition(sleep = 0, send_msgs = [
                Message({"output": ups.read_time()}, receiver = shell_id)
            ])
    except Exception as e:
        yield Condition(sleep = 0, send_msgs = [
            Message({"output": str(sys.print_exception(e))}, receiver = shell_id)
        ])
