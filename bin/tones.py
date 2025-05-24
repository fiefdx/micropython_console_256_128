import sys

from scheduler import Condition, Message
from common import exists, path_join

coroutine = True

def parse(path):
    result = []
    with open(path, "r") as fp:
        content = fp.read()
        parts = content.split("|")
        for part in parts:
            notes = part.split(",")
            for note in notes:
                note = note.strip()
                result.append(note)
    return result


def main(*args, **kwargs):
    result = "invalid parameters"
    args = kwargs["args"]
    shell_id = kwargs["shell_id"]
    shell = kwargs["shell"]
    
    notes = {
        "S": 0,
        "C2": 65, "C#2": 69, "D2": 73, "D#2": 78, "E2": 82, "F2": 87, "F#2": 92, "G2": 98, "G#2": 104, "A2": 110, "A#2": 117, "B2": 123,
        "C3": 131, "C#3": 139, "D3": 147, "D#3": 156, "E3": 165, "F3": 175, "F#3": 185, "G3": 196, "G#3": 208, "A3": 220, "A#3": 233, "B3": 247,
        "C4": 262, "C#4": 277, "D4": 294, "D#4": 311, "E4": 330, "F4": 349, "F#4": 370, "G4": 392, "G#4": 415, "A4": 440, "A#4": 466, "B4": 494,
        "C5": 523, "C#5": 554, "D5": 587, "D#5": 622, "E5": 659, "F5": 698, "F#5": 740, "G5": 784, "G#5": 831, "A5": 880, "A#5": 932, "B5": 988,
        "C6": 1047, "C#6": 1109, "D6": 1175, "D#6": 1245, "E6": 1319, "F6": 1397, "F#6": 1480, "G6": 1568, "G#6": 1661, "A6": 1760, "A#6": 1865, "B6": 1976,
    }
    
    times = {"1": 1000, "1.": 1500, "2": 500, "2.": 750, "4": 250, "4.": 375, "8": 125, "8.": 188, "16": 63, "16.": 95, "32": 32, "32.": 48}
    
    try:
        if len(args) >= 2:
            volume = int(args[0])
            common_time = args[1]
            bpm = int(args[2])
            path = None
            if len(args) >= 4:
                path = args[3]
            data = ["C4-4", "C#4-4", "D4-4", "D#4-4", "E4-4", "F4-4", "F#4-4", "G4-4", "G#4-4", "A4-4", "A#4-4", "B4-4"]
            if path and exists(path):
                data = parse(path)
            one_beat_note = common_time.split("/")[-1].strip()
            one_beat_time = int(60 * 1000 / bpm)
            for k in times:
                if "." in k:
                    times[k] = int((int(one_beat_note) / int(k[:-1])) * one_beat_time * 1.5)
                else:
                    times[k] = int((int(one_beat_note) / int(k)) * one_beat_time)
            for note in data:
                notation = note.split("-")
                note = notation[0]
                length = times[notation[1]]
                freq = notes[note]
                yield Condition.get().load(sleep = length + 20, send_msgs = [
                    Message.get().load({"freq": freq, "volume": volume, "length": length}, receiver = shell.scheduler.sound_id)
                ])
            yield Condition.get().load(sleep = 0, send_msgs = [
                Message.get().load({"output": ""}, receiver = shell_id)
            ])
        else:
            yield Condition.get().load(sleep = 0, send_msgs = [
                Message.get().load({"output": result}, receiver = shell_id)
            ])
    except Exception as e:
        yield Condition.get().load(sleep = 0, send_msgs = [
            Message.get().load({"output": str(sys.print_exception(e))}, receiver = shell_id)
        ])
