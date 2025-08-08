import sys
import uos
from io import StringIO

from wavePlayer import wavePlayer

from keyboard import KeyBoard
from common import exists, path_join

coroutine = False


def main(*args, **kwargs):
    result = "invalid parameters"
    try:
        if len(args) > 0:
            path = args[0]
            if exists(path) and path.lower().endswith(".wav"):
                k = KeyBoard()
                k.scan_rows = 2
                player = wavePlayer()
                result = player.play(path, k)
    except Exception as e:
        player.stop()
        buf = StringIO()
        sys.print_exception(e, buf)
        result = buf.getvalue()
    return result
