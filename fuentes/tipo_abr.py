#!/usr/bin/env python3
from glob import glob
import os

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

for fl in sorted(glob("csv/t*.csv")):
    t = fl.split("/")[-1]
    t = t[1:-4]
    if not t.isdigit():
        continue
    with open(fl, "r") as f:
        rows = f.read()
        rows = rows.strip()
        rows = rows.split("\n")[2:]
        tipo = set(r.split(";")[2] for r in rows[2:])
        if len(tipo)==0:
            continue
        elif len(tipo)==1:
            tipo = tipo.pop()
        else:
            tipo = tuple(sorted(tipo))
        print('"%s": %s' % (t, tipo))
