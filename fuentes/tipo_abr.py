#!/usr/bin/env python3
from glob import glob
import os
import re

re_br = re.compile(r"\s*\n\s*")
re_fl = re.compile(r"\s*;\s*")

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
        rows = re_br.split(rows)[2:]
        tipo = set(re_fl.split(r)[2] for r in rows)
        if len(tipo)==0:
            continue
        elif len(tipo)==1:
            tipo = tipo.pop()
        else:
            tipo = tuple(sorted(tipo))
        print('"%s": %s' % (t, tipo))
