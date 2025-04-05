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

from basictoken import BASICToken as Token
from lexer import Lexer
from program import Program

from ST75256 import ST75256
import sdcard
# import font8
import font7
# import font6
from writer import Writer
from scheduler import Scheluder, Condition, Task, Message
from common import ticks_ms, ticks_add, ticks_diff, sleep_ms
from shell import Shell
from keyboard import KeyBoard
sys.path.insert(0, "/bin")
sys.path.append("/")

if machine:
    machine.freq(240000000)
    print("freq: %s mhz" % (machine.freq() / 1000000))
if microcontroller:
    microcontroller.cpu.frequency = 200000000
    print("freq: %s mhz" % (microcontroller.cpu.frequency / 1000000))


def monitor(task, name, scheduler = None, display_id = None):
    while True:
        gc.collect()
        #print(int(100 - (gc.mem_free() * 100 / (264 * 1024))), gc.mem_free())
        #monitor_msg = "CPU%s:%3d%%  RAM:%3d%%" % (scheduler.cpu, int(100 - scheduler.idle), int(100 - (scheduler.mem_free() * 100 / (264 * 1024))))
        #print(monitor_msg)
        #print(len(scheduler.tasks))
        yield Condition(sleep = 2000)
        #yield Condition(sleep = 2000, send_msgs = [Message({"msg": monitor_msg}, receiver = display_id)])


