import os
import sys
import gc
import time
import uos
machine = None
microcontroller = None
try:
    import machine
except:
    try:
        import microcontroller
    except:
        print("no machine & microcontroller module support")
thread = None
try:
    import _thread as thread
except:
    print("no multi-threading module support")
from machine import Pin, SPI, PWM
from micropython import const

# for pybasic
from basictoken import BASICToken as Token
# from lexer import Lexer
# from program import Program

from ST75256 import ST75256
import sdcard
# import font8
import font7_slow as font7
# import font6
from writer import Writer
from scheduler import Scheluder, Condition, Task, Message
from common import ticks_ms, ticks_add, ticks_diff, sleep_ms
from basic_shell_alone import BasicShell
from keyboard import KeyBoard

if machine:
    machine.freq(240000000)
    print("freq: %s mhz" % (machine.freq() / 1000000))
if microcontroller:
    microcontroller.cpu.frequency = 240000000
    print("freq: %s mhz" % (microcontroller.cpu.frequency / 1000000))


def monitor(task, name, scheduler = None, display_id = None):
    while True:
        gc.collect()
        #print(int(100 - (gc.mem_free() * 100 / (264 * 1024))), gc.mem_free())
        #monitor_msg = "CPU%s:%3d%%  RAM:%3d%%" % (scheduler.cpu, int(100 - scheduler.idle), int(100 - (scheduler.mem_free() * 100 / (264 * 1024))))
        #print(monitor_msg)
        #print(len(scheduler.tasks))
        #scheduler.add_task(Task.get().load(free.main, "test", condition = Condition.get(), kwargs = {"args": [], "shell_id": scheduler.shell_id}))
        # ram_free = gc.mem_free()
        # ram_used = gc.mem_alloc()
        # monitor_msg = "R%6.2f%%|F%7.2fk/%d|U%7.2fk/%d" % (100.0 - (ram_free * 100 / (264 * 1024)),
        #                                                   ram_free / 1024,
        #                                                   ram_free,
        #                                                   ram_used / 1024,
        #                                                   ram_used)
        # print(monitor_msg)
        # print(Message.remain(), Condition.remain(), Task.remain())
        yield Condition.get().load(sleep = 2000)


