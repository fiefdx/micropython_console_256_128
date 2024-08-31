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
        temp = ups.read_temp()
        voltage, P, plugged_in = ups.read_power_status()
        battery_msg = "%5.3fV %3.1fC %3d%% %s" % (voltage, temp, P, "plugged in" if plugged_in else "on battery")
        yield Condition(sleep = 0, send_msgs = [
            Message({"output": battery_msg}, receiver = shell_id)
        ])
    except Exception as e:
        yield Condition(sleep = 0, send_msgs = [
            Message({"output": str(sys.print_exception(e))}, receiver = shell_id)
        ])
