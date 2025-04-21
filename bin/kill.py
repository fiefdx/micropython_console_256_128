import uos

coroutine = False


def main(*args, **kwargs):
    result = "invalid parameters"
    if len(args) > 0:
        pid = int(args[0])
        scheduler = kwargs["scheduler"]
        task = scheduler.get_task(pid)
        if task:
            scheduler.remove_task(task)
            task.clean()
            result = "task id: %s killed" % pid
        else:
            result = "task id: %s not exist" % pid
    return result