def display(task, name, scheduler = None, display_cs = None, sd_cs = None, spi = None):
    sd_cs.high()
    # spi.init(baudrate=50000000, polarity=1, phase=1)
    spi.init(baudrate=62500000, polarity=1, phase=1)
    lcd = ST75256(256, 128, spi, Pin(1), Pin(6), display_cs, rot=0)
    contrast = 0x138
    contrast_max = const(0x150)
    contrast_min = const(0x120)
    lcd.contrast(contrast)
    frame_previous = None
    clear_line = const("                                          ")
    cursor_previous = None
    wri = Writer(lcd, font7)
    wri.wrap = False
    while True:
        yield Condition.get().load(sleep = 0, wait_msg = True)
        msg = task.get_message()
        sd_cs.high()
        spi.init(baudrate=62500000, polarity=1, phase=1)
        #spi.init(baudrate=1000000, polarity=1, phase=1)
        # time.sleep_ms(1)
        refresh = False
        #t = ticks_ms()
        #print(msg.content)
        if "contrast" in msg.content:
            if msg.content["contrast"] == "contrast-up":
                contrast += 1
                if contrast >= contrast_max:
                    contrast = contrast_max
            elif msg.content["contrast"] == "contrast-down":
                contrast -= 1
                if contrast <= contrast_min:
                    contrast = contrast_min
            lcd.contrast(contrast)
        if "clear" in msg.content:
            lcd.fill(0)
        if "frame" in msg.content:
            #ttt = ticks_ms()
            #lcd.fill(0)
            frame = msg.content["frame"]
            lines = [False for i in range(len(frame))]
            if frame_previous:
                if len(frame) < len(frame_previous):
                    lines = [False for i in range(len(frame_previous))]
                for n, l in enumerate(frame):
                    if n < len(frame_previous):
                        if l != frame_previous[n]:
                            lines[n] = l
                            if l == "":
                                lines[n] = clear_line
                    else:
                        lines[n] = l
                if len(frame_previous) > len(frame):
                    for n in range(len(frame), len(frame_previous)):
                        lines[n] = clear_line
            else:
                lines = frame
            x = 1
            if lines.count(False) < 9:
                wri.clear_frame(18, 42, 0)
                wri.printframe(frame, 0)
                refresh = True
            else:
                for n, l in enumerate(lines):
                    if l:
                        if l == clear_line:
                            Writer.set_textpos(lcd, n * 7, x)
                            wri.clear_line(42, 0)
                        else:
                            Writer.set_textpos(lcd, n * 7, x)
                            wri.clear_line(42, 0)
                            Writer.set_textpos(lcd, n * 7, x)
                            wri.printstring(l, 0)
                refresh = True
            frame_previous = frame
            #print(">>>", ticks_ms() - ttt), ticks_ms() - tttt)
        if "cursor" in msg.content:
            refresh = True
            x, y, c = msg.content["cursor"]
            if c == "hide":
                #print("hide: ", x, y)
                lcd.line(x * 6, y * 7, x * 6, y * 7 + 5, 0)
            else:
                # print("cursor: ", x, y, c)
                if cursor_previous:
                    xp, yp, cp = cursor_previous
                    #if yp != y or xp > x:
                    lcd.line(xp * 6, yp * 7, xp * 6, yp * 7 + 5, 0)
                    #lcd.line(xp * 6, yp * 8, xp * 6, yp * 8 + 6, 0)
                lcd.line(x * 6, y * 7, x * 6, y * 7 + 5, c)
                #lcd.line(x * 6, y * 8, x * 6, y * 8 + 6, c)
                cursor_previous = [x, y, c]
        if "keyboard_mode" in msg.content:
            keyboard_mode = msg.content["keyboard_mode"]
            if keyboard_mode == "DF":
                lcd.line(1, 127, 10, 127, 0)
            elif keyboard_mode == "SH":
                lcd.line(1, 127, 5, 127, 1)
            elif keyboard_mode == "CP":
                lcd.line(6, 127, 10, 127, 1)
        if refresh:
            lcd.show()
        msg.release()
            
            
def storage(task, name, scheduler = None, display_cs = None, sd_cs = None, spi = None):
    display_cs.high() # disable display
    spi.init(baudrate=13200000, polarity=0, phase=0)
    sd = None
    vfs = None
    try:
        sd = sdcard.SDCard(spi, sd_cs, baudrate=13200000)
        vfs = uos.VfsFat(sd)
        uos.mount(vfs, "/sd")
    except Exception as e:
        print(e)
    while True:
        yield Condition.get().load(sleep = 0, wait_msg = True)
        msg = task.get_message()
        try:
            display_cs.high() # disable display
            spi.init(baudrate=13200000, polarity=0, phase=0)
            sd_cs.low()
        except Exception as e:
            yield Condition.get().load(sleep = 0, send_msgs = [
                Message.get().load({"output": str(e)}, receiver = scheduler.shell_id)
            ])
        msg.release()


def cursor(task, name, interval = 500, s = None, display_id = None, storage_id = None):
    flash = 0
    enabled = True
    while True:
        msg = task.get_message()
        if msg:
            if msg.content["enabled"]:
                enabled = True
            else:
                enabled = False
        if enabled:
            s.set_cursor_color(flash)
            if flash == 0:
                flash = 1
            else:
                flash = 0
            if s.enable_cursor:
                yield Condition.get().load(sleep = interval, send_msgs = [Message.get().load({"cursor": s.get_cursor_position()}, receiver = display_id)])
            else:
                x, y, _ = s.get_cursor_position()
                yield Condition.get().load(sleep = interval, send_msgs = [Message.get().load({"cursor": (x, y, "hide")}, receiver = display_id)])
        else:
            yield Condition.get().load(sleep = interval)
        if msg:
            msg.release()
        
        
