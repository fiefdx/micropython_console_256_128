import uos
import machine

from scheduler import Condition, Task, Message
from common import exists, path_join, isfile, isdir, path_split, mkdirs, copy


def main(*args, **kwargs):
    scheduler = kwargs["scheduler"]
    if exists("/main.basic.py"):
        uos.rename("/main.py", "/main.shell.py")
        uos.rename("/main.basic.py", "/main.py")
        machine.soft_reset()
