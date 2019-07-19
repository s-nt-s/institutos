import re
from functools import lru_cache

import requests
from bunch import Bunch
import json
import geopy.distance
import copy
from arcgis.gis import GIS

from .centro import get_data, get_abr
from .common import get_pdf, get_soup, mkBunch, read_yml, get_km, unzip, mkBunchParse, to_num, read_csv
from .db import DBshp
from .confmap import parse_nombre, parse_tipo, etapas_ban
from .decorators import *
from shapely.geometry import MultiPolygon, Point, Polygon, shape

re_bocm = re.compile(r".*(BOCM-[\d\-]+).PDF", re.IGNORECASE)
re_location = re.compile(r"document.location.href=\s*[\"'](.*.csv)[\"']")
re_sp = re.compile(r"\s+", re.MULTILINE | re.UNICODE)
re_centro = re.compile(r"\b(28\d\d\d\d\d\d)\b")
re_pdfs = re.compile(r".*\bapplication%2Fpdf\b.*")


class Dataset():
    def __init__(self, *args, **kargs):
        self.indice = mkBunch("fuentes/indice.yml")
        self.fuentes = mkBunch("fuentes/fuentes.yml") or Bunch()
        self.arreglos = read_yml("fuentes/arreglos.yml")

    def dwn_centros(self, file, data=None):
        if data is None:
            data = {}
        data["titularidadPublica"] = "S"
        soup = get_soup(self.indice.centros, data=data)
        codCentrosExp = soup.find(
            "input", attrs={"name": "codCentrosExp"}).attrs["value"].strip()
        if not codCentrosExp:
            open(file, 'w').close()
            return False
        url = soup.find(
            "form", attrs={"id": "frmExportarResultado"}).attrs["action"]

        soup = get_soup(url, data={"codCentrosExp": codCentrosExp})
        script = re_location.search(soup.find("script").string).group(1)
        url = urljoin(url, script)
        r = requests.get(url)
        content = r.content.decode('iso-8859-1')
        content = str.encode(content)
        with open(file, "wb") as f:
            f.write(content)
        return True

    def dwn_and_read(self, file, data=None, **kargv):
        if not os.path.isfile(file):
            if not self.dwn_centros(file, data=data):
                return []
        out = read_csv(file, start=1, null=("-", 0), parse=to_num, **kargv)
        return list(out)

    @property
    @lru_cache(maxsize=None)
    @JsonCache(file="data/centros.json", to_bunch=True)
    def centros(self):
        centros = []
        col_centros = self.dwn_and_read("fuentes/csv/centros.csv")
        total = len(col_centros)
        excluidos={}
        for count, i in enumerate(col_centros):
            print("Cargando centros %s%% [%s]      " % (
                int(count*100/total), total-count), end="\r")
            id = i["CODIGO CENTRO"]
            if id not in self.centro_ok:
                continue
            dir = " ".join(
                [str(s) for s in (i["DOMICILIO"], i["COD. POSTAL"], i["MUNICIPIO"]) if s])
            dat = i["AREA TERRITORIAL"]
            if dat:
                dat = dat.split("-")[-1]
            if dir in ("", "Madrid"):
                dir = None
            extra = get_data(id)
            etapas = extra.get("etapas")
            excluir=[]
            if etapas:
                for e in etapas_ban:
                    if e in etapas:
                        excluir.append(e)
                        etapas.remove(e)
            tipo=self.centro_tipo.get(id) or i["TIPO DE CENTRO"]
            if not etapas and tipo!="036":
                excluidos[(tipo, extra.get("info"))]=excluir
                continue
            arreglo = self.arreglos.get(id, {})
            latlon = arreglo.get("latlon") or extra.get("latlon")
            c = Bunch(
                id=id,
                dat=dat,
                nombre=i["CENTRO"],
                direccion=dir,
                telefono=i["TELEFONO"],
                mail=extra.get("tlMail"),
                latlon=latlon,
                nocturno=extra.get("nocturno"),
                dificultad=id in self.dificultad,
                adaptado=id in self.adaptado,
                excelencia=id in self.excelencia,
                tecnico=id in self.tecnico,
                bilingue=id in self.bilingue,
                url=extra.get("url"),
                info=extra.get("info"),
                tipo=tipo,
                status_web=extra.get("status_web"),
                min_distance=self.min_distance(latlon),
                etapas=etapas
            )
            for k, v in arreglo.items():
                c[k]=v
            if id in self.nocturno and not c.nocturno:
                print(extra["info"])
            centros.append(c)
        centros = sorted(centros, key=lambda c: c.id)
        print("Cargando centros 100%%: %s        " % len(centros))
        if excluidos:
            print("Centros excluidos:")
            for e, lst in excluidos.items():
                print(*e)
                for ex in lst:
                    print(" ", ex)
        return centros

    @property
    @TxtCache(file="fuentes/pdf/vacantes.txt")
    def vacantes(self):
        txt = ''
        for a in get_soup(self.indice.vacantes, select="#textoCuerpo a"):
            href = a.attrs.get("href")
            if re_pdfs.search(href):
                txt = txt + get_pdf(href) + '\n'
        return txt[:-1]

    @property
    @TxtCache(file="fuentes/pdf/convocatoria.txt")
    def convocatoria(self):
        url = get_soup(self.indice.convocatoria,
                       select="#textoCuerpo a", attr="href")
        bocm = re_bocm.search(url).group(1)
        self.fuentes.convocatoria = "http://www.bocm.es/" + bocm.lower()
        return get_pdf(url)
        # return self.fuentes.convocatoria

    @property
    @TxtCache(file="fuentes/pdf/anexo29.txt")
    def anexo29(self):
        return get_pdf(self.indice.anexo29)

    def get_centrosid(self, file=None, txt=True, **kargv):
        if file is None and len(kargv) == 0:
            raise Exception("file argument is mandatory")
        if file is None and len(kargv) > 0:
            k, v = next(iter(kargv.items()))
            if k == "itRegimenNocturno":
                file = "nocturno"
            elif k == "itInTecno":
                file = "tecnico"
            elif k == "cdTramoEdu":
                edu=[v]
                for p in ("cdNivelEdu", "cdEnsenanza", "cdEspecialidad", "cdEspecialidadII"):
                    t = kargv.get(p)
                    if t and not t.startsWith("-"):
                        edu.append(t)
                file = "e"+("_".join(edu))
                txt = False
                if "cdLegislacionSE" not in kargv and self.legislacion:
                    kargv["cdLegislacionSE"]=self.legislacion
            elif k == "cdGenerico":
                file = "t"+v
                txt = False
        if file is None:
            raise Exception("No file name associate to: " +
                            ", ".join(sorted(kargv.keys())))
        if txt is True:
            txt = "data/centros/" + file+".txt"
        file = "fuentes/csv/" + file + ".csv"
        create_txt = txt and not(os.path.isfile(file) and os.path.isfile(txt))
        col_centros = self.dwn_and_read(file, data=kargv)
        out = set(c["CODIGO CENTRO"] for c in col_centros)
        if create_txt:
            with open(txt, "w") as f:
                f.write("\n".join(sorted(str(i) for i in out)))
        return out

    @property
    @lru_cache(maxsize=None)
    def legislacion(self):
        soup = get_soup(self.indice.centros)
        cdLegislacionSE = soup.find("input", attrs={"name": "cdLegislacionSE"})
        if cdLegislacionSE:
            cdLegislacionSE = cdLegislacionSE.attrs["value"].strip()
        return cdLegislacionSE

    @property
    @lru_cache(maxsize=None)
    def nocturno(self):
        return self.get_centrosid(itRegimenNocturno=4)

    @property
    @lru_cache(maxsize=None)
    def bilingue(self):
        return self.get_centrosid("bilingue",
                                  checkCentroBilingue="S",
                                  checkCentroConvenio="S",
                                  checkSeccionesLinguisticasFr="S",
                                  checkSeccionesLinguisticasAl="S",
                                  )

    @property
    @lru_cache(maxsize=None)
    def excelencia(self):
        return self.get_centrosid("excelencia",
                                  itCentroExcelencia="S",
                                  itAulaExcelencia="S"
                                  )

    @property
    @lru_cache(maxsize=None)
    def tecnico(self):
        return self.get_centrosid(itInTecno="S")

    @property
    @lru_cache(maxsize=None)
    def adaptado(self):
        return self.get_centrosid("adaptado",
                                  checkIntegraA="S",
                                  checkIntegraM="S",
                                  checkIntegraT="S"
                                  )

    @property
    @lru_cache(maxsize=None)
    @ListCache(file="data/centros/dificultad.txt", cast=int)
    def dificultad(self):
        dificultad = []
        anexo29 = False
        for linea in self.convocatoria.split("\n"):
            linea = re_sp.sub(" ", linea.replace("\x02", " ")).strip()
            if linea.startswith("ANEXO 30"):
                return dificultad
            anexo29 = anexo29 or linea.startswith("ANEXO 29")
            if anexo29:
                cs = re_centro.findall(linea)
                if len(cs) > 0:
                    dificultad.extend(cs)
        if len(dificultad) == 0:
            dificultad = re_centro.findall(self.anexo29)
        dificultad = set(int(d) for d in dificultad)
        return dificultad

    @property
    @lru_cache(maxsize=None)
    @ListCache(file="data/centros/ok.txt", cast=int, reload=True)
    def centro_ok(self):
        col = set()
        # 020 068 080 081 103 106 120 131 132 151 152 171 180 204 205 206
        for cod in "036 016 017 031 035 042 047 070".split():
            aux = self.get_centrosid(cdGenerico=cod)
            col = col.union(aux)
        return col
        convo = re_centro.findall(self.convocatoria)
        convo = set(int(d) for d in convo)
        return col.intersection(convo)

    @property
    @lru_cache(maxsize=None)
    @JsonCache(file="data/tipos.json")
    def tipos(self):
        soup = get_soup(self.indice.centros)
        tipos = {}
        for o in soup.select("#comboGenericos option"):
            v = o.attrs.get("value")
            if v and v not in ("0", "-1"):
                tipos[v] = re_sp.sub(" ", o.get_text()).strip()
        return tipos

    @property
    @lru_cache(maxsize=None)
    @JsonCache(file="data/ensenanzas.json")
    def ensenanzas(self):
        soup = get_soup(self.indice.centros)
        tipos = {}
        for o in soup.select("#comboTipoEnsenanza option"):
            v = o.attrs.get("value")
            if v and v not in ("0", "-1"):
                tipos[v] = re_sp.sub(" ", o.get_text()).strip()
        return tipos


    def dwn_ensenanzas(self):
        for k in sorted(self.ensenanzas.keys()):
            pass


    @property
    @lru_cache(maxsize=None)
    def centro_tipo(self):
        tipos = {}
        for cod in sorted(self.tipos.keys()):
            for id in self.get_centrosid(cdGenerico=cod):
                c = tipos.get(id, [])
                c.append(cod)
                tipos[id] = c
        for kc, c in list(tipos.items()):
            l = len(c)
            if l == 0:
                tipos[kc] = None
            elif l == 1:
                tipos[kc] = c.pop()
        return tipos

    @property
    def geojson(self):
        geojson = {'type':'FeatureCollection', 'features':[]}
        for c in self.centros:
            if not c.latlon:
                continue
            feature = {'type':'Feature',
                       'properties':{},
                       'geometry':{'type':'Point',
                                   'coordinates':[]}}
            lat, lon = tuple(map(float, c.latlon.split(",")))
            feature['geometry']['coordinates'] = [lon,lat]
            properties = feature['properties']
            for k, v in copy.deepcopy(c).items():
                properties[k] = v
            abr = get_abr(c.tipo)
            if abr:
                nombre=c.nombre
                if c.id == 28078043 and "alcobendas v" in nombre:
                    nombre = "Alcobendas V"
                elif abr == "AH":
                    for s in ("Aula Hospitalaria Hosp. ", "Aula Hospitalaria ", "Hospital "):
                        if nombre.startswith(s):
                            nombre=nombre[len(s):]
                elif abr == "SIES":
                    for s in ("Seccion del Ies ",):
                        if nombre.startswith(s):
                            nombre=nombre[len(s):]
                t = parse_tipo(self.tipos[c.tipo])
                properties["nombre"] = "<span title='{0}'>{1}</span> {2}".format(t, abr, nombre)
            geojson['features'].append(feature)
        return geojson

    @property
    @lru_cache(maxsize=None)
    @JsonCache(file="data/estaciones.json", reload=True)
    def estaciones(self):
        estaciones=set()
        for k in self.indice.transporte.keys():
            for o in read_csv("fuentes/transporte/"+k+"/stops.txt", separator=","):
                lat, lon = float(o["stop_lat"]), float(o["stop_lon"])
                estaciones.add((lat, lon))
        return estaciones

    def unzip(self):
        for k, d in self.indice.transporte.items():
            unzip("fuentes/transporte/"+k, d.data)

    def min_distance(self, latlon):
        if not latlon:
            return None
        lat, lon = tuple(map(float, latlon.split(",")))
        distances = [geopy.distance.vincenty((lat, lon), latlon).m for latlon in self.estaciones]
        return min(distances)

    @property
    @lru_cache(maxsize=None)
    @JsonCache(file="data/overpass.json")
    def overpass(self):
        r = requests.get(self.indice.overpass.transporte)
        return r.json()


    @property
    @lru_cache(maxsize=None)
    @JsonCache(file="data/transporte.json", reload=True)
    def _transporte(self, reload=True):
        db = DBshp("data/transporte.db", reload=True)
        db.execute("sql/base.sql")
        data={}
        for k in self.indice.transporte.keys():
            trips={}
            shapes={}
            for o in read_csv("fuentes/transporte/"+k+"/trips.txt", separator=",", parse=to_num, encoding='utf-8-sig'):
                t = trips.get(o["route_id"], set())
                t.add(o["shape_id"])
                trips[o["route_id"]]=t
            for o in read_csv("fuentes/transporte/"+k+"/shapes.txt", separator=",", parse=to_num, encoding='utf-8-sig'):
                obj = shapes.get(o["shape_id"], [])
                obj.append((o["shape_pt_sequence"], o["shape_pt_lat"], o["shape_pt_lon"]))
                shapes[o["shape_id"]]=obj

            data[k]=[]
            for o in read_csv("fuentes/transporte/"+k+"/routes.txt", separator=",", parse=to_num, encoding='utf-8-sig'):
                obj={}
                route_id = o["route_id"]
                obj["linea"] = o["route_short_name"]
                obj["nombre"] = o["route_long_name"]
                obj["color"] = "#"+o["route_color"]
                obj["url"] = o["route_url"]
                obj["trips"]={}
                for shape_id in sorted(trips[route_id]):
                    points=[]
                    for sec, lat, lon in sorted(shapes[shape_id]):
                        db.insert("linea", orden=sec, tipo=k, nombre=obj["nombre"], shape_id=shape_id, route_id=route_id, point=Point(lon, lat))
                        if len(points)>5:
                            dis1 = geopy.distance.vincenty((lat, lon), points[-1]).m
                            flag=False
                            if dis1>1700:
                                for i in reversed(points):
                                    dis2 = geopy.distance.vincenty((lat, lon), i).m
                                    if dis2<500:
                                        flag=True
                                        break
                            if flag:
                                print(obj["linea"], shape_id, sec)
                                print(dis1, dis2)
                                continue
                        point = (lat, lon)
                        points.append(point)
                    obj["trips"][shape_id]=points
                data[k].append(obj)
        db.commit()
        db.close()
        return data


    @property
    @lru_cache(maxsize=None)
    def geojson_transporte(self, reload=True):
        geojson = {'type':'FeatureCollection', 'features':[]}
        item = {'type':'Feature',
                   'properties':{},
                   'geometry':{'type':'LineString',
                               'coordinates':[]}}
        for red in self.transporte.values():
            for l in red:
                for key, tp in l["trips"].items():
                    pr = copy.deepcopy(l)
                    del pr["trips"]
                    pr["shape_id"]=key
                    ln = copy.deepcopy(item)
                    ln['properties']=pr
                    for lat, lon in tp:
                        ln['geometry']['coordinates'].append((lon, lat))
                    geojson['features'].append(ln)
        return geojson

    def gis(self):
        gis = GIS()

        for k, v in self.indice.transporte.items():
            print(k)
            id = v.capas.split("=")[-1]
            data_item = gis.content.get(id)
            for lyr in data_item.layers:
                if "TRAMO" in lyr.properties.name:
                    print(lyr.url)
                    for f in lyr.properties.fields:
                        print(f['name'])

    @lru_cache(maxsize=None)
    @ParamJsonCache(file="fuentes/transporte/{0}.json")
    def get_tramos(self, tipo):
        r = requests.get(self.indice.transporte[tipo].tramos)
        return r.json()

    @property
    @lru_cache(maxsize=None)
    #@JsonCache(file="data/transporte.json", reload=True)
    def transporte(self):
        for k in self.indice.transporte.keys():
            colors={}
            for o in read_csv("fuentes/transporte/"+k+"/routes.txt", separator=",", parse=to_num, encoding='utf-8-sig'):
                color = "#"+o["route_color"]
                line = o["route_short_name"]
                print(line, color)
                colors[line] = color
            tramo = self.get_tramos(k)
            lineas = set(f["attributes"]["NUMEROLINEAUSUARIO"] for f in tramo["features"])
            print("\n".join(sorted(lineas)))
