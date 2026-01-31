import os
import sys
import socket
import traceback
import logging
import math
import time
import random
import pygame
import threading
from threading import Thread
from queue import Queue, Empty

import logger

LOG = logging.getLogger(__name__)

__version__ = "0.0.1"

os.environ['SDL_VIDEO_CENTERED'] = '1'

TaskQueue = Queue(5)
ResultQueue = Queue(5)


class StoppableThread(Thread):
    def __init__(self):
        super(StoppableThread, self).__init__()
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()


class WorkThread(StoppableThread):
    def __init__(self, task_queue, result_queue):
        StoppableThread.__init__(self)
        Thread.__init__(self)
        self.task_queue = task_queue
        self.result_queue = result_queue

    def run(self):
        try:
            while True:
                if not self.stopped():
                    try:
                        task = self.task_queue.get(block = False)
                        if task:
                            time.sleep(0.1)
                        else:
                            time.sleep(0.1)
                    except Empty:
                        time.sleep(0.1)
                else:
                    break
        except Exception as e:
            print(e)


class UserInterface(object):
    def __init__(self, host, port, work_thread, task_queue, result_queue):
        pygame.init()
        pygame.mixer.init()
        self.window = pygame.display.set_mode((512, 128)) # pygame.FULLSCREEN | pygame.SCALED) # , pygame.RESIZABLE)
        pygame.display.set_caption("RemoteKeyboard - v%s" % __version__)
        pygame.display.set_icon(pygame.image.load("icon.png"))

        self.host = host
        self.port = port
        self.work_thread = work_thread
        self.font_command = pygame.font.SysFont('Arial', 70)
        self.font = pygame.font.SysFont('Arial', 20)
        self.chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ`1234567890-=[]\\;',./~!@#$%^&*()_+{}|:\"<>? \b\n"
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((self.host, self.port))
        self.input = ""
        self.input_max_length = 10

        self.keys = {
            pygame.K_ESCAPE: ("ES", "ES"),
            pygame.K_RETURN: ("\n", "\n"),
            pygame.K_SPACE: (" ", " "),
            pygame.K_BACKSPACE: ("\b", "\b"),
            pygame.K_a: ("a", "A"),
            pygame.K_b: ("b", "B"),
            pygame.K_c: ("c", "C"),
            pygame.K_d: ("d", "D"),
            pygame.K_e: ("e", "E"),
            pygame.K_f: ("f", "F"),
            pygame.K_g: ("g", "G"),
            pygame.K_h: ("h", "H"),
            pygame.K_i: ("i", "I"),
            pygame.K_j: ("j", "J"),
            pygame.K_k: ("k", "K"),
            pygame.K_l: ("l", "L"),
            pygame.K_m: ("m", "M"),
            pygame.K_n: ("n", "N"),
            pygame.K_o: ("o", "O"),
            pygame.K_p: ("p", "P"),
            pygame.K_q: ("q", "Q"),
            pygame.K_r: ("r", "R"),
            pygame.K_s: ("s", "S"),
            pygame.K_t: ("t", "T"),
            pygame.K_u: ("u", "U"),
            pygame.K_v: ("v", "V"),
            pygame.K_w: ("w", "W"),
            pygame.K_x: ("x", "X"),
            pygame.K_y: ("y", "Y"),
            pygame.K_z: ("z", "Z"),
            pygame.K_BACKQUOTE: ("`", "~"),
            pygame.K_1: ("1", "!"),
            pygame.K_2: ("2", "@"),
            pygame.K_3: ("3", "#"),
            pygame.K_4: ("4", "$"),
            pygame.K_5: ("5", "%"),
            pygame.K_6: ("6", "^"),
            pygame.K_7: ("7", "&"),
            pygame.K_8: ("8", "*"),
            pygame.K_9: ("9", "("),
            pygame.K_0: ("0", ")"),
            pygame.K_MINUS: ("-", "_"),
            pygame.K_EQUALS: ("=", "+"),
            pygame.K_LEFTBRACKET: ("[", "{"),
            pygame.K_RIGHTBRACKET: ("]", "}"),
            pygame.K_BACKSLASH: ("\\", "|"),
            pygame.K_SEMICOLON: (";", ":"),
            pygame.K_QUOTE: ("'", "\""),
            pygame.K_COMMA: (",", "<"),
            pygame.K_PERIOD: (".", ">"),
            pygame.K_SLASH: ("/", "?"),
            pygame.K_UP: ("UP", "UP"),
            pygame.K_DOWN: ("DN", "DN"),
            pygame.K_LEFT: ("LT", "LT"),
            pygame.K_RIGHT: ("RT", "RT"),
            pygame.K_PAGEUP: ("SUP", "SUP"),
            pygame.K_PAGEDOWN: ("SDN", "SDN"),
        }
        self.key_pressed = None
        self.key_pressed_status = False
        self.key_pressed_interval = 5
        self.key_pressed_trigger = 10
        self.key_pressed_counter = 0

        self.clock = pygame.time.Clock()
        self.key = ""
        self.running = True

    def quit(self):
        self.s.close()
        self.work_thread.stop()
        self.running = False

    def process_key(self, event):
        self.key = self.keys[event.key][0]
        if event.mod & pygame.KMOD_CAPS:
            self.key = self.keys[event.key][1]
        elif event.mod & pygame.KMOD_SHIFT:
            self.key = self.keys[event.key][1]
        self.s.sendall(self.key.encode())
        self.input += self.key
        self.key_pressed = event.key
        self.key_pressed_counter = 0
        if len(self.input) >= self.input_max_length:
            self.input = self.input[-self.input_max_length:]
        print(self.key)

    def process_input(self):
        self.key_pressed_counter += 1
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
                break
            elif event.type == pygame.KEYDOWN:
                if event.key in self.keys:
                    # self.process_key(event)
                    self.key = self.keys[event.key][0]
                    if event.mod & pygame.KMOD_CAPS:
                        self.key = self.keys[event.key][1]
                    elif event.mod & pygame.KMOD_SHIFT:
                        self.key = self.keys[event.key][1]
                    elif event.mod & pygame.KMOD_CTRL:
                        if self.key == "s" or self.key == "S":
                            self.key = "SAVE"
                        elif "z" >= self.key >= "a" or "Z" >= self.key >= "A":
                            self.key = "Ctrl-" + self.key.upper()
                    self.s.sendall(self.key.encode())
                    self.input += self.key if self.key != "\b" else " "
                    if self.key in self.chars:
                        self.key_pressed = self.key
                        self.key_pressed_counter = 0
                    if len(self.input) >= self.input_max_length:
                        self.input = self.input[-self.input_max_length:]
                    print(self.key)
            elif event.type == pygame.KEYUP:
                if event.key in self.keys:
                    self.key = self.keys[event.key][0]
                    if event.mod & pygame.KMOD_CAPS:
                        self.key = self.keys[event.key][1]
                    elif event.mod & pygame.KMOD_SHIFT:
                        self.key = self.keys[event.key][1]
                    if self.key == self.key_pressed:
                        self.key_pressed = None
                        self.key_pressed_status = False
        if not self.key_pressed_status:
            if self.key_pressed_counter >= self.key_pressed_trigger:
                self.key_pressed_status = True
                self.key_pressed_counter = 0
                if self.key_pressed is not None:
                    self.s.sendall(self.key_pressed.encode())
                    self.input += self.key if self.key != "\b" else " "
                    if len(self.input) >= self.input_max_length:
                        self.input = self.input[-self.input_max_length:]
                    print(self.key_pressed)
        else:
            if self.key_pressed_counter >= self.key_pressed_interval:
                self.key_pressed_counter = 0
                if self.key_pressed is not None:
                    self.s.sendall(self.key_pressed.encode())
                    self.input += self.key if self.key != "\b" else " "
                    if len(self.input) >= self.input_max_length:
                        self.input = self.input[-self.input_max_length:]
                    print(self.key_pressed)

    def render(self):
        red = (180, 53, 53)
        yellow = (214, 199, 11)
        green = (81, 146, 3)
        offset_x = 0
        offset_y = 0
        self.window.fill((180, 180, 180))
        input_cache = self.font_command.render(self.input, True, (0, 0, 0))
        x = (512 - input_cache.get_width()) // 2
        self.window.blit(input_cache, (offset_x + x, offset_y + 20))
        pygame.display.update()

    def run(self):
        while self.running:
            self.process_input()
            self.render()
            self.clock.tick(30)

if __name__ == "__main__":
    logger.config_logging(file_name = "keyboard.log",
                          log_level = "INFO",
                          dir_name = "logs",
                          day_rotate = False,
                          when = "D",
                          interval = 1,
                          max_size = 20,
                          backup_count = 5,
                          console = True)
    LOG.info("start")
    host = "192.168.4.41"
    port = 8888
    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    worker = WorkThread(TaskQueue, ResultQueue)
    worker.start()
    UserInterface = UserInterface(host, port, worker, TaskQueue, ResultQueue)
    UserInterface.run()
    worker.join()
    pygame.quit()
    LOG.info("end")