def display(task, name, scheduler = None, display_cs = None, sd_cs = None, spi = None):
    sd_cs.high()
    spi.init(baudrate=50000000, polarity=1, phase=1)
    #spi.init(baudrate=1000000, polarity=1, phase=1)
    lcd = ST75256(256, 128, spi, Pin(1), Pin(6), display_cs, rot=0)
    contrast = 0x138
    contrast_max = 0x150
    contrast_min = 0x120
    lcd.contrast(contrast)
    frame_previous = None
    clear_line = " " * 42
    cursor_previous = None
    while True:
        yield Condition(sleep = 0, wait_msg = True)
        msg = task.get_message()
        sd_cs.high()
        spi.init(baudrate=50000000, polarity=1, phase=1)
        #spi.init(baudrate=1000000, polarity=1, phase=1)
        # time.sleep_ms(1)
        refresh = False
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
            #lcd.fill(0)
            #frame_previous = None
            frame = msg.content["frame"]
            #print("frame:", frame)
            lines = [False for i in range(len(frame))]
            if frame_previous:
                if len(frame) < len(frame_previous):
                    lines = [False for i in range(len(frame_previous))]
                #print("frame: ", frame)
                #print("frame_p", frame_previous)
                for n, l in enumerate(frame):
                    #if l == "":
                    #    l = clear_line
                    if n < len(frame_previous):
                        if l != frame_previous[n]:
                            lines[n] = l
                            if l == "":
                                lines[n] = clear_line
                        #elif l == clear_line:
                        #    l = clear_line
                    else:
                        lines[n] = l
                if len(frame_previous) > len(frame):
                    for n in range(len(frame), len(frame_previous)):
                        lines[n] = clear_line
            else:
                lines = frame
            wri = Writer(lcd, font7)
            x = 1
            for n, l in enumerate(lines):
                if l:
                    Writer.set_textpos(lcd, n * 7, x)
                    wri.printstring(clear_line, 0)
                    Writer.set_textpos(lcd, n * 7, x)
                    wri.printstring(l, 0)
            refresh = True
            frame_previous = frame
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
        #if scheduler.keyboard.mode == "DF":
        #    lcd.line(127, 0, 127, 5, 0)
        #elif scheduler.keyboard.mode == "SH":
        #    lcd.line(127, 0, 127, 2, 1)
        #elif scheduler.keyboard.mode == "CP":
        #    lcd.line(127, 3, 127, 5, 1)
        if "bricks" in msg.content:
            refresh = True
            offset_x = msg.content["bricks"]["offset_x"]
            offset_y = msg.content["bricks"]["offset_y"]
            width = msg.content["bricks"]["width"]
            height = msg.content["bricks"]["height"]
            brick_size = msg.content["bricks"]["size"]
            data = msg.content["bricks"]["data"]
            for w in range(width):
                x = w * brick_size + offset_x
                for h in range(height):
                    y = h * brick_size + offset_y
                    if data[h][w] == "o":
                        lcd.rect(x, y, brick_size, brick_size, 0)
                    elif data[h][w] == "x":
                        lcd.rect(x, y, brick_size, brick_size, 1)
        if "texts" in msg.content:
            refresh = True
            for text in msg.content["texts"]:
                x = text["x"]
                y = text["y"]
                c = text["c"]
                s = text["s"]
                wri = Writer(lcd, font7)
                #Writer.set_textpos(lcd, y, x)
                #wri.printstring(c, 0)
                Writer.set_textpos(lcd, y, x)
                wri.printstring(s, 0)
        if "rects" in msg.content:
            refresh = True
            for rect in msg.content["rects"]:
                x, y, w, h = rect
                lcd.rect(x, y, w, h, 1)
        if "binary" in msg.content:
            refresh = True
            data = msg.content["binary"]
            width, height = msg.content["width"], msg.content["height"]
            offset_x, offset_y = msg.content["x"], msg.content["y"]
            invert_color = msg.content["invert"]
            for y in range(height):
                i = 0
                continue_255 = None
                continue_0 = None
                continue_8 = None
                x = 0
                while x < width:
                    b = 7 - (x % 8)
                    if continue_255 is None and data[y][i] == 255:
                        continue_255 = data[y][i+1] * 8
                        lcd.line(x + offset_x, y + offset_y, x + offset_x + continue_255, y + offset_y, 0 if invert_color else 1)
                        x += continue_255
                        i += 2
                        continue_255 = None
                    elif continue_0 is None and data[y][i] == 0:
                        continue_0 = data[y][i+1] * 8
                        lcd.line(x + offset_x, y + offset_y, x + offset_x + continue_0, y + offset_y, 1 if invert_color else 0)
                        x += continue_0
                        i += 2
                        continue_0 = None
                    else:
                        d = data[y][i]
                        if continue_8 is None:
                            continue_8 = 8
                        if continue_8 is not None and continue_8 > 0:
                            continue_8 -= 1
                            if continue_8 == 0:
                                continue_8 = None
                                i += 1
                        c = (d >> b) & 1
                        if invert_color:
                            c ^= 1
                        lcd.pixel(x + offset_x, y + offset_y, c)
                        x += 1
        if refresh:
            lcd.show()
        del msg
            
            
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
        yield Condition(sleep = 0, wait_msg = True)
        msg = task.get_message()
        try:
            display_cs.high() # disable display
            spi.init(baudrate=13200000, polarity=0, phase=0)
            sd_cs.low()
            if "cmd" in msg.content:
                cmd = msg.content["cmd"]
                #print("cmd: ", cmd, len(cmd), sys.path)
                args = cmd.split(" ")
                module = args[0].split(".")[0]
                #if "/sd/usr" not in sys.path:
                #    sys.path.insert(0, "/sd/usr")
                #import bin
                if module not in sys.modules:
                    #import_str = "from bin import %s" % module
                    import_str = "import %s; sys.modules['%s'] = %s" % (module, module, module)
                    #print(import_str)
                    exec(import_str)
                #print(sys.modules)
                if module in ("mount", "umount"):
                    output, sd, vfs = sys.modules["%s" % module].main(*args[1:], shell_id = scheduler.shell_id, sd = sd, vfs = vfs, spi = spi, sd_cs = sd_cs)
                else:
                    output = sys.modules["%s" % module].main(*args[1:], shell_id = scheduler.shell_id)
                #exec("del bin.%s" % module)
                exec("del %s" % module)
                del sys.modules["%s" % module]
                gc.collect()
                #gc.mem_free()
                #if module in ("mount", "umount"):
                #    output, sd, vfs = bin.__dict__[module].main(*args[1:], shell_id = scheduler.shell_id, sd = sd, vfs = vfs, spi = spi, sd_cs = sd_cs)
                #else:
                #    output = bin.__dict__[module].main(*args[1:], shell_id = scheduler.shell_id)
                yield Condition(sleep = 0, send_msgs = [
                    Message({"output": output}, receiver = scheduler.shell_id)
                ])
        except Exception as e:
            yield Condition(sleep = 0, send_msgs = [
                Message({"output": str(e)}, receiver = scheduler.shell_id)
            ])
        del msg


def cursor(task, name, interval = 500, s = None, display_id = None, storage_id = None):
    flash = 0
    n = 0
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
                yield Condition(sleep = interval, send_msgs = [Message({"cursor": s.get_cursor_position()}, receiver = display_id)])
            else:
                x, y, _ = s.get_cursor_position()
                yield Condition(sleep = interval, send_msgs = [Message({"cursor": (x, y, "hide")}, receiver = display_id)])
        else:
            yield Condition(sleep = interval)
        del msg
        
        
