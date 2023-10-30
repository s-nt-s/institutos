import re
from contextlib import closing
from html.parser import HTMLParser

import requests
import urllib3
import time
from random import randint
import json
import bs4

from .common import get_soup, fix_text
from .utm_to_geo import utm_to_geo

urllib3.disable_warnings()

re_sp = re.compile(r"\s+", re.MULTILINE | re.UNICODE)
re_dire = re.compile(r"^\s*Dirección:", re.MULTILINE | re.UNICODE | re.DOTALL)
re_coord = re.compile(r"&xIni=([\d\.]+)&yIni=([\d\.]+)")
re_minusculas = re.compile(r"[a-z]")
re_nocturno = re.compile(r".*\bnocturno\b.*")
re_title = re.compile("<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
htmlp = HTMLParser()


def get_abr(t):
    if t in ("016", "017"):
        return "CI"
    if t == "068":
        return "CIFP"
    if t == "031":
        return "CEPA"
    if t == "035":
        return "CARCEL"
    if t == "036":
        return "AH"
    if t == "042":
        return "IES"
    if t == "047":
        return "SIES"
    if t == "070":
        return "CEIPS"
    if t == "039":
        return "CREI"
    if t == "020":
        return "CEE"
    if t == "204":
        return "EOEP-ES"
    if t == "205":
        return "EOEP-AT"
    if t == "206":
        return "EOEP-GE"
    return None


def status_web(url, stweb, intentos=1):
    if url.endswith("/"):
        url=url[:-1]
    if stweb and url in stweb:
        return stweb[url]
    buffer = ""
    try:
        with closing(requests.get(url, stream=True, verify=False, timeout=5)) as res:
            status = res.status_code
            if status != 200:
                return status
            for chunk in res.iter_content(chunk_size=1024, decode_unicode=True):
                buffer = buffer+chunk
                match = re_title.search(buffer)
                if match:
                    title = htmlp.unescape(match.group(1))
                    title = re_sp.sub(" ", title).strip()
                    if title == "Web de centro deshabilitada | EducaMadrid":
                        return 999
    except Exception as e:
        if intentos > 0:
            time.sleep(10)
            return status_web(url, stweb, intentos=intentos-1)
        return 991
    return 200


def get_grafica(ct, **kargv):
    data={
        "callCount":1,
        "c0-scriptName":"GraficasDWRAccion",
        "c0-methodName":"obtenerGrafica",
        "c0-id": ("%s_%s" % (randint(1000, 9999), int(time.time()*1000))),
        "c0-e1": "string:"+ct,
        "c0-e2":"string:TODO",
        "c0-e3":"string:1",
        "c0-e4":"string:1",
        "c0-param0":"Object:{cdCentro:reference:c0-e1, cdnivelEducativo:reference:c0-e2, cdGrafica:reference:c0-e3, tipoGrafica:reference:c0-e4}",
        "xml":True
    }
    if kargv:
        data.update(kargv)
    r = requests.post("http://gestiona.madrid.org/wpad_pub/dwr/exec/GraficasDWRAccion.obtenerGrafica.dwr", data=data)
    return r.text.replace(";", ";\n")


def get_estadistica(ct):
    estadistica={}
    grafica = get_grafica(ct)

    y,v,c = (None,)*3
    for l in grafica.split("\n"):
        l = l.strip()
        if len(l)==0:
            if y and v and c:
                obj = estadistica.get(y, {})
                obj[c]=v
                estadistica[y]=obj
            y,v,c = (None,)*3
            continue
        m = re.match(r'^var s\d+="(20\d+)-20\d+";$', l)
        if m:
            y=int(m.group(1))
            continue
        m = re.match(r'^var s\d+="\s*(.+?)\s*";', l)
        if m:
            c=m.group(1)
            continue
        m = re.match(r'^var s\d+=(\d+);$', l);
        if m:
            v = int(m.group(1))
            continue
    print(json.dumps(estadistica, indent=4))


def get_text(n, index=0):
    if isinstance(n, bs4.element.ResultSet) or type(n) is list:
        n = n[index]
    txt = re_sp.sub(" ", n.get_text()).strip()
    return txt


def get_abr_dir(w1):
    w1 = w1.lower()
    if w1 == "avenida":
        return "Av."
    if w1 == "bulevar":
        return "Blvr."
    if w1 == "calle":
        return "C/"
    if w1 == "callejon":
        return None
    if w1 == "camino":
        return None
    if w1 == "carrera":
        return None
    if w1 == "carretera":
        return "Ctra."
    if w1 == "paraje":
        return None
    if w1 == "parcela":
        return None
    if w1 == "pasaje":
        return None
    if w1 == "paseo":
        return None
    if w1 == "plaza":
        return "Pl."
    if w1 == "ronda":
        return "Rda."
    if w1 == "senda":
        return None
    if w1 == "urbanizacion":
        return "Urb."
    return None


def parse_dir(dir):
    if not dir:
        return dir
    rst = dir.split()
    for i, w in enumerate(rst):
        w=w.lower()
        if w in ("de", "del", "la", "el", "lo", "los"):
            rst[i]=w
    rst[0] = get_abr_dir(rst[0]) or rst[0]
    dir = " ".join(rst)
    dir = re.sub(r"\b(s/n|c/v)\b",  lambda x: x.group().upper(), dir, flags=re.IGNORECASE)
    return dir


def parse_etapa(txt: str):
    spl = txt.split("\n")
    if len(spl) == 1:
        return txt
    if spl[0] == "Educación Especial (Adaptac.LOE)":
        aux = spl[-1].split("-", 1)
        if aux[0] == "Ed. Básica Obligatoria":
            return f"Educación Especial {aux[1].strip()} (Adaptac. LOE)"
        if spl[-1] == "Educación Básica Obligatoria (Adaptac. LOE)":
            return "Educación Básica Obligatoria (Adaptac. LOE)"
        if spl[-1] == "Educación Infantil (Adaptac. LOE)":
            return "Educación Especial Infantil (Adaptac. LOE)"
        if spl[-1] == "Programas de Transición a la Vida Adulta (Adaptac. LOE)":
            return spl[-1]
    if spl[0] == "Educación Especial (LOMLOE)":
        if spl[-1] == "Edcuación Básica Oblicatoria (EBO)":
            return "Edcuación Básica Oblicatoria (LOMLOE)"
        if spl[-1] == "Educación Infantil Especial (EIE)":
            return spl[-1]
        if spl[-1] == "Talleres Formativos (TF)":
            return spl[-1]
    return txt.replace("\n", " -> ")


def get_data(ctr, stweb):
    ctr = str(ctr)
    d1 = get_data1(ctr)
    d2 = None
    if d1 not in (None, False):
        for k in ("latlon", "direccion", "mail", "url"):
            if not d1.get(k):
                if d2 is None:
                    print("  buscar %s en segunda opción" % k)
                    d2 = get_data2(ctr)
                d1[k] = d2.get(k)
    else:
        print("  buscar %s en segunda opción" % ctr)
        d1 = get_data2(ctr)
        d2 = False
    url = d1.get("url")
    if url:
        d1["status_web"] = status_web(url, stweb)
        if d1["status_web"] != 200 and d2 is not False:
            if d2 is None:
                print("  buscar url en segunda opción tras obtener status_web=" +str(d1["status_web"]))
                d2 = get_data2(ctr)
            _url = d2.get("url")
            if _url and _url != url:
                if status_web(_url, stweb) == 200:
                    d1["url"]=_url
                    d1["status_web"] = 200
    if d1.get("url") and d1["url"].endswith("/"):
        d1["url"]=d1["url"][:-1]
    return d1


def lst_remove(arr1: list, arr2: list):
    for i in arr2:
        if i in arr1:
            arr1.remove(i)


def get_data1(ctr):
    url = "https://gestiona.comunidad.madrid/wpad_pub/run/j/MostrarFichaCentro.icm?cdCentro=" + ctr
    soup = get_soup(url, to_file="fuentes/madrid.org/"+ctr+".html")
    items = soup.select("div.formularioconTit input")
    if len(items) == 0:
        return False
    data = {}
    for i in items:
        n = i.attrs.get("name", "").strip()
        v = i.attrs.get("value", "").strip()
        if v == "null":
            continue
        if len(n) > 0 and len(v) > 0 and n not in ("filtroConsultaSer", "salidaCompSerializada", "formularioConsulta"):
            data[n] = v
    d = re_sp.sub(" ", soup.find(text=re_dire).findParent(
        "td").get_text()).strip()[11:-1].title()
    data["direccion"] = d
    href = soup.find("div", attrs={"id": "Mapa"}).find("a").attrs["onclick"]
    m = re_coord.search(href)
    data["UTM_ED50-HUSO_30"] = m.group(1) + "," + m.group(2)
    if data["UTM_ED50-HUSO_30"] != "0.0,0.0":
        utm_split = data["UTM_ED50-HUSO_30"].split(",")
        x, y = tuple(map(float, data["UTM_ED50-HUSO_30"].split(",")))
        lat, lon = utm_to_geo(30, x, y, "ED50")
        data["latlon"] = str(lat) + "," + str(lon)
    data["tipo"] = data["tlGenericoCentro"]
    data["nombre"] = data["tlNombreCentro"].title()
    data["url"] = data.get("tlWeb")
    data["mail"] = data.get("tlMail")
    data["dat"] = data.get("tlAreaTerritorial")
    data["info"] = url
    # tipos_des[data["TIPO"]]=data["tlGenericoExt"].capitalize()
    data["nocturno"] = [get_text(n.findParent("tr").find("td"))
                        for n in soup.findAll(text=re_nocturno)]
    if len(data["nocturno"]) == 0:
        data["nocturno"] = None
    etapas = []
    txt_especial = ("Educación Especial (Adaptac.LOE)", "Educación Especial (LOMLOE)")
    for tr in soup.select("#capaEtapasContent tr"):
        td = tr.find("td")
        txt = get_text(td)
        if txt and txt != "Etapa":
            txt = fix_text(txt)
            txt = txt.replace("Educación Secundaria Obligatoria", "ESO")
            if txt in ('"Bachibac" Programa doble titulación Bachiller-Baccalaureat', '"Bachibac" Programa doble titulación Bachillerato'):
                txt = "Bachibac"
            lv = 0
            cls = td.attrs["class"]
            if isinstance(cls, str):
                cls = cls.split()
            for cl in cls:
                if cl.startswith("p"):
                    cl = cl[1:]
                    if cl.isdigit():
                        lv = int(cl)
            if lv == 0:
                etapas.append(txt)
                continue
            if len(etapas) == 0:
                continue
            lst_etapa = etapas[-1].split("\n")
            if lst_etapa[0] not in txt_especial:
                continue
            if lv == 40:
                etapas.append(lst_etapa[0]+'\n'+txt)
            elif lv == 60:
                etapas.append("\n".join(lst_etapa[0:2])+'\n'+txt)
    for etapa in list(etapas):
        spl = etapa.split("\n")
        if len(spl) < 2:
            continue
        txt = "\n".join(spl[:-1])
        if txt in etapas:
            etapas.remove(txt)
    etapas = list(map(parse_etapa, etapas))
    data["etapas"] = etapas if len(etapas) else None
    return data


def get_data2(ctr):
    data = {}
    url = "http://www.buscocolegio.com/Colegio/detalles-colegio.action?id=" + ctr
    soup = get_soup(url, to_file="fuentes/buscocolegio.com/"+ctr+".html")
    h3 = soup.find("h3", text="Código")
    if h3 is None:
        print("NO h3[text()='Código']")
        return data
    cod = h3.parent.find("strong").string
    if ctr != cod:
        return data
    data["nombre"] = get_text(soup.select("li > span[itemprop='name']"))
    if data["nombre"].startswith("IES "):
        data["nombre"] = data["nombre"][4:]
    if not re_minusculas.search(data["nombre"]):
        data["nombre"] = data["nombre"].title()
    data["direccion"] = get_text(soup.select("i.icon-location-pin + span"))
    data["direccion"] = data["direccion"].replace("(Madrid)", "Madrid")
    latitude = soup.find("meta", attrs={"itemprop": "latitude"})
    if latitude:
        latitude = latitude.attrs["content"]
    longitude = soup.find("meta", attrs={"itemprop": "longitude"})
    if longitude:
        longitude = longitude.attrs["content"]
    if latitude and longitude:
        data["latlon"] = latitude + "," + longitude

    data["url"] = soup.find(text=re.compile(
        r"\s*Página\s+Web\s*", re.MULTILINE | re.IGNORECASE)).findParent("div").find("a")
    if data["url"]:
        data["url"] = data["url"].get_text().strip()

    if soup.find("div", attrs={"data-title": "IES"}):
        data["tipo"] = "IES"

    data["mail"] = soup.find("h3", text=re.compile(
        r"\s*Email\s*", re.MULTILINE | re.IGNORECASE)).findParent("div").find("a")
    if data["mail"]:
        data["mail"] = data["mail"].get_text().strip()

    data["DAT"] = ""
    data["info"] = url
    return data

def subStart(ori, *args, new_start=None):
    for s in args:
        if ori.startswith(s):
            ori = ori[len(s):]
            if new_start:
                ori = new_start + ori
    return ori

def parse_nombre_centro(c):
    abr = get_abr(c.tipo)
    nombre = c.nombre
    if c.id == 28078043 and "alcobendas v" in nombre:
        nombre = "Alcobendas V"
    elif abr == "AH":
        nombre = subStart(nombre, "Aula Hospitalaria Hosp. ", "Aula Hospitalaria ", "Hospital ")
    elif abr.startswith("EOEP"):
        nombre = subStart(nombre, "Equipo General ", "Equipo Gral. ", "Equipo ")
        nombre = subStart(nombre, "E. a. Temprana ", "Eq. Aten.temprana ", "Eq. At.temp. ", "Equipo At. Temp. ", "Eoep de At.tna ", "Eq. Aten. Temprana ", "At. Temp. ", "E.a.temprana ", "Atencion Temprana ")
        nombre = subStart(nombre, "E.e ", "E.e. ")
    elif abr == "SIES":
        nombre = subStart(nombre, "Seccion del Ies ")
    nombre=nombre.replace("s.", "S.")
    nombre=nombre.replace("S.mart", "S. Mart")
    return abr, nombre
