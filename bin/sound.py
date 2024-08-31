import sys

from scheduler import Condition, Message


def main(*args, **kwargs):
    result = "invalid parameters"
    args = kwargs["args"]
    shell_id = kwargs["shell_id"]
    shell = kwargs["shell"]
    try:
        if len(args) >= 3:
            freq = int(args[0])
            volume = int(args[1])
            length = int(args[2])
            yield Condition(sleep = 0, send_msgs = [
                Message({"freq": freq, "volume": volume, "length": length}, receiver = shell.scheduler.sound_id)
            ])
            yield Condition(sleep = 0, send_msgs = [
                Message({"output": ""}, receiver = shell_id)
            ])
        else:
            yield Condition(sleep = 0, send_msgs = [
                Message({"output": result}, receiver = shell_id)
            ])
    except Exception as e:
        yield Condition(sleep = 0, send_msgs = [
            Message({"output": str(sys.print_exception(e))}, receiver = shell_id)
        ])

