import socket
import time
import struct


def get_ntp_time():
    ntp_delta = 2208988800 - 3600 * 8
    query = bytearray(48)
    query[0] = 0x1B
    addr = socket.getaddrinfo('asia.pool.ntp.org', 123)[0][-1]
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.settimeout(5)
        r = s.sendto(query, addr)
        m = s.recv(48)
    finally:
        s.close()
    v = struct.unpack("!I", m[40:44])[0]
    t = v - ntp_delta
    return time.gmtime(t) # (2024, 8, 21, 17, 12, 7, 2, 234)
