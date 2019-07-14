import json
import os
import re
import subprocess
import sys
from urllib.parse import urljoin

import bs4
import requests
import yaml
from bunch import Bunch

from io import BytesIO
from zipfile import ZipFile
import urllib.request
from math import sin, cos, sqrt, atan2, radians



def get_pdf(url, to_file=None):
    ps = subprocess.Popen(("curl", "-s", url), stdout=subprocess.PIPE)
    output = subprocess.check_output(
        ('pdftotext', '-layout', '-nopgbrk', '-', '-'), stdin=ps.stdout)
    ps.wait()
    if to_file:
        with open(to_file, "wb") as f:
            f.write(output)
    txt = output.decode(sys.stdout.encoding)
    return txt


def request_soup(url, data=None):
    print(url, data)
    if data:
        r = requests.post(url, data=data)
    else:
        r = requests.get(url)
    soup = bs4.BeautifulSoup(r.content, "html.parser")
    for n in soup.findAll(["a", "form", "iframe", "img", "link", "script", "frame"]):
        if n.name in ("a", "link"):
            att = "href"
        elif n.name in ("frame", "iframe", "img", "script"):
            att = "src"
        elif n.name in ("form", ):
            att = "action"
        href = n.attrs.get(att)
        if href and not href.startswith("#") and not href.startswith("javascript:"):
            n.attrs[att] = urljoin(url, href)
    return soup


def get_soup(url, data=None, select=None, attr=None, to_file=None):
    isFile = to_file and os.path.isfile(to_file)
    if isFile:
        with open(to_file) as f:
            soup = bs4.BeautifulSoup(f.read(), "html.parser")
    else:
        soup = request_soup(url, data=data)
        if to_file:
            with open(to_file, "w") as f:
                f.write(str(soup))
    if select:
        select = soup.select(select)
        if len(select) == 0:
            return None
        if attr:
            return select[0].attrs.get(attr)
        if len(select) == 1:
            return select[0]
        return select
    return soup


def mkBunchParse(obj):
    if isinstance(obj, list):
        for i, v in enumerate(obj):
            obj[i] = mkBunchParse(v)
        return obj
    if isinstance(obj, dict):
        data = []
        # Si la clave es un año lo pasamos a entero
        flag = True
        for k in obj.keys():
            if not isinstance(k, str):
                return {k: mkBunchParse(v) for k, v in obj.items()}
            if not(k.isdigit() and len(k) == 4 and int(k[0]) in (1, 2)):
                flag = False
        if flag:
            return {int(k): mkBunchParse(v) for k, v in obj.items()}
        obj = Bunch(**{k: mkBunchParse(v) for k, v in obj.items()})
        return obj
    return obj


def read_yml(file):
    if not os.path.isfile(file):
        return None
    with open(file, "r") as f:
        data = list(yaml.load_all(f, Loader=yaml.FullLoader))
        if len(data) == 1:
            data = data[0]
        return data


def mkBunch(file):
    if not os.path.isfile(file):
        return None
    ext = file.rsplit(".", 1)[-1]
    if ext == "yml":
        data = read_yml(file)
    if ext == "json":
        data = read_js(file)
    data = mkBunchParse(data)
    return data


def read_js(file, to_bunch=False):
    if file and os.path.isfile(file):
        with open(file, 'r') as f:
            js = json.load(f)
            if to_bunch:
                js = mkBunchParse(js)
            return js
    return None


re_json1 = re.compile(r"^\[\s*{")
re_json2 = re.compile(r" *}\s*\]$")
re_json3 = re.compile(r"}\s*,\s*{")
re_json4 = re.compile(r"^  ", re.MULTILINE)


def obj_to_js(data):
    txt = json.dumps(data, indent=2)
    txt = re_json1.sub("[{", txt)
    txt = re_json2.sub("}]", txt)
    txt = re_json3.sub("},{", txt)
    txt = re_json4.sub("", txt)
    return txt


def save_js(file, data):
    txt = obj_to_js(data)
    with open(file, "w") as f:
        f.write(txt)


def read_csv(file, start=0, where=None, null=None):
    head = None
    with open(file, "r") as f:
        for i, l in enumerate(f.readlines()):
            l = l.rstrip()
            l = l.rstrip(";")
            if l:
                campos = []
                for c in l.split(";"):
                    c = c.strip()
                    if c == "":
                        c = None
                    elif c.isdigit():
                        c = int(c)
                    campos.append(c)
                if i == start:
                    head = campos
                elif head:
                    o = {h: c for h, c in zip(head, campos)}
                    ok = True
                    if where is not None:
                        for k, v in where.items():
                            ok = ok and o.get(k) == v
                    if ok:
                        if null:
                            for k, v in list(o.items()):
                                if v in null:
                                    o[k] = None
                        yield o

def create_script(file, **kargv):
    with open(file, "w") as f:
        for k, v in kargv.items():
            f.write("var "+k+" = ")
            json.dump(v, f, indent=2)
            f.write(";\n")



def read_zip(url, file, start=0):
    url = urllib.request.urlopen(url)
    with ZipFile(BytesIO(url.read())) as my_zip_file:
        for i, line in enumerate(my_zip_file.open(file).readlines()):
            line = line.decode()
            line = line.strip()
            if line and i>=start:
                yield line

def get_km(lat1, lon1, lat2, lon2):
    R = 6373.0

    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c

    return distance
