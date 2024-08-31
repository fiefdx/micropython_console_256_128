from scheduler import Condition, Message


def main(*args, **kwargs):
    task = args[0]
    name = args[1]
    shell_id = kwargs["shell_id"]
    shell = kwargs["shell"]
    try:
        yield Condition(sleep = 0, send_msgs = [
            Message({"output": shell.help_commands()}, receiver = shell_id)
        ])
    except Exception as e:
        yield Condition(sleep = 0, send_msgs = [
            Message({"output": sys.print_exception(e)}, receiver = shell_id)
        ])