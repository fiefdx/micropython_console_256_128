from scheduler import Condition, Task, Message

coroutine = False


def main(*args, **kwargs):
    scheduler = kwargs["scheduler"]
    result = ""
    for i, t in enumerate(scheduler.tasks):
        result += "%03d: %s\n"  % (t.id, t.name)
    result += "-" * 42 + "\n"
    result += "Message[%s/%s] Condition[%s/%s] Task[%s/%s]" % (
        Message.remain(), len(Message.pool),
        Condition.remain(), len(Condition.pool),
        Task.remain(), len(Task.pool)
    )
    return result
