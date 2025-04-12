import uos


def main(*args, **kwargs):
    scheduler = kwargs["scheduler"]
    result = ""
    for i, t in enumerate(scheduler.tasks):
        result += "% 3d: %s\n"  % (t.id, t.name)
    return result[:-1]