def shell(task, name, scheduler = None, display_id = None, storage_id = None):
    yield Condition(sleep = 1000)
    #s = Shell()
    s = Shell(display_size = (41, 18), scheduler = scheduler, storage_id = storage_id, display_id = display_id)
    s.write_line(" Welcome to TinyShell")
    s.write_char("\n")
    yield Condition(sleep = 0, send_msgs = [Message({"frame": s.get_display_frame()}, receiver = display_id)])
    cursor_id = scheduler.add_task(Task(cursor, "cursor", kwargs = {"interval": 500, "s": s, "display_id": display_id, "storage_id": storage_id}))
    scheduler.shell = s
    s.cursor_id = cursor_id
    while True:
        yield Condition(sleep = 0, wait_msg = True)
        msg = task.get_message()
        #print("msg.content: ", msg.content)
        if "clear" in msg.content:
            if not s.disable_output:
                yield Condition(sleep = 0, send_msgs = [
                    Message({"clear": True}, receiver = display_id)
                ])
                yield Condition(sleep = 0, send_msgs = [
                    Message({"frame": s.get_display_frame(), "cursor": s.get_cursor_position(1)}, receiver = display_id)
                ])
        if "keyboard_mode" in msg.content:
            yield Condition(sleep = 0, send_msgs = [
                Message({"keyboard_mode": msg.content["keyboard_mode"]}, receiver = display_id)
            ])
        if "char" in msg.content:
            c = msg.content["char"]
            s.input_char(c)
            if not s.disable_output:
                yield Condition(sleep = 0, send_msgs = [
                    Message({"frame": s.get_display_frame(), "cursor": s.get_cursor_position(1)}, receiver = display_id)
                ])
        elif "output" in msg.content:
            output = msg.content["output"]
            s.write_lines(output, end = True)
            if not s.disable_output:
                yield Condition(sleep = 0, send_msgs = [
                    Message({"frame": s.get_display_frame(), "cursor": s.get_cursor_position(1)}, receiver = display_id)
                ])
        elif "output_part" in msg.content:
            output = msg.content["output_part"]
            s.write_lines(output, end = False)
            if not s.disable_output:
                yield Condition(sleep = 0, send_msgs = [
                    Message({"frame": s.get_display_frame(), "cursor": s.get_cursor_position(1)}, receiver = display_id)
                ])
        elif "output_char" in msg.content:
            c = msg.content["output_char"]
            s.write_char(c)
            if not s.disable_output:
                yield Condition(sleep = 0, send_msgs = [
                    Message({"frame": s.get_display_frame(), "cursor": s.get_cursor_position(1)}, receiver = display_id)
                ])
        elif "frame" in msg.content:
            yield Condition(sleep = 0, send_msgs = [
                Message(msg.content, receiver = display_id)
            ])
        del msg


def keyboard_input_test(task, name, interval = 50, shell_id = None):
    yield Condition(sleep = 2000)
    data = "ls\n"
    i = 0
    while True:
        c = data[i]
        yield Condition(sleep = 1000, send_msgs = [Message({"char": c}, receiver = shell_id)])
        i += 1
        if i >= len(data):
            i = 0
            yield Condition(sleep = 10000)


def display_backlight(task, name, interval = 500, display_id = None):
    while True:
        for duty_cycle in range(0, 65536, 6553):
            display_pwm.duty_u16(duty_cycle)
            print("duty_cycle: ", duty_cycle)
            yield Condition(sleep = interval)
        for duty_cycle in range(65536, 0, -6553):
            display_pwm.duty_u16(duty_cycle)
            yield Condition(sleep = interval)
            print("duty_cycle: ", duty_cycle)
            
            
