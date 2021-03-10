import functools
import os
import time

from .common import *


class Cache:
    def __init__(self, file, *args, reload=False, maxOld=1, **kargs):
        self.file = file
        self.data = {}
        self.func = None
        self.reload = reload
        self.maxOld = maxOld
        if maxOld is not None:
            self.maxOld = time.time() - (maxOld * 86400)


    def get_file_name(self, *args, **kargs):
        return self.file

    def read(self):
        pass

    def save(self):
        pass

    def tooOld(self, fl):
        if self.maxOld is None or not os.path.isfile(fl):
            return False
        if os.stat(fl).st_mtime < self.maxOld:
            return True
        return False

    def callCache(self, slf, *args, **kargs):
        if not self.reload and not self.isReload(slf, *args, **kargs):
            data = self.read(*args, **kargs)
            if data:
                return data
        data = self.func(slf, *args, **kargs)
        self.save(data, *args, **kargs)
        return data

    def isReload(self, slf, *args, **kargs):
        reload = getattr(slf, "reload", False)
        if reload == True:
            return True
        if isinstance(reload, (list, tuple)) and self.file in reload:
            return True
        fl = self.get_file_name(*args, **kargs)
        if isinstance(reload, (list, tuple)) and fl in reload:
            return True
        if self.tooOld(fl):
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
        outdir = os.path.dirname(self.file)
        os.makedirs(outdir, exist_ok=True)
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
            data = list(sorted(data))
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
        outdir = os.path.dirname(self.file)
        os.makedirs(outdir, exist_ok=True)
        with open(self.file, "w") as f:
            for i, l in enumerate(data):
                if i > 0:
                    f.write("\n")
                f.write(str(l))


class ParamJsonCache(JsonCache):
    def __init__(self, *args, **kargv):
        JsonCache.__init__(self, *args, **kargv)

    def get_file_name(self, *args, **kargs):
        return self.file.format(*args, **kargs)

    def read(self, *args, **kargs):
        f = self.get_file_name(*args, **kargs)
        return read_js(f)

    def save(self, data, *args, **kargs):
        f = self.get_file_name(*args, *kargs)
        save_js(f, data)
