import os
import sys
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
    def __init__(self, work_thread, task_queue, result_queue):
        pygame.init()
        pygame.mixer.init()
        self.window = pygame.display.set_mode((512, 512)) # pygame.FULLSCREEN | pygame.SCALED) # , pygame.RESIZABLE)
        pygame.display.set_caption("RemoteKeyboard - v%s" % __version__)
        # pygame.display.set_icon(pygame.image.load("assets/icon.png"))

        self.work_thread = work_thread
        self.font_command = pygame.font.SysFont('Arial', 80)
        self.font = pygame.font.SysFont('Arial', 20)

        self.clock = pygame.time.Clock()
        self.key = ""
        self.running = True

    def quit(self):
        self.work_thread.stop()
        self.running = False

    def process_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
                break
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.quit()
                elif event.key == pygame.K_RETURN:
                    self.key = "\n"
                    print("enter")
                elif event.key == pygame.K_LEFT:
                    pass
                elif event.key == pygame.K_RIGHT:
                    pass
                elif event.key == pygame.K_UP:
                    pass
                elif event.key == pygame.K_DOWN:
                    pass
                elif event.key == pygame.K_f:
                    self.key = "f"
                    pass

    def render(self):
        red = (180, 53, 53)
        yellow = (214, 199, 11)
        green = (81, 146, 3)
        offset_x = 0
        offset_y = 0
        self.window.fill((180, 180, 180))
        key = self.font_command.render(self.key, True, (0, 0, 0))
        x = (512 - key.get_width()) // 2
        self.window.blit(key, (offset_x + x, offset_y + 20))
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
    host = "192.164.4.28"
    port = 8888
    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        port = host = sys.argv[2]
    worker = WorkThread(TaskQueue, ResultQueue)
    worker.start()
    UserInterface = UserInterface(worker, TaskQueue, ResultQueue)
    UserInterface.run()
    worker.join()
    pygame.quit()
    LOG.info("end")