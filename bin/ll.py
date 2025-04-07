import uos

from common import exists, path_join, get_size


def main(*args, **kwargs):
    files = []
    dirs = []
    path = uos.getcwd()
    if len(args) > 0:
        path = args[0]
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    fs = uos.listdir(path)
    max_length = 0
    for f in fs:
        p = path_join(path, f)
        s = uos.stat(p)
        size = get_size(s[6])
        if len(f) + len(size) + 3 > max_length:
            max_length = len(f) + len(size) + 3
        if s[0] == 16384:
            dirs.append((f, "   0.00B"))
        elif s[0] == 32768:
            files.append((f, size))
    result = ""
    format_string = "%s|%s|%s"
    if max_length <= 42:
        max_length = 42
    result += (format_string + "\n") % ("Name" + " " * (max_length - 11 - 4), "T", "    Size")
    result += "-" * max_length + "\n"
    for d in dirs:
        result += (format_string + "\n") % (d[0] + " " * (max_length - 11 - len(d[0])), "D", d[1])
    for f in files:
        result += (format_string + "\n") % (f[0] + " " * (max_length - 11 - len(f[0])), "F", f[1])
    result += "-" * max_length + "\n"
    result += "Total: %s, Dirs: %s, Files: %s" % (len(dirs) + len(files), len(dirs), len(files))
    return result
