import os
import json

from basictoken import BASICToken as Token


class DictFile(object):
    def __init__(self, path):
        self.path = path
        self.wf = open(self.path, "w")
        self.rf = None
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
        if key in self.index:
            pos = self.index[key]
            if self.rf is None:
                self.rf = open(self.path, "r")
            self.rf.seek(pos, 0)
            d = json.loads(self.rf.readline()[:-1])["d"]
            t = []
            if isinstance(d, list):
                for dd in d:
                    t.append(Token(dd[0], dd[1], dd[2]))
            else:
                t = Token(d[0], d[1], d[2])
            return t
        else:
            return None

    def __delitem__(self, key):
        del self.index[key]
    
    def get(self, key):
        return self.__getitem__(key)

    def __setitem__(self, key, value):
        pos, length = self.writejson(value)
        self.index[key] = pos
        if self.rf:
            self.rf.close()
        self.rf = None
        
    def clear(self):
        self.index.clear()
        self.wf.close()
        self.wf = open(self.path, "w")


class DictFileSlow(object):
    def __init__(self, path, max_line_num = 6000):
        self.max_line_num = max_line_num
        self.path = path
        self.index_path = self.path + ".idx"
        self.wf = open(self.path, "w")
        self.rf = None
        with open(self.index_path, "wb") as fp:
            for i in range(self.max_line_num / 40):
                fp.write(b'\xff\xff' * 40)
        self.rf_idx = open(self.index_path, "r+b")
        self.index = set()
        
    def writejson(self, d):
        line = json.dumps({"d": d}) + "\n"
        length = len(line)
        pos = self.wf.tell()
        self.wf.write(line)
        self.wf.flush()
        return pos, length

    def keys(self):
        return self.index

    def __contains__(self, key):
        return key in self.index

    def __len__(self):
        return len(self.index)

    def __getitem__(self, key):
        self.rf_idx.seek(int(key) * 2, 0)
        b = self.rf_idx.read(2)
        if b != b'\xff\xff':
            pos = int.from_bytes(b)
            if self.rf is None:
                self.rf = open(self.path, "r")
            self.rf.seek(pos, 0)
            d = json.loads(self.rf.readline()[:-1])["d"]
            t = []
            if isinstance(d, list):
                for dd in d:
                    t.append(Token(dd[0], dd[1], dd[2]))
            else:
                t = Token(d[0], d[1], d[2])
            return t
        else:
            return None

    def __delitem__(self, key):
        if key in self.index:
            self.index.remove(key)
    
    def get(self, key):
        return self.__getitem__(key)

    def __setitem__(self, key, value):
        if key not in self.index:
            self.index.add(key)
        pos, length = self.writejson(value)
        self.rf_idx.seek(int(key) * 2, 0)
        self.rf_idx.write(pos.to_bytes(2))
        if self.rf:
            self.rf.close()
        self.rf = None
        
    def clear(self):
        self.wf.close()
        self.wf = open(self.path, "w")
        with open(self.index_path, "wb") as fp:
            for i in range(self.max_line_num / 40):
                fp.write(b'\xff\xff' * 40)
        if self.rf:
            self.rf.close()
        self.rf = None
        self.rf_idx = open(self.index_path, "r+b")
        self.index = set()
