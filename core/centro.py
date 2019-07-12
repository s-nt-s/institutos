import re

import bs4
import requests
import simplekml
import utm

from .common import get_soup
from .utm_to_geo import utm_to_geo

re_sp = re.compile(r"\s+", re.MULTILINE | re.UNICODE)
re_dire = re.compile(r"^\s*Dirección:", re.MULTILINE | re.UNICODE | re.DOTALL)
re_coord = re.compile(r"&xIni=([\d\.]+)&yIni=([\d\.]+)")
re_minusculas = re.compile(r"[a-z]")
re_nocturno = re.compile(r".*\bnocturno\b.*")


def get_text(n, index=0):
    if type(n) is list:
        n = n[index]
    txt = re_sp.sub(" ", n.get_text()).strip()
    return txt


def get_data(ctr):
    ctr = str(ctr)
    d1 = get_data1(ctr)
    if d1 is not None:
        if not d1.get("latlon"):
            d2 = get_data2(ctr)
            d1["latlon"] = d2.get("latlon")
        return d1
    return get_data2(ctr)


def get_data1(ctr):
    url = "http://gestiona.madrid.org/wpad_pub/run/j/MostrarFichaCentro.icm?cdCentro=" + ctr
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
        lon, lat = utm_to_geo(30, x, y, "ED50")
        data["latlon"] = str(lat) + "," + str(lon)
    data["tipo"] = data["tlGenericoCentro"]
    data["nombre"] = data["tlNombreCentro"].title()
    data["url"] = data.get("tlWeb")
    data["dat"] = data.get("tlAreaTerritorial")
    data["info"] = url
    # tipos_des[data["TIPO"]]=data["tlGenericoExt"].capitalize()
    data["nocturno"] = [get_text(n.findParent("tr").find("td"))
                        for n in soup.findAll(text=re_nocturno)]
    if len(data["nocturno"]) == 0:
        data["nocturno"] = None
    return data


def get_data2(ctr):
    data = {}
    url = "http://www.buscocolegio.com/Colegio/detalles-colegio.action?id=" + ctr
    soup = get_soup(url, to_file="fuentes/buscocolegio.com/"+ctr+".html")
    cod = soup.find("h3", text="Código").parent.find("strong").string
    if ctr != cod:
        return data
    data["nombre"] = get_text(soup.select("div.sliding-panel-inner h4"))
    if data["nombre"].startswith("IES "):
        data["nombre"] = data["nombre"][4:]
    if not re_minusculas.search(data["nombre"]):
        data["nombre"] = data["nombre"].title()
    data["direccion"] = get_text(
        soup.find("div", attrs={"data-title": "Localización"}).find("h1"))
    data["direccion"] = data["direccion"].replace("(Madrid)", "Madrid")
    latitude = soup.find("meta", attrs={"itemprop": "latitude"}).attrs[
        "content"]
    longitude = soup.find("meta", attrs={"itemprop": "longitude"}).attrs[
        "content"]
    data["latlon"] = latitude + "," + longitude

    data["url"] = soup.find(text=re.compile(
        r"\s*Página\s+Web\s*", re.MULTILINE)).findParent("li").find("a").attrs["href"]

    if soup.find("div", attrs={"data-title": "IES"}):
        data["tipo"] = "IES"

    data["DAT"] = ""
    data["info"] = url
    return data
