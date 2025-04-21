from wifi import WIFI

coroutine = False


def main(*args, **kwargs):
    WIFI.active(True)
    return "\n".join(WIFI.ifconfig())