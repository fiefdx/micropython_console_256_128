import gc
import sys
from machine import Pin, I2C

from scheduler import Condition, Message
from ds3231 import ds3231

coroutine = True


def main(*args, **kwargs):
    task = args[0]
    name = args[1]
    result = "invalid parameters"
    shell_id = kwargs["shell_id"]
    shell = kwargs["shell"]
    shell.enable_cursor = False
    width, height = 42, 18
    i2c = I2C(1, scl=Pin(27), sda=Pin(26), freq=100000)
    ups = ds3231(i2c)
    try:
        app_exit = False
        while not app_exit:
            try:
                frame = []
                gc.collect()
                frame.append("         %s" % ups.read_time())
                temp = ups.read_temp()
                voltage, P, plugged_in = ups.read_power_status()
                monitor_msg = " CPU%s:%3d%% RAM:%3d%% PM[%s]: %4.2fV %2dC %3d%%" % (shell.scheduler.cpu, int(100 - shell.scheduler.idle), int(100 - (shell.scheduler.mem_free() * 100 / (264 * 1024))), "C" if plugged_in else "B", voltage, temp, P)
                frame.append(monitor_msg)
                for i, t in enumerate(shell.scheduler.tasks):
                    frame.append("%03d %38s"  % (t.id, t.name))
                for i in range(0, height - len(frame)):
                    frame.append("")
                yield Condition.get().load(sleep = 1000, wait_msg = False, send_msgs = [
                    Message.get().load({"output_part": "\n".join(frame[:height])}, receiver = shell_id)
                ])
                yield Condition.get().load(sleep = 1000)
                msg = task.get_message()
                if msg:
                    if msg.content["msg"] == "ES":
                        app_exit = True
                    msg.release()
            except Exception as e:
                print(e)
        yield Condition.get().load(sleep = 0, send_msgs = [
            Message.get().load({"output": ""}, receiver = shell_id)
        ])
        shell.enable_cursor = True
    except Exception as e:
        yield Condition.get().load(sleep = 0, send_msgs = [
            Message.get().load({"output": sys.print_exception(e)}, receiver = shell_id)
        ])
        shell.enable_cursor = True
