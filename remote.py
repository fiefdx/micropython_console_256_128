import socket

from pynput import keyboard
import pygetwindow as gw # Or a similar library for your OS

TARGET_TERMINAL_TITLE = "Windows PowerShell" # Replace with the actual title or a substring
ctrl_pressed = False
all_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ`1234567890-=[]\\;',./~!@#$%^&*()_+{}|:\"<>? "
S = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
S.connect(("192.168.4.28", 8888))


def on_press(key):
    global ctrl_pressed
    if is_terminal_focused(TARGET_TERMINAL_TITLE):
        try:
            if hasattr(key, "char") and key.char == '\x11':
                S.close()
                return False
            elif hasattr(key, "char") and key.char == "q" and ctrl_pressed:
                return False
            elif key == keyboard.Key.ctrl_l:
                ctrl_pressed = True

            c = ""
            if hasattr(key, "char"):
                c = key.char
            if key == keyboard.Key.esc:
                c = "ES"
                S.sendall(c.encode())
            elif key == keyboard.Key.enter:
                c = "\n"
                S.sendall(c.encode())
            elif key == keyboard.Key.space:
                c = " "
                S.sendall(c.encode())
            elif key == keyboard.Key.backspace:
                c = "\b"
                S.sendall(c.encode())
            elif key == keyboard.Key.up:
                c = "UP"
                S.sendall(c.encode())
            elif key == keyboard.Key.down:
                c = "DN"
                S.sendall(c.encode())
            elif key == keyboard.Key.left:
                c = "LT"
                S.sendall(c.encode())
            elif key == keyboard.Key.right:
                c = "RT"
                S.sendall(c.encode())
            elif key == keyboard.Key.page_up:
                c = "BX"
                S.sendall(c.encode())
            elif key == keyboard.Key.page_down:
                c = "BB"
                S.sendall(c.encode())
            elif key == keyboard.Key.home:
                c = "BY"
                S.sendall(c.encode())
            elif key == keyboard.Key.end:
                c = "BA"
                S.sendall(c.encode())
            elif key == keyboard.Key.left and ctrl_pressed:
                c = "BY"
                S.sendall(c.encode())
            elif key == keyboard.Key.right and ctrl_pressed:
                c = "BA"
                S.sendall(c.encode())
            elif len(c) == 1 and c in all_chars:
                S.sendall(c.encode())
            print(f'alphanumeric key {key.char if hasattr(key, "char") else key} pressed in terminal')
        except Exception as e:
            print(e)
        except AttributeError:
            print(f'special key {key} pressed in terminal')

def on_release(key):
    global ctrl_pressed
    if is_terminal_focused(TARGET_TERMINAL_TITLE):
        # print(f'{key} released in terminal')
        if key == keyboard.Key.ctrl_l:
            ctrl_pressed = False

def is_terminal_focused(terminal_title_substring):
    active_window = gw.getActiveWindow() # For Windows
    # print(active_window.title)
    if active_window and terminal_title_substring in active_window.title:
        return True
    return False

listener = keyboard.Listener(
    on_press = on_press,
    on_release = on_release,
    suppress = True)
listener.start()
listener.join() # Keep the main thread alive while the listener runs