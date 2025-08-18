import os
import time
import json
import urequests as requests


class Chat(object):
    def __init__(self, host, port, model, context_length = 10, timeout = 3600, stream = False):
        self.host = host
        self.port = port
        self.model = model
        self.timeout = timeout
        self.stream = stream
        self.context_length = context_length
        self.context = []
        self.headers = {"Content-Type": "application/json"}

    def chat(self, message):
        url = "http://%s:%s/api/chat" % (self.host, self.port)
        self.context.append({"role": "user", "content": message})
        if len(self.context) > self.context_length:
            self.context.pop(0)
        data = {"model": self.model, "messages": self.context, "stream": self.stream}
        r = requests.post(url, data = json.dumps(data), headers = self.headers, stream = self.stream, timeout = self.timeout)
        if r.status_code == 200:
            if self.stream:
                result = b""
                line = r.raw.readline()
                while line:
                    result += line
                    line = r.raw.readline()
                return True, result
            else:
                response = r.json()
                self.context.append({"role": response["message"]["role"], "content": response["message"]["content"]})
                if len(self.context) > self.context_length:
                    self.context.pop(0)
                return True, response["message"]["content"]
        else:
            return False, r.reason

    def clear(self):
        self.context.clear()
