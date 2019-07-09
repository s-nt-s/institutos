import re
import requests
import bs4
import utm
import simplekml
import textwrap

url_gestiona_madrid = "http://gestiona.madrid.org/wpad_pub/run/j/MostrarFichaCentro.icm?cdCentro="
url_buscocolegio = "http://www.buscocolegio.com/Colegio/detalles-colegio.action?id="

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

def get_dificultad():
    dificultad=[]
    anexo29 = False
    with open("data/convocatoria.txt", mode="r", encoding="utf-8") as f:
        for linea in f.readlines():
            linea = re_sp.sub(" ",linea.replace("\x02"," ")).strip()
            if linea.startswith("ANEXO 30"):
                return dificultad
            anexo29 = anexo29 or linea.startswith("ANEXO 29")
            if anexo29:
                cs = centro.findall(linea)
                if len(cs)>0:
                    dificultad.extend(cs)
    return dificultad

def get_data(ctr):
    return get_data1(url_gestiona_madrid, ctr) or get_data2(url_buscocolegio, ctr)

def get_data1(url, ctr):
    r = requests.get(url + ctr)
    soup = bs4.BeautifulSoup(r.text, "html.parser")
    items = soup.select("div.formularioconTit input")
    if len(items)==0:
        return False
    data = {}
    for i in items:
        n = i.attrs.get("name", "").strip()
        v = i.attrs.get("value", "").strip()
        if len(n) > 0 and len(v) > 0:
            data[n] = v
    d = re_sp.sub(" ", soup.find(text=re_dire).findParent(
        "td").get_text()).strip()[11:-1].title()
    data["direccion"] = d
    href = soup.find("div", attrs={"id": "Mapa"}).find("a").attrs["onclick"]
    m = re_coord.search(href)
    data["UTM_ED50-HUSO_30"] = m.group(1) + "," + m.group(2)
    utm_split = data["UTM_ED50-HUSO_30"].split(",")
    latlon = utm.to_latlon(float(utm_split[0]), float(utm_split[1]), 30, 'T')
    data["coord"] = (latlon[1]-0.001283,latlon[0]-0.001904)
    data["latlon"] = str(latlon[0]) + "," + str(latlon[1])
    data["tipo"] = data["tlGenericoCentro"]
    data["nombre"] = data["tlNombreCentro"].title()
    data["url"] = data["tlWeb"]
    data["dat"] = data["tlAreaTerritorial"]
    data["info"] = url + ctr
    tipos_des[data["TIPO"]]=data["tlGenericoExt"].capitalize()
    data["nocturno"] = [get_text(n.findParent("tr").find("td")) for n in soup.findAll(text=re_nocturno)]
    return data


def get_data2(url, ctr):
    r = requests.get(url + ctr)
    soup = bs4.BeautifulSoup(r.text, "html.parser")
    data = {}
    data["nombre"] = get_text(soup.select("div.sliding-panel-inner h4"))
    if data["nombre"].startswith("IES "):
        data["nombre"]= data["nombre"][4:]
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
    data["coord"] = (float(longitude),float(latitude))

    data["url"] = soup.find(text=re.compile(r"\s*Página\s+Web\s*", re.MULTILINE)).findParent("li").find("a").attrs["href"]

    if soup.find("div", attrs={"data-title": "IES"}):
        data["tipo"] = "IES"

    data["DAT"] = ""
    data["info"] = url + ctr
    return data

centro_dificutlad=get_dificultad()

class Centro:
    def __init__(id, *args, **kargv):
        self.id=id
        for k, v in get_data(id).items():
            setattr(self, k, v)
        self.dificultad = self.id in centro_dificutlad
