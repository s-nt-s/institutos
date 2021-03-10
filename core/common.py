import json
import os
import re
import subprocess
import sys
import zipfile as zipfilelib
from io import BytesIO
from math import atan2, cos, radians, sin, sqrt
from urllib.parse import urljoin
import time
from .web import Web, FF, get_session

import bs4
import requests
import yaml
from bunch import Bunch

w = Web()#get_session("https://www.madrid.org/wpad_pub/run/j/BusquedaAvanzada.icm")

def unzip(target, *urls):
    if os.path.isdir(target):
        return
    os.makedirs(target, exist_ok=True)
    for url in urls:
        print(url, "-->", target)
        response = requests.get(url, verify=False)
        filehandle = BytesIO(response.content)
        with zipfilelib.ZipFile(filehandle, 'r') as zip:
            zip.extractall(target)


def get_pdf(url, to_file=None):
    print("get_pdf:", url)
    ps = subprocess.Popen(("curl", "-s", url), stdout=subprocess.PIPE)
    output = subprocess.check_output(
        ('pdftotext', '-layout', '-nopgbrk', '-', '-'), stdin=ps.stdout)
    ps.wait()
    if to_file:
        outdir = os.path.dirname(to_file)
        os.makedirs(outdir, exist_ok=True)
        with open(to_file, "wb") as f:
            f.write(output)
    txt = output.decode(sys.stdout.encoding)
    return txt

def get_local_soup(file, maxOld=1):
    if file is None or not os.path.isfile(file):
        return None
    maxOld = time.time() - (maxOld * 86400)
    if os.stat(file).st_mtime < maxOld:
        return None
    with open(file) as f:
        #print("get_local_soup:", file)
        return bs4.BeautifulSoup(f.read(), "html.parser")

def get_soup(url, data=None, select=None, attr=None, to_file=None):
    if to_file is None and data is None and url.endswith("/wpad_pub/run/j/BusquedaAvanzada.icm"):
        to_file = "fuentes/madrid.org/buscador.html"
    soup = get_local_soup(to_file)
    if soup is None:
        print("request_soup:", url, data)
        soup = w.get(url, **(data or {}))
        if to_file:
            outdir = os.path.dirname(to_file)
            os.makedirs(outdir, exist_ok=True)
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
re_json4 = re.compile(r"\[\s*([^,\s]+)\s*,\s*([^,\s]+)\s*\]")
re_json5 = re.compile(r"\[\s*([^,\s]+)\s*\]")
re_json6 = re.compile(r"^  ", re.MULTILINE)


def obj_to_js(data):
    txt = json.dumps(data, indent=2)
    txt = re_json1.sub("[{", txt)
    txt = re_json2.sub("}]", txt)
    txt = re_json3.sub("},{", txt)
    txt = re_json4.sub(r"[\1, \2]", txt)
    txt = re_json5.sub(r"[\1]", txt)
    txt = re_json6.sub("", txt)
    return txt


def save_js(file, data):
    txt = obj_to_js(data)
    outdir = os.path.dirname(file)
    os.makedirs(outdir, exist_ok=True)
    with open(file, "w") as f:
        f.write(txt)


def to_num(st, coma=False):
    s = st.strip() if st else None
    if s is None:
        return None
    try:
        if coma:
            s = s.replace(".", "")
            s = s.replace(",", ".")
        s = float(s)
        if int(s) == s:
            s = int(s)
        return s
    except:
        pass
    return st


def read_csv(file, start=0, where=None, null=None, separator=";", parse=None, encoding=None):
    if parse is None:
        def parse(x): return x
    head = None
    with open(file, "r", encoding=encoding) as f:
        for i, l in enumerate(f.readlines()):
            l = l.rstrip()
            l = l.rstrip(separator)
            if l:
                campos = []
                for c in l.split(separator):
                    c = c.strip()
                    if c == "":
                        c = None
                    c = parse(c)
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


def create_script(file, indent=2, **kargv):
    separators=(',', ':') if indent is None else None
    outdir = os.path.dirname(file)
    os.makedirs(outdir, exist_ok=True)
    with open(file, "w") as f:
        for i, (k, v) in enumerate(kargv.items()):
            if i>0:
                f.write(";\n")
            f.write("var "+k+" = ")
            json.dump(v, f, indent=indent, separators=separators)
            f.write(";")


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
