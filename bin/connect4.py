import os
import gc
import sys
import time
import random
from math import ceil
from io import StringIO

from shell import Shell
from scheduler import Condition, Message
from common import exists, path_join, isfile, isdir

coroutine = True





def main(*args, **kwargs):
    #print(kwargs["args"])
    task = args[0]
    name = args[1]
    shell = kwargs["shell"]
    shell_id = kwargs["shell_id"]
    display_id = shell.display_id
    cursor_id = shell.cursor_id
    shell.disable_output = True
    shell.enable_cursor = False
    shell.scheduler.keyboard.scan_rows = 2
    tiles = [
        {"id": 160, "body": {
            "tile": [
                0b00001111,0b11110000,
                0b00010000,0b00001000,
                0b00100000,0b00000100,
                0b01000000,0b00000010,
                0b10000000,0b00000001,
                0b10000000,0b00000001,
                0b10000000,0b00000001,
                0b10000000,0b00000001,
                0b10000000,0b00000001,
                0b10000000,0b00000001,
                0b10000000,0b00000001,
                0b10000000,0b00000001,
                0b01000000,0b00000010,
                0b00100000,0b00000100,
                0b00010000,0b00001000,
                0b00001111,0b11110000],
            "width": 16, "height": 16
        }},
        {"id": 161, "body": {
            "tile": [
                0b00001111,0b11110000,
                0b00011111,0b11111000,
                0b00111111,0b11111100,
                0b01111111,0b11111110,
                0b11111111,0b11111111,
                0b11111111,0b11111111,
                0b11111111,0b11111111,
                0b11111111,0b11111111,
                0b11111111,0b11111111,
                0b11111111,0b11111111,
                0b11111111,0b11111111,
                0b11111111,0b11111111,
                0b01111111,0b11111110,
                0b00111111,0b11111100,
                0b00011111,0b11111000,
                0b00001111,0b11110000],
            "width": 16, "height": 16
        }},
    ]
    try:
        if len(kwargs["args"]) == 0:
            offset_x = 97
            offset_y = 7
            width = 10
            height = 20
            size = 6
            frame_interval = 30
            yield Condition.get().load(sleep = 0, send_msgs = [
                Message.get().load({"clear": True}, receiver = display_id)
            ])
            yield Condition.get().load(sleep = 0, send_msgs = [
                Message.get().load({"update_tiles": tiles}, receiver = cursor_id)
            ])
            yield Condition.get().load(sleep = 0, send_msgs = [
                Message.get().load({"enabled": False}, receiver = cursor_id)
            ])
            yield Condition.get().load(sleep = frame_interval, wait_msg = False, send_msgs = [
                Message.get().load({
                    "tiles": {
                        "data": [[160,161,160,161],
                                 [160,161,160,161],
                                 [160,161,160,161],
                                 [160,161,160,161]],
                        "width": 4,
                        "height": 4,
                        "size_w": 16,
                        "size_y": 16,
                        "offset_x": 10,
                        "offset_y": 10,
                    }
                }, receiver = display_id)
            ])
            
            c = None
            msg = task.get_message()
            if msg:
                c = msg.content["msg"]
                msg.release()
            while c != "ES":
                msg = task.get_message()
                if msg:
                    c = msg.content["msg"]
                    msg.release()
                else:
                    c = None
        else:
            yield Condition.get().load(sleep = 0, send_msgs = [
                Message.get().load({"output": "invalid parameters"}, receiver = shell_id)
            ])
        yield Condition.get().load(sleep = 0, send_msgs = [
            Message.get().load({"clear": True}, receiver = display_id)
        ])
        yield Condition.get().load(sleep = 0, send_msgs = [
            Message.get().load({"enabled": True}, receiver = cursor_id)
        ])
        shell.disable_output = False
        shell.enable_cursor = True
        shell.current_shell = None
        shell.scheduler.keyboard.scan_rows = 5
        yield Condition.get().load(sleep = 0, wait_msg = False, send_msgs = [
            Message.get().load({"output": ""}, receiver = shell_id)
        ])
    except Exception as e:
        yield Condition.get().load(sleep = 0, send_msgs = [
            Message.get().load({"clear": True}, receiver = display_id)
        ])
        yield Condition.get().load(sleep = 0, send_msgs = [
            Message.get().load({"enabled": True}, receiver = cursor_id)
        ])
        shell.disable_output = False
        shell.enable_cursor = True
        shell.current_shell = None
        shell.scheduler.keyboard.scan_rows = 5
        reason = sys.print_exception(e)
        if reason is None:
            reason = "render failed"
        yield Condition.get().load(sleep = 0, send_msgs = [
            Message.get().load({"output": str(reason)}, receiver = shell_id)
        ])