def shell(task, name, scheduler = None, display_id = None, storage_id = None):
    yield Condition.get().load(sleep = 1000)
    #s = Shell()
    s = BasicShell(display_size = (41, 18), cache_size = (-1, 36), history_length = 20, scheduler = scheduler, storage_id = storage_id, display_id = display_id)
    # print = s.print
    Token.print = s.print
    s.write_line("            Welcome to PyBASIC")
    s.write_char("\n")
    yield Condition.get().load(sleep = 0, send_msgs = [Message.get().load({"frame": s.get_display_frame()}, receiver = display_id)])
    cursor_id = scheduler.add_task(Task.get().load(cursor, "cursor", kwargs = {"interval": 500, "s": s, "display_id": display_id, "storage_id": storage_id}))
    scheduler.shell = s
    s.cursor_id = cursor_id
    frame_previous = None
    while True:
        yield Condition.get().load(sleep = 0, wait_msg = False)
        msg = task.get_message()
        if msg:
            #print("msg.content: ", msg.content)
            if "clear" in msg.content:
                if not s.disable_output:
                    yield Condition.get().load(sleep = 0, send_msgs = [
                        Message.get().load({"clear": True}, receiver = display_id)
                    ])
                    yield Condition.get().load(sleep = 0, send_msgs = [
                        Message.get().load({"frame": s.get_display_frame(), "cursor": s.get_cursor_position(1)}, receiver = display_id)
                    ])
            if "keyboard_mode" in msg.content:
                yield Condition.get().load(sleep = 0, send_msgs = [
                    Message.get().load({"keyboard_mode": msg.content["keyboard_mode"]}, receiver = display_id)
                ])
            if "char" in msg.content:
                c = msg.content["char"]
                s.input_char(c)
                if not s.disable_output:
                    yield Condition.get().load(sleep = 0, send_msgs = [
                        Message.get().load({"frame": s.get_display_frame(), "cursor": s.get_cursor_position(1)}, receiver = display_id)
                    ])
                else:
                    frame = s.get_display_frame()
                    if s.diff_frame(frame, frame_previous):
                        yield Condition.get().load(sleep = 0, wait_msg = False, send_msgs = [
                            Message.get().load({"frame": frame, "cursor": s.get_cursor_position(1)}, receiver = display_id)
                        ])
                        frame_previous = frame
                    else:
                        yield Condition.get().load(sleep = 0, wait_msg = False)
            elif "output" in msg.content:
                output = msg.content["output"]
                s.write_lines(output, end = True)
                if not s.disable_output:
                    yield Condition.get().load(sleep = 0, send_msgs = [
                        Message.get().load({"frame": s.get_display_frame(), "cursor": s.get_cursor_position(1)}, receiver = display_id)
                    ])
            elif "output_part" in msg.content:
                output = msg.content["output_part"]
                s.write_lines(output, end = False)
                if not s.disable_output:
                    yield Condition.get().load(sleep = 0, send_msgs = [
                        Message.get().load({"frame": s.get_display_frame(), "cursor": s.get_cursor_position(1)}, receiver = display_id)
                    ])
            elif "output_char" in msg.content:
                c = msg.content["output_char"]
                s.write_char(c)
                if not s.disable_output:
                    yield Condition.get().load(sleep = 0, send_msgs = [
                        Message.get().load({"frame": s.get_display_frame(), "cursor": s.get_cursor_position(1)}, receiver = display_id)
                    ])
            elif "frame" in msg.content:
                yield Condition.get().load(sleep = 0, send_msgs = [
                    Message.get().load(msg.content, receiver = display_id)
                ])
            msg.release()
        else:
            frame = s.get_display_frame()
            if s.diff_frame(frame, frame_previous):
                yield Condition.get().load(sleep = 0, wait_msg = False, send_msgs = [
                    Message.get().load({"frame": frame, "cursor": s.get_cursor_position(1)}, receiver = display_id)
                ])
                frame_previous = frame
            else:
                yield Condition.get().load(sleep = 0, wait_msg = False)
            
            
