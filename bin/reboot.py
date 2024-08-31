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
        ups.reboot()
        yield Condition(sleep = 0, send_msgs = [
            Message({"output": "reboot ..."}, receiver = shell_id)
        ])
    except Exception as e:
        yield Condition(sleep = 0, send_msgs = [
            Message({"output": str(sys.print_exception(e))}, receiver = shell_id)
        ])

