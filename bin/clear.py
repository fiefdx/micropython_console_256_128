import uos

from common import exists, path_join

coroutine = False


def main(*args, **kwargs):
    lines = [" "*42 for i in range(50)]
    return "\n".join(lines)

