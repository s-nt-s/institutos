import functools
import os

from .common import *


class Cache:
    def __init__(self, file, *args, reload=False, **kargs):
        self.file = file
        self.data = {}
        self.func = None
        self.reload = reload

    def read(self):
        pass

    def save(self):
        pass

    def callCache(self, slf, *args, **kargs):
        if not self.reload and not self.isReload(slf):
            data = self.read(*args, **kargs)
            if data:
                return data
        data = self.func(slf, *args, **kargs)
        self.save(data, *args, **kargs)
        return data

    def isReload(self, slf):
        reload = getattr(slf, "reload", False)
        if reload == True:
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
    def __init__(self, *args, to_bunch=False, **kargv):
        Cache.__init__(self, *args, **kargv)
        self.to_bunch = to_bunch

    def read(self, *args, **kargs):
        return read_js(self.file, to_bunch=self.to_bunch)

    def save(self, data, *args, **kargs):
        if isinstance(data, set):
            data=list(sorted(data))
        save_js(self.file, data)


class ListCache(Cache):
    def __init__(self, *args, cast=lambda x: x, **kargv):
        Cache.__init__(self, *args, **kargv)
        self.cast = cast

    def read(self, *args, **kargs):
        if not os.path.isfile(self.file):
            return None
        lst = []
        with open(self.file, "r") as f:
            for l in f.readlines():
                l = l.strip()
                l = self.cast(l)
                if l:
                    lst.append(l)
        return lst

    def save(self, data, *args, **kargs):
        if isinstance(data, set):
            data = sorted(data)
        with open(self.file, "w") as f:
            for i, l in enumerate(data):
                if i > 0:
                    f.write("\n")
                f.write(str(l))

class ParamJsonCache(JsonCache):
    def __init__(self, *args, **kargv):
        JsonCache.__init__(self, *args, **kargv)

    def read(self, *args, **kargs):
        f = self.file.format(*args, **kargs)
        return read_js(f)

    def save(self, data, *args, **kargs):
        f = self.file.format(*args, *kargs)
        save_js(f, data)
