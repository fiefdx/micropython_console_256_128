import gc
import sys

from scheduler import Condition, Message


def main(*args, **kwargs):
    args = kwargs["args"]
    shell_id = kwargs["shell_id"]
    try:
        gc.collect()
        ram_free = gc.mem_free()
        ram_used = gc.mem_alloc()
        monitor_msg = "R%6.2f%%|F%7.2fk/%d|U%7.2fk/%d" % (100.0 - (ram_free * 100 / (264 * 1024)), ram_free / 1024, ram_free, ram_used / 1024, ram_used)
        yield Condition(sleep = 0, send_msgs = [
            Message({"output": monitor_msg}, receiver = shell_id)
        ])
    except Exception as e:
        yield Condition(sleep = 0, send_msgs = [
            Message({"output": str(sys.print_exception(e))}, receiver = shell_id)
        ])