from machine import Pin, PWM
from micropython import const

from common import sleep_ms


class KeyBoard(object):
    def __init__(self):
        self.volume = 0
        self.volume_min = const(0)
        self.volume_max = const(15)
        self.volume_levels = (0, 100, 200, 500, 1000, 2000, 3000, 5000, 7000, 10000, 15000, 20000, 25000, 30000, 50000)
        self.light = 6
        self.light_min = const(0)
        self.light_max = const(15)
        self.light_levels = (0, 100, 500, 1000, 5000, 6553, 13106, 19659, 26212, 32765, 39318, 45871, 52424, 58977, 65530)
        self.display_pwm = PWM(Pin(8))
        self.display_pwm.freq(1000)
        self.update_light_level()
        self.data_pin = Pin(13, Pin.OUT)
        self.clock_pin = Pin(14, Pin.OUT)
        self.latch_pin = Pin(15, Pin.OUT)
        self.y_lines = [
            Pin(16, Pin.IN, Pin.PULL_UP), # 0
            Pin(17, Pin.IN, Pin.PULL_UP), # 1
            Pin(18, Pin.IN, Pin.PULL_UP), # 2
            Pin(19, Pin.IN, Pin.PULL_UP), # 3
            Pin(20, Pin.IN, Pin.PULL_UP), # 4
        ]
        self.keys = (
            (("UP", "UP", "SUP"), ("DN", "DN", "SDN"), ("LT", "LT", "LT"), ("RT", "RT", "RT"), ("BX", "BX", "light-up"), ("BB", "BB", "light-down"), ("BY", "BY", "volume-down"), ("BA", "BA", "volume-up"), ("", "", ""), ("", "", ""), ("", "", ""), ("", "", "")), # contrast-down, contrast-up
            (("ES", "ES", "ES"), ("q", "Q", "`"), ("w", "W", "~"), ("e", "E", "="), ("r", "R", "_"), ("t", "T", "-"), ("y", "Y", "+"), ("u", "U", "["), ("i", "I", "]"), ("o", "O", "{"), ("p", "P", "}"), ("\b", "\b", "\b")),
            (("CP", "CP", "CP"), ("a", "A", "Ctrl-A"), ("s", "S", "SAVE"), ("d", "D"), ("f", "F"), ("g", "G", "Ctrl-G"), ("h", "H", "Ctrl-H"), ("j", "J"), ("k", "K", "contrast-down"), ("l", "L", "contrast-up"), (";", ";", ":"), ("'", "'", '"')),
            (("SH", "SH", "SH"), ("z", "Z", "Ctrl-Z"), ("x", "X", "Ctrl-X"), ("c", "C", "Ctrl-C"), ("v", "V", "Ctrl-V"), ("b", "B", "Ctrl-B"), ("n", "N"), ("m", "M"), (",", ",", "<"), (".", ".", ">"), ("/", "/", "?"), ("\\", "\\", "|")),
            (("1", "1", "!"), ("2", "2", "@"), ("3", "3", "#"), ("4", "4", "$"), ("5", "5", "%"), (" ", " ", " "), ("\n", "\n", "\n"), ("6", "6", "^"), ("7", "7", "&"), ("8", "8", "*"), ("9", "9", "("), ("0", "0", ")")),
        )
        self.press_buttons = [
            [False, False, False, False, False, False, False, False, False, False, False, False],
            [False, False, False, False, False, False, False, False, False, False, False, False],
            [False, False, False, False, False, False, False, False, False, False, False, False],
            [False, False, False, False, False, False, False, False, False, False, False, False],
            [False, False, False, False, False, False, False, False, False, False, False, False],
        ]
        self.buttons = []
        self.release = []
        self.mode = "DF" # default
        self.button = ""
        self.continue_press_counter = 0
        self.continue_press_interval = const(9)
        self.update_light_level()
        self.scan_rows = 5
        self.game_mode = False
        self.game_press_counters = {"UP": 0, "DN": 0, "LT": 0, "RT": 0, "p": 0, "\b": 0, ";": 0, "'": 0}
        self.disable = False
        
    def get_volume(self):
        return self.volume_levels[self.volume]
        
    def update_scan_lines(self, v, size = 16):
        #put latch down to start data sending
        self.clock_pin.value(0)
        self.latch_pin.value(0)
        self.clock_pin.value(1)
        #load data in reverse order
        for i in range(size - 1, -1, -1):
            self.clock_pin.value(0)
            self.data_pin.value((v >> i) & 1)
            self.clock_pin.value(1)
        #put latch up to store data on register
        self.clock_pin.value(0)
        self.latch_pin.value(1)
        self.clock_pin.value(1)
        
    def update_light_level(self):
        self.display_pwm.duty_u16(self.light_levels[self.light])
        
    def clear(self):
        self.button = ""
        self.buttons.clear()
        
    def scan_keys(self):
        self.buttons.clear()
        for x in range(12):
            self.update_scan_lines(0xffff ^ (1 << x))
            for y in range(2):
                keys = self.keys[y][x]
                key = keys[0]
                if self.y_lines[y].value() == False: # pressd
                    self.buttons.append(key)
        return self.buttons

    def scan(self):
        if self.game_mode:
            self.buttons.clear()
            for x in range(12):
                self.update_scan_lines(0xffff ^ (1 << x))
                for y in range(2):
                    keys = self.keys[y][x]
                    key = keys[0]
                    if self.y_lines[y].value() == False: # pressd
                        if self.press_buttons[y][x]: # already pressed
                            if key in self.game_press_counters:
                                if self.game_press_counters[key] % 6 == 0:
                                    self.buttons.append(key)
                                self.game_press_counters[key] += 1
                        else:
                            if key in self.game_press_counters:
                                if self.game_press_counters[key] == 0:
                                    self.buttons.append(key)
                                    self.game_press_counters[key] += 1
                            else:
                                self.button = key
                        self.press_buttons[y][x] = True
                    else: # not press
                        if self.press_buttons[y][x]:
                            if key in self.game_press_counters:
                                self.game_press_counters[key] = 0
                        self.press_buttons[y][x] = False
        else:
            for x in range(12):
                self.update_scan_lines(0xffff ^ (1 << x))
                for y in range(self.scan_rows):
                    if self.y_lines[y].value() == False: # pressd
                        if self.press_buttons[y][x]: # already pressed
                            if self.continue_press_counter % self.continue_press_interval == 0:
                                keys = self.keys[y][x]
                                key = keys[0]
                                if self.mode == "SH":
                                    if len(keys) > 2:
                                        key = keys[2]
                                elif self.mode == "CP":
                                    key = keys[1]
                                if key == "light-up":
                                    self.light += 1
                                    if self.light >= self.light_max:
                                        self.light = self.light_max - 1
                                    self.update_light_level()
                                elif key == "light-down":
                                    self.light -= 1
                                    if self.light <= 0:
                                        self.light = 0
                                    self.update_light_level()
                                if key == "volume-up":
                                    self.volume += 1
                                    if self.volume >= self.volume_max:
                                        self.volume = self.volume_max - 1
                                elif key == "volume-down":
                                    self.volume -= 1
                                    if self.volume <= 0:
                                        self.volume = 0
                                #if key not in ("light-up", "light-down", "SH", "CP"):
                                self.button = key
                            self.continue_press_counter += 1
                        else:
                            if self.continue_press_counter == 0:
                                keys = self.keys[y][x]
                                key = keys[0]
                                if self.keys[y][x][0] == "SH": # SH mode change
                                    if self.mode == "DF":
                                        self.mode = "SH"
                                    elif self.mode == "SH":
                                        self.mode = "DF"
                                    self.button = "SH"
                                elif self.keys[y][x][0] == "CP": # CP mode change
                                    if self.mode == "DF":
                                        self.mode = "CP"
                                    elif self.mode == "CP":
                                        self.mode = "DF"
                                    self.button = "CP"
                                else: # other keys
                                    if self.mode == "SH":
                                        if len(keys) > 2:
                                            key = keys[2]
                                    elif self.mode == "CP":
                                        key = keys[1]
                                    if key == "light-up":
                                        self.light += 1
                                        if self.light >= self.light_max:
                                            self.light = self.light_max - 1
                                        self.update_light_level()
                                    elif key == "light-down":
                                        self.light -= 1
                                        if self.light <= 0:
                                            self.light = 0
                                        self.update_light_level()
                                    if key == "volume-up":
                                        self.volume += 1
                                        if self.volume >= self.volume_max:
                                            self.volume = self.volume_max - 1
                                    elif key == "volume-down":
                                        self.volume -= 1
                                        if self.volume <= 0:
                                            self.volume = 0
                                    #if key not in ("light-up", "light-down", "SH", "CP"):
                                    self.button = key
                                self.continue_press_counter += 1
                        self.press_buttons[y][x] = True
                        # print("press: ", self.keys[y][x])
                    else: # not press
                        if self.press_buttons[y][x]:
                            if self.continue_press_counter > 0:
                                self.continue_press_counter = 0
                        self.press_buttons[y][x] = False
        return self.button, self.buttons
