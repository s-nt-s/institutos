import functools
import os
from .common import *

class Cache:
    def __init__(self, file):
        self.file = file
        self.data = {}
        self.func = None

    def read(self):
        pass

    def save(self):
        pass

    def callCache(self, slf, *args, **kargs):
        if not self.isReload(slf):
            data = self.read(*args, **kargs)
            if data:
                return data
        data = self.func(slf, *args, **kargs)
        self.save(data, *args, **kargs)
        return data

    def isReload(self, slf):
        reload = getattr(slf, "reload", None)
        if reload is None or reload == True:
            return True
        if (isinstance(reload, list) or isinstance(reload, tuple)) and self.file in reload:
            return True
        return False

    def __call__(self, func):
        functools.update_wrapper(self, func)
        self.func = func
        return lambda *args, **kargs: self.callCache(*args, **kargs)


class TxtCache(Cache):
    def __init__(self, *args, **kargv):
        Cache.__init__(self, *args, **kargv)

    def read(self, *args, **kargs):
        if os.path.isfile(self.file):
            with open(self.file, "r") as f:
                return f.read()

    def save(self, data, *args, **kargs):
        with open(self.file, "w") as f:
            return f.write(data)


class JsonCache(Cache):
    def __init__(self, *args, **kargv):
        Cache.__init__(self, *args, **kargv)

    def read(self, *args, **kargs):
        return read_js(self.file)

    def save(self, data, *args, **kargs):
        save_js(self.file, data)
