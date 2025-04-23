import sys
import uos

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
        result = sys.print_exception(e)
    return result