def keyboard_input(task, name, scheduler = None, interval = 50, shell_id = None, display_id = None):
    k = KeyBoard()
    scheduler.keyboard = k
    keyboard_mode = k.mode
    key_sound = const(2000)
    while True:
        yield Condition.get().load(sleep = interval)
        key, keys = k.scan()
        volume = k.get_volume()
        if key.startswith("contrast"):
            if volume > 0:
                yield Condition.get().load(sleep = 0, send_msgs = [Message.get().load({"freq": key_sound, "volume": k.get_volume(), "length": 5}, receiver = scheduler.sound_id)])
            yield Condition.get().load(sleep = 0, send_msgs = [Message.get().load({"contrast": key}, receiver = display_id)])
        elif key in ("light-up", "light-down", "volume-up", "volume-down", "SH", "CP"):
            if volume > 0:
                yield Condition.get().load(sleep = 0, send_msgs = [Message.get().load({"freq": key_sound, "volume": k.get_volume(), "length": 5}, receiver = scheduler.sound_id)])
        elif key != "" or len(keys) > 0:
            if volume > 0:
                yield Condition.get().load(sleep = 0, send_msgs = [Message.get().load({"freq": key_sound, "volume": k.get_volume(), "length": 5}, receiver = scheduler.sound_id)])
            if scheduler.shell and scheduler.shell.session_task_id and scheduler.exists_task(scheduler.shell.session_task_id):
                yield Condition.get().load(sleep = 0, send_msgs = [Message.get().load({"msg": key, "keys": keys}, receiver = scheduler.shell.session_task_id)])
            else:
                yield Condition.get().load(sleep = 0, send_msgs = [Message.get().load({"char": key}, receiver = shell_id)])
        if keyboard_mode != k.mode:
            keyboard_mode = k.mode
            yield Condition.get().load(sleep = 0, send_msgs = [Message.get().load({"keyboard_mode": keyboard_mode}, receiver = shell_id)])
        k.clear()
        
        
def sound_output(task, name, scheduler = None, sound_pwm = None):
    while True:
        yield Condition.get().load(sleep = 0, wait_msg = True)
        msg = task.get_message()
        tone_freq = msg.content["freq"]
        tone_length = msg.content["length"]
        tone_volume = msg.content["volume"]
        sound_pwm.freq(tone_freq)
        sound_pwm.duty_u16(tone_volume)
        if tone_length < 100:
            sleep_ms(tone_length)
        else:
            yield Condition.get().load(sleep = tone_length)
        sound_pwm.duty_u16(0)
        msg.release()


if __name__ == "__main__":
    try:
        led = machine.Pin("LED", machine.Pin.OUT)
        sound_pwm = PWM(Pin(12))
        sd_cs = machine.Pin(9, machine.Pin.OUT)
        display_cs = machine.Pin(5, machine.Pin.OUT)
        spi = SPI(0, baudrate=62500000, polarity=1, phase=1, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
        Message.init_pool(15)
        Condition.init_pool(12)
        Task.init_pool(12)
        s = Scheluder(cpu = 0)
        display_id = s.add_task(Task.get().load(display, "display", condition = Condition.get(), kwargs = {"scheduler": s, "display_cs": display_cs, "sd_cs": sd_cs, "spi": spi}))
        storage_id = s.add_task(Task.get().load(storage, "storage", condition = Condition.get(), kwargs = {"scheduler": s, "display_cs": display_cs, "sd_cs": sd_cs, "spi": spi}))
        # storage_id = None
        sound_id = s.add_task(Task.get().load(sound_output, "sound_output", condition = Condition.get(), kwargs = {"scheduler": s, "sound_pwm": sound_pwm}))
        s.sound_id = sound_id
        shell_id = s.add_task(Task.get().load(shell, "shell", condition = Condition.get(), kwargs = {"scheduler": s, "display_id": display_id, "storage_id": storage_id}))
        s.shell_id = shell_id
        keyboard_id = s.add_task(Task.get().load(keyboard_input, "keyboard_input", condition = Condition.get(), kwargs = {"scheduler": s, "interval": 10, "shell_id": shell_id, "display_id": display_id}))
        #display_id = None
        monitor_id = s.add_task(Task.get().load(monitor, "monitor", condition = Condition.get(), kwargs = {"scheduler": s, "display_id": display_id}))
        # led.on()
        led.off()
        s.run()
    except Exception as e:
        import sys
        print("main exit: %s" % sys.print_exception(e))
    print("core0 exit")