def keyboard_input(task, name, scheduler = None, interval = 50, shell_id = None, display_id = None):
    k = KeyBoard()
    scheduler.keyboard = k
    keyboard_mode = k.mode
    key_sound = 2000
    while True:
        yield Condition(sleep = interval)
        key = k.scan()
        #if len(keys) > 0:
            #print(keys)
            #for key in keys:
        volume = k.get_volume()
        if key.startswith("contrast"):
            if volume > 0:
                yield Condition(sleep = 0, send_msgs = [Message({"freq": key_sound, "volume": k.get_volume(), "length": 5}, receiver = scheduler.sound_id)])
            yield Condition(sleep = 0, send_msgs = [Message({"contrast": key}, receiver = display_id)])
        elif key in ("light-up", "light-down", "volume-up", "volume-down", "SH", "CP"):
            if volume > 0:
                yield Condition(sleep = 0, send_msgs = [Message({"freq": key_sound, "volume": k.get_volume(), "length": 5}, receiver = scheduler.sound_id)])
        elif key != "":
            # print("key: ", key)
            if volume > 0:
                yield Condition(sleep = 0, send_msgs = [Message({"freq": key_sound, "volume": k.get_volume(), "length": 5}, receiver = scheduler.sound_id)])
            if scheduler.shell and scheduler.shell.session_task_id and scheduler.exists_task(scheduler.shell.session_task_id):
                yield Condition(sleep = 0, send_msgs = [Message({"msg": key}, receiver = scheduler.shell.session_task_id)])
            else:
                yield Condition(sleep = 0, send_msgs = [Message({"char": key}, receiver = shell_id)])
        if keyboard_mode != k.mode:
            keyboard_mode = k.mode
            yield Condition(sleep = 0, send_msgs = [Message({"keyboard_mode": keyboard_mode}, receiver = shell_id)])
        k.clear()
        
        
def sound_output(task, name, scheduler = None, sound_pwm = None):
    while True:
        yield Condition(sleep = 0, wait_msg = True)
        msg = task.get_message()
        tone_freq = msg.content["freq"]
        tone_length = msg.content["length"]
        tone_volume = msg.content["volume"]
        sound_pwm.freq(tone_freq)
        sound_pwm.duty_u16(tone_volume)
        if tone_length < 100:
            sleep_ms(tone_length)
        else:
            yield Condition(sleep = tone_length)
        sound_pwm.duty_u16(0)


def counter(task, name, interval = 100, display_id = None):
    n = 0
    while True:
        if n % 100 == 0:
            yield Condition(sleep = interval, send_msgs = [Message({"msg": "counter: %06d" % n}, receiver = display_id)])
        else:
            yield Condition(sleep = interval)
        n += 1


def core1_thread(scheduler):
    scheduler.run()
    print("core1: exit")


def run_core1(task, name, scheduler = None, start_after = 5000, display_id = None):
    yield Condition(sleep = start_after)
    thread.start_new_thread(core1_thread, (scheduler,))
    yield Condition(send_msgs = [Message({"msg": "start core1"}, receiver = display_id)])


if __name__ == "__main__":
    try:
        led = machine.Pin("LED", machine.Pin.OUT)
        sound_pwm = PWM(Pin(12))
        sd_cs = machine.Pin(9, machine.Pin.OUT)
        display_cs = machine.Pin(5, machine.Pin.OUT)
        spi = SPI(0, baudrate=1000000, polarity=1, phase=1, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
        s = Scheluder(cpu = 0)
        display_id = s.add_task(Task(display, "display", kwargs = {"scheduler": s, "display_cs": display_cs, "sd_cs": sd_cs, "spi": spi}))
        storage_id = s.add_task(Task(storage, "storage", kwargs = {"scheduler": s, "display_cs": display_cs, "sd_cs": sd_cs, "spi": spi}))
        # storage_id = None
        sound_id = s.add_task(Task(sound_output, "sound_output", kwargs = {"scheduler": s, "sound_pwm": sound_pwm}))
        s.sound_id = sound_id
        shell_id = s.add_task(Task(shell, "shell", kwargs = {"scheduler": s, "display_id": display_id, "storage_id": storage_id}))
        s.shell_id = shell_id
        keyboard_id = s.add_task(Task(keyboard_input, "keyboard_input", kwargs = {"scheduler": s, "interval": 10, "shell_id": shell_id, "display_id": display_id}))
        #display_id = None
        monitor_id = s.add_task(Task(monitor, "monitor", kwargs = {"scheduler": s, "display_id": display_id}))
        #counter_id = s.add_task(Task(counter, "counter", kwargs = {"interval": 10, "display_id": display_id}))
        #backlight_id = s.add_task(Task(display_backlight, "display_backlight", kwargs = {"interval": 500, "display_id": display_id}))
        #keyboard_id = s.add_task(Task(test_keyboard, "test_keyboard", kwargs = {"interval": 50, "display_id": display_id}))
        # led.on()
        led.off()
        s.run()
    except Exception as e:
        import sys
        print("main exit: %s" % sys.print_exception(e))
    print("core0 exit")
