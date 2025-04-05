import gc
import sys

def reload(mod):
    mod_name = mod.__name__
    del sys.modules[mod_name]
    gc.collect()
    return __import__(mod_name)

