from scheduler import Condition, Task, Message


def main(*args, **kwargs):
    scheduler = kwargs["scheduler"]
    scheduler.stop = True
    return "stoped"
