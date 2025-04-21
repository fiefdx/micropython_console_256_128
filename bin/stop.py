from scheduler import Condition, Task, Message

coroutine = False


def main(*args, **kwargs):
    scheduler = kwargs["scheduler"]
    scheduler.stop = True
    return "stoped"
