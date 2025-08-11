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

# from basictoken import BASICToken as Token
# from lexer import Lexer
# from program import Program

from ST75256 import ST75256
import sdcard
# import font8
import font7
# import font6
from writer import Writer
from tile_writer import Writer as TileWriter
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
        yield Condition.get().load(sleep = 1000)
        #yield Condition(sleep = 100, send_msgs = [Message.get().load({"output": monitor_msg}, receiver = scheduler.shell_id)])


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
    tile61 = (
        0b11111111,
        0b10000111,
        0b10110111,
        0b10110111,
        0b10000111,
        0b11111111,
    )
    tile60 = (
        0b00000011,
        0b00000011,
        0b00000011,
        0b00000011,
        0b00000011,
        0b00000011,
    )
    tile41 = (
        0b11111111,
        0b10011111,
        0b10011111,
        0b11111111,
    )
    tile40 = (
        0b00001111,
        0b00001111,
        0b00001111,
        0b00001111,
    )
    tiles = {
        60: {"tile": tile60, "width": const(6), "height": const(6)},
        61: {"tile": tile61, "width": const(6), "height": const(6)},
        40: {"tile": tile40, "width": const(4), "height": const(4)},
        41: {"tile": tile41, "width": const(4), "height": const(4)},
    }
    tile_wri = TileWriter(lcd, tiles)
    while True:
        yield Condition.get().load(sleep = 0, wait_msg = True)
        msg = task.get_message()
        while True:
            try:
                sd_cs.high()
                spi.init(baudrate=62500000, polarity=1, phase=1)
                #spi.init(baudrate=1000000, polarity=1, phase=1)
                # time.sleep_ms(1)
                refresh = False
                t = ticks_ms()
                #print(msg.content)
                if "update_tiles" in msg.content:
                    tile_wri.add_tiles(msg.content["update_tiles"])
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
                    if False and lines.count(False) < 9:
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
                #if scheduler.keyboard.mode == "DF":
                #    lcd.line(127, 0, 127, 5, 0)
                #elif scheduler.keyboard.mode == "SH":
                #    lcd.line(127, 0, 127, 2, 1)
                #elif scheduler.keyboard.mode == "CP":
                #    lcd.line(127, 3, 127, 5, 1)
                if "render" in msg.content:
                    for category in msg.content["render"]:
                        if category == "tiles" and "tiles" in msg.content:
                            refresh = True
                            offset_x = msg.content["tiles"]["offset_x"]
                            offset_y = msg.content["tiles"]["offset_y"]
                            width = msg.content["tiles"]["width"]
                            height = msg.content["tiles"]["height"]
                            size_w = msg.content["tiles"]["size_w"]
                            size_h = msg.content["tiles"]["size_h"]
                            data = msg.content["tiles"]["data"]
                            for w in range(width):
                                x = w * size_w + offset_x
                                for h in range(height):
                                    y = h * size_h + offset_y
                                    tile_wri.print_tile_id(data[h][w], x, y)
                        if category == "objects" and "objects" in msg.content:
                            refresh = True
                            for o in msg.content["objects"]:
                                tile_wri.print_tile_id(o["id"], o["x"], o["y"])
                        if category == "bricks" and "bricks" in msg.content:
                            refresh = True
                            offset_x = msg.content["bricks"]["offset_x"]
                            offset_y = msg.content["bricks"]["offset_y"]
                            width = msg.content["bricks"]["width"]
                            height = msg.content["bricks"]["height"]
                            brick_size = msg.content["bricks"]["size"]
                            data = msg.content["bricks"]["data"]
                            if brick_size == 6:
                                for w in range(width):
                                    x = w * brick_size + offset_x
                                    for h in range(height):
                                        y = h * brick_size + offset_y
                                        if data[h][w] == "o":
                                            # lcd.rect(x, y, brick_size, brick_size, 0)
                                            tile_wri.print_tile_id(60, x, y)
                                        elif data[h][w] == "x":
                                            # lcd.rect(x, y, brick_size, brick_size, 1)
                                            tile_wri.print_tile_id(61, x, y)
                            elif brick_size == 4:
                                for w in range(width):
                                    x = w * brick_size + offset_x
                                    for h in range(height):
                                        y = h * brick_size + offset_y
                                        if data[h][w] == "o":
                                            # lcd.rect(x, y, brick_size, brick_size, 0)
                                            tile_wri.print_tile_id(40, x, y)
                                        elif data[h][w] == "x":
                                            # lcd.rect(x, y, brick_size, brick_size, 1)
                                            tile_wri.print_tile_id(41, x, y)
                        if category == "texts" and "texts" in msg.content:
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
                        if category == "lines" and "lines" in msg.content:
                            refresh = True
                            for line in msg.content["lines"]:
                                xs, ys, xe, ye, invert_color = line
                                lcd.line(xs, ys, xe, ye, 1 if invert_color else 0)
                        if category == "rects" and "rects" in msg.content:
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
                msg.release()
                break
            except Exception as e:
                msg.release()
                sys.print_exception(e)
            
            
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
                    output = sys.modules["%s" % module].main(*args[1:], shell_id = scheduler.shell_id, scheduler = scheduler)
                #exec("del bin.%s" % module)
                exec("del %s" % module)
                del sys.modules["%s" % module].main
                del sys.modules["%s" % module]
                gc.collect()
                #gc.mem_free()
                #if module in ("mount", "umount"):
                #    output, sd, vfs = bin.__dict__[module].main(*args[1:], shell_id = scheduler.shell_id, sd = sd, vfs = vfs, spi = spi, sd_cs = sd_cs)
                #else:
                #    output = bin.__dict__[module].main(*args[1:], shell_id = scheduler.shell_id)
                yield Condition.get().load(sleep = 0, send_msgs = [
                    Message.get().load({"output": output}, receiver = scheduler.shell_id)
                ])
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
    s = Shell(display_size = (41, 18), cache_size = (-1, 50), history_length = 50, scheduler = scheduler, storage_id = storage_id, display_id = display_id)
    s.write_line("           Welcome to TinyShell")
    s.write_char("\n")
    yield Condition.get().load(sleep = 0, send_msgs = [Message.get().load({"frame": s.get_display_frame()}, receiver = display_id)])
    cursor_id = scheduler.add_task(Task.get().load(cursor, "cursor", kwargs = {"interval": 500, "s": s, "display_id": display_id, "storage_id": storage_id}))
    scheduler.shell = s
    s.cursor_id = cursor_id
    while True:
        yield Condition.get().load(sleep = 0, wait_msg = True)
        msg = task.get_message()
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
            
            
def keyboard_input(task, name, scheduler = None, interval = 50, shell_id = None, display_id = None):
    k = KeyBoard()
    scheduler.keyboard = k
    keyboard_mode = k.mode
    key_sound = const(2000)
    while True:
        yield Condition.get().load(sleep = interval)
        key = k.scan()
        #if len(keys) > 0:
            #print(keys)
            #for key in keys:
        volume = k.get_volume()
        if key.startswith("contrast"):
            if volume > 0:
                yield Condition.get().load(sleep = 0, send_msgs = [Message.get().load({"freq": key_sound, "volume": k.get_volume(), "length": 5}, receiver = scheduler.sound_id)])
            yield Condition.get().load(sleep = 0, send_msgs = [Message.get().load({"contrast": key}, receiver = display_id)])
        elif key in ("light-up", "light-down", "volume-up", "volume-down", "SH", "CP"):
            if volume > 0:
                yield Condition.get().load(sleep = 0, send_msgs = [Message.get().load({"freq": key_sound, "volume": k.get_volume(), "length": 5}, receiver = scheduler.sound_id)])
        elif key != "":
            # print("key: ", key)
            if volume > 0:
                yield Condition.get().load(sleep = 0, send_msgs = [Message.get().load({"freq": key_sound, "volume": k.get_volume(), "length": 5}, receiver = scheduler.sound_id)])
            if scheduler.shell and scheduler.shell.session_task_id and scheduler.exists_task(scheduler.shell.session_task_id):
                yield Condition.get().load(sleep = 0, send_msgs = [Message.get().load({"msg": key}, receiver = scheduler.shell.session_task_id)])
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
        if tone_freq >= 20:
            sound_pwm.freq(tone_freq)
            sound_pwm.duty_u16(tone_volume)
        if tone_length < 10:
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
        Message.init_pool(25)
        Condition.init_pool(15)
        Task.init_pool(15)
        s = Scheluder(cpu = 0)
        display_id = s.add_task(Task.get().load(display, "display", condition = Condition.get(), kwargs = {"scheduler": s, "display_cs": display_cs, "sd_cs": sd_cs, "spi": spi}))
        storage_id = s.add_task(Task.get().load(storage, "storage", condition = Condition.get(), kwargs = {"scheduler": s, "display_cs": display_cs, "sd_cs": sd_cs, "spi": spi}))
        # storage_id = None
        sound_id = s.add_task(Task.get().load(sound_output, "sound_output", condition = Condition.get(), kwargs = {"scheduler": s, "sound_pwm": sound_pwm}))
        s.sound_id = sound_id
        shell_id = s.add_task(Task.get().load(shell, "shell", condition = Condition.get(), kwargs = {"scheduler": s, "display_id": display_id, "storage_id": storage_id}))
        s.shell_id = shell_id
        s.set_log_to(shell_id)
        keyboard_id = s.add_task(Task.get().load(keyboard_input, "keyboard_input", condition = Condition.get(), kwargs = {"scheduler": s, "interval": 10, "shell_id": shell_id, "display_id": display_id}))
        #display_id = None
        monitor_id = s.add_task(Task.get().load(monitor, "monitor", condition = Condition.get(), kwargs = {"scheduler": s, "display_id": display_id}))
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

