import os
import json

from basictoken import BASICToken as Token


class DictFile(object):
    def __init__(self, path):
        self.path = path
        self.wf = open(self.path, "w")
        self.index = {}

    def writejson(self, d):
        line = json.dumps({"d": d}) + "\n"
        length = len(line)
        pos = self.wf.tell()
        self.wf.write(line)
        self.wf.flush()
        return pos, length

    def keys(self):
        return self.index.keys()

    def __contains__(self, key):
        return key in self.index

    def __len__(self):
        return len(self.index)

    def __getitem__(self, key):
        pos, length = self.index[key]
        self.rf = open(self.path, "r")
        self.rf.seek(pos, 0)
        d = json.loads(self.rf.read(length - 1))["d"]
        t = []
        if isinstance(d, list):
            for dd in d:
                t.append(Token(dd["c"], dd["C"], dd["l"]))
        else:
            t = Token(d["c"], d["C"], d["l"])
        self.rf.close()
        return t
    
    def get(self, key):
        return self.__getitem__(key)

    def __setitem__(self, key, value):
        pos, length = self.writejson(value)
        self.index[key] = [pos, length]

    def clear(self):
        self.index.clear()
        self.wf.close()
        self.wf = open(self.path, "w")


class DictFileSlow(object):
    def __init__(self, path):
        self.path = path
        self.wf = open(self.path, "w")
        self.index = {}
        
    def writejson(self, d):
        line = json.dumps({"d": d}) + "\n"
        length = len(line)
        pos = self.wf.tell()
        self.wf.write(line)
        self.wf.flush()
        return pos, length

    def keys(self):
        return self.index.keys()

    def __contains__(self, key):
        return key in self.index

    def __len__(self):
        return len(self.index)

    def __getitem__(self, key):
        pos = self.index[key]
        self.rf = open(self.path, "r")
        self.rf.seek(pos, 0)
        d = json.loads(self.rf.readline()[:-1])["d"]
        t = []
        if isinstance(d, list):
            for dd in d:
                t.append(Token(dd["c"], dd["C"], dd["l"]))
        else:
            t = Token(d["c"], d["C"], d["l"])
        self.rf.close()
        return t
    
    def get(self, key):
        return self.__getitem__(key)

    def __setitem__(self, key, value):
        pos, length = self.writejson(value)
        self.index[key] = pos
        
    def clear(self):
        self.index.clear()
        self.wf.close()
        self.wf = open(self.path, "w")
