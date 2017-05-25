# -*- coding: utf-8 -*-
import re
import requests
import bs4
import utm
import simplekml
import textwrap

# pdftotext ANEXO.pdf -table -nopgbrk

centro = re.compile(r"\b(28\d\d\d\d\d\d)\b")
asignatura = re.compile(r"\b(\d\d\d\d\d\d\d)\b")
mates = re.compile(r"\b(MATEMATICAS)\b")
gestiona_madrid = "http://gestiona.madrid.org/wpad_pub/run/j/MostrarFichaCentro.icm?cdCentro="
buscocolegio = "http://www.buscocolegio.com/Colegio/detalles-colegio.action?id="

num = re.compile(r".*?(\d+).*")
sp = re.compile(r"\s+", re.MULTILINE | re.UNICODE)
spc = re.compile(r"\s*Especialidad:\s*(\d+-.*)\s*")
prs = re.compile(r"(.*)\bPuntos:\s(Total:\s.*)")
campos = ["Total", "Año Opos.", "Ptos. Opos.", "Origen", "Mod"]
dec = re.compile(r"^\d+,\d+$")
dire = re.compile(r"^\s*Dirección:", re.MULTILINE | re.UNICODE | re.DOTALL)
coord = re.compile(r"&xIni=([\d\.]+)&yIni=([\d\.]+)")
minusculas = re.compile(r"[a-z]")
nocturno = re.compile(r".*\bnocturno\b.*")

datos = {}
tipos_des = {}
centro1 = None
centro2 = None

def get_dificultad():
    dificultad=[]
    anexo29 = False
    with open("convocatoria.txt", mode="r", encoding="utf-8") as f:
        for linea in f.readlines():
            linea = sp.sub(" ",linea.replace("\x02"," ")).strip()
            if linea.startswith("ANEXO 30"):
                return dificultad
            anexo29 = anexo29 or linea.startswith("ANEXO 29")
            if anexo29:
                cs = centro.findall(linea)
                if len(cs)>0:
                    dificultad.extend(cs)
    return dificultad

dificultad = get_dificultad()

def get_text(n, index=0):
    if type(n) is list:
        n = n[index]
    txt = sp.sub(" ", n.get_text()).strip()
    return txt


def get_data(ctr):
    return get_data1(ctr) or get_data2(ctr)

def get_data1(ctr):
    r = requests.get(gestiona_madrid + ctr)
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
    d = sp.sub(" ", soup.find(text=dire).findParent(
        "td").get_text()).strip()[11:-1].title()
    data["direccion"] = d
    href = soup.find("div", attrs={"id": "Mapa"}).find("a").attrs["onclick"]
    m = coord.search(href)
    data["UTM_ED50-HUSO_30"] = m.group(1) + "," + m.group(2)
    utm_split = data["UTM_ED50-HUSO_30"].split(",")
    latlon = utm.to_latlon(float(utm_split[0]), float(utm_split[1]), 30, 'T')
    data["coord"] = (latlon[1]-0.001283,latlon[0]-0.001904)
    data["latlon"] = str(latlon[0]) + "," + str(latlon[1])
    data["TIPO"] = data["tlGenericoCentro"]
    data["nombre"] = data["tlNombreCentro"].title()
    data["URL"] = data["tlWeb"]
    data["DAT"] = data["tlAreaTerritorial"]
    data["INFO"] = gestiona_madrid + ctr
    tipos_des[data["TIPO"]]=data["tlGenericoExt"].capitalize()
    data["COD"] = ctr
    data["NOCTURNO"] = [get_text(n.findParent("tr").find("td")) for n in soup.findAll(text=nocturno)]
    return data


def get_data2(ctr):
    r = requests.get(buscocolegio + ctr)
    soup = bs4.BeautifulSoup(r.text, "html.parser")
    data = {}
    data["nombre"] = get_text(soup.select("div.sliding-panel-inner h4"))
    if data["nombre"].startswith("IES "):
        data["nombre"]= data["nombre"][4:]
    if not minusculas.search(data["nombre"]):
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

    data["URL"] = soup.find(text=re.compile(r"\s*Página\s+Web\s*", re.MULTILINE)).findParent("li").find("a").attrs["href"]

    if soup.find("div", attrs={"data-title": "IES"}):
        data["TIPO"] = "IES"
    
    data["DAT"] = ""
    data["INFO"] = buscocolegio + ctr
    data["COD"] = ctr
    return data

with open("centros.txt", mode="r", encoding="utf-8") as f:
    for linea in f.readlines():
        linea.strip()
        centros = centro.findall(linea)
        asignaturas = asignatura.findall(linea)

        for c in centros:
            if linea.startswith(c):
                centro1 = c
            else:
                centro2 = c
            if c not in datos:
                datos[c] = []

        for a in asignaturas:
            if linea.startswith(a):
                datos[centro1].append(a)
            else:
                datos[centro2].append(a)

        if len(asignaturas) == 0:
            for m in mates.findall(linea):
                if linea.startswith(m):
                    datos[centro1].append("0590006")
                else:
                    datos[centro2].append("0590006")


matematicas = []
for k, v in datos.items():
    if "0590006" in v:
        matematicas.append(get_data(k))

tipos = list(set(map(lambda x: x["TIPO"], matematicas)))

folders={}

kml=simplekml.Kml()
kml.document.name = "Matemáticas - Madrid"

style_dificultad = simplekml.Style()
style_dificultad.iconstyle.color = simplekml.Color.red
style_dificultad.iconstyle.icon.href = 'http://maps.google.com/mapfiles/ms/micons/red.png'

kml.document.style = style_dificultad

style_nocturno = simplekml.Style()
style_nocturno.iconstyle.color = simplekml.Color.grey
style_nocturno.iconstyle.icon.href = 'http://maps.google.com/mapfiles/ms/micons/grey.png'

kml.document.style = style_nocturno

for t in tipos:
    folder = kml.newfolder(name=t)
    if t in tipos_des:
        folder.name = t +" ("+tipos_des[t]+")"
        folder.description = tipos_des[t]
    folders[t]=folder

for data in matematicas:
    folder = folders[data["TIPO"]]
    pnt = folder.newpoint(name=data["nombre"], coords=[data["coord"]])
    pnt.description = textwrap.dedent(
    '''
        <b>%s</b> %s<br/>
        Dirección: %s<br/>
        URL: %s<br/>
        INFO: %s
    ''' % (data["COD"], data["DAT"], data["direccion"], data["URL"], data["INFO"])
    ).strip()
    if data["COD"] in dificultad:
        pnt.style = style_dificultad
        pnt.description = pnt.description + "<br/>Centro de especial dificultad"
    ntn=data.get("NOCTURNO", [])
    if len(ntn)>0:
        pnt.style = style_nocturno
        pnt.description = pnt.description + "<br/>Nocturno en:"
        for n in ntn:
            pnt.description = pnt.description + "<br/>"+n

kml.save("centros.kml")
