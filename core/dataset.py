import copy
import re
from functools import lru_cache
import os
import time

import geopy.distance
import requests
from bunch import Bunch
from shapely.geometry import LineString, Polygon

from .centro import get_abr, get_data, parse_dir, parse_nombre_centro
from .common import (get_km, get_pdf, get_soup, mkBunch, mkBunchParse,
                     read_csv, read_yml, to_num, unzip, read_js)
from .confmap import etapas_ban, parse_nombre, parse_tipo
from .decorators import *
from .web import Web

re_bocm = re.compile(r".*(BOCM-[\d\-]+).PDF", re.IGNORECASE)
re_location = re.compile(r"document.location.href=\s*[\"'](.*.csv)[\"']")
re_sp = re.compile(r"\s+", re.MULTILINE | re.UNICODE)
re_centro = re.compile(r"\b(28\d\d\d\d\d\d)\b")
re_pdfs = re.compile(r".*\bapplication%2Fpdf\b.*")

re_csv_br = re.compile(r"\s*\n\s*")
re_csv_fl = re.compile(r"\s*;\s*")

def add_point(points, lat, lon):
    if len(points) > 5:
        lt, ln = points[-1]
        dis1 = geopy.distance.vincenty((lat, lon), (lt, ln)).m
        if dis1 > 1700:
            for lt, ln in reversed(points):
                dis2 = geopy.distance.vincenty((lat, lon), (lt, ln)).m
                if dis2 < 1600:
                    return
    points.append((lat, lon))


def sort_line(cod):
    if isinstance(cod, dict):
        cod = cod["linea"]
    if isinstance(cod, int):
        nums = [cod]
        cod = str(cod)
    else:
        nums = [int(n) for n in re.findall(r'\d+', cod)]
    while len(nums) < 3:
        nums.append(999)
    nums.append(cod)
    return tuple(nums)


def get_num_linea(tipo, codigolinea, numerolinea):
    cod = None
    if tipo == "metro":
        cod = numerolinea.split("-")[0]
    elif tipo == "cercanias":
        cod = codigolinea
    elif tipo == "metro_ligero":
        cod = "ML"+numerolinea.split("-")[0]
    if cod[-1].lower() in ("a", "b"):
        cod = cod[:-1]
    if cod.isdigit():
        cod = int(cod)
    return cod

class MyException(Exception):
    def __init__(self, code, *args, **kargs):
        super().__init__(*args, **kargs)
        self.code = code

class Dataset():
    TIPOS_OK = "016 017 020 031 035 036 039 042 047 068 070 204 205 206".split()

    def __init__(self, reload_centros=False, *args, **kargs):
        self.indice = mkBunch("fuentes/indice.yml")
        self.fuentes = mkBunch("fuentes/fuentes.yml") or Bunch()
        self.arreglos = read_yml("fuentes/arreglos.yml")
        self.tipo_abr = {v:k for k,v in read_yml("fuentes/tipo_abr.yml").items()}
        self.reload = []
        if reload_centros:
            self.reload.append("data/centros.json")
        if os.path.isfile("data/centros.json"):
            self.reload.append("data/status_web.json")
            self.status_web

    def _dwn_centros(self, file, data=None, _intentos=2):
        if data is None:
            data = {}
        data["titularidadPublica"] = "S"
        tipo_centro = data.get("cdGenerico")
        soup = get_soup(self.indice.centros, data=data)
        if tipo_centro is not None:
            tp = soup.select("#comboGenericos option[selected]")
            if tp and tp[-1].attrs["value"]!=tipo_centro:
                tp = tp[-1].attrs["value"]
                raise MyException(1, "Se pidio cdGenerico=%s pero se obtuvo %s" % (tipo_centro, tp))
        codCentrosExp = soup.find(
            "input", attrs={"name": "codCentrosExp"})
        if codCentrosExp is None:
            raise MyException(2, "Falta codCentrosExp")
        codCentrosExp = codCentrosExp.attrs["value"].strip()
        if not codCentrosExp:
            if _intentos and not("CENTRO PRIVADO " in self.tipos.get(tipo_centro, "")):
                time.sleep(15)
                return self._dwn_centros(file, data=data, _intentos=_intentos-1)
            open(file, 'w').close()
            return False
        url = soup.find(
            "form", attrs={"id": "frmExportarResultado"})
        url = url.attrs["action"]
        soup = get_soup(url, data={"codCentrosExp": codCentrosExp})
        script = soup.find("script")
        error = soup.select_one("#detalle_error")
        if error is not None and script is None:
            raise Exception(error.get_text().strip())
        script = re_location.search(script.string).group(1)
        url = urljoin(url, script)
        r = requests.get(url)
        if r.status_code == 404:
            raise Exception("{} not found ({})".format(url, r.status_code))
        content = r.content.decode('iso-8859-1')
        rows = content.strip()
        rows = re_csv_br.split(rows)
        rows = rows[2:]
        rows = [re_csv_fl.split(r) for r in rows]
        ids = tuple(sorted(set(r[1] for r in rows)))
        if ids != tuple(sorted(set(codCentrosExp.split(";")))):
            raise MyException(1, "No se han devuelto los mismos centros que se solicitaron")
        if tipo_centro:
            tipo = set(r[2] for r in rows)
            if len(tipo)==0:
                raise Exception("csv sin tipo")
            elif len(tipo) == 1:
                tipo = tipo.pop()
                tp = self.tipo_abr.get(tipo)
                if tp != tipo_centro:
                    raise MyException(1, "Se pidio cdGenerico=%s pero se obtuvo %s" % (tipo_centro, (tp, tipo)))
            else:
                tipo = tuple(sorted(tipo))
                raise MyException(1, "Se pidio cdGenerico=%s pero se obtuvo %s" % (tipo_centro, tipo))
        content = str.encode(content)
        with open(file, "wb") as f:
            f.write(content)
        return True

    def dwn_centros(self, *args, intentos=3, **kargv):
        try:
            return self._dwn_centros(*args, **kargv)
        except MyException as e:
            if intentos>0:
                print(str(e))
                if e.code==2:
                    time.sleep(15)
                else:
                    time.sleep(30)
                return self.dwn_centros(*args, **kargv, intentos=intentos-1)
            raise e from None


    def dwn_and_read(self, file, data=None, maxOld=1, **kargv):
        if maxOld is not None:
            maxOld = time.time() - (maxOld * 86400)
        if not os.path.isfile(file) or (maxOld is not None and os.stat(file).st_mtime < maxOld):
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
        total_antes = len(col_centros)
        col_centros = [c for c in col_centros if c["CODIGO CENTRO"] in self.centro_ok]
        total = len(col_centros)
        print(total_antes-total, "centros descartados por tipo")
        excluidos = {}
        for count, i in enumerate(col_centros):
            print("Cargando centros %s%% [%s]      " % (
                int(count*100/total), total-count), end="\r")
            id = i["CODIGO CENTRO"]
            dir = " ".join(
                [str(s) for s in (i["DOMICILIO"], i["COD. POSTAL"], i["MUNICIPIO"]) if s])
            dat = i["AREA TERRITORIAL"]
            if dat:
                dat = dat.split("-")[-1]
            if dir in ("", "Madrid"):
                dir = None
            extra = get_data(id, self.status_web)
            etapas = extra.get("etapas")
            exist_etapas = etapas and len(etapas) > 0
            excluir = []
            if etapas:
                for e in etapas_ban:
                    if e in etapas:
                        excluir.append(e)
                        etapas.remove(e)
            tipo = self.centro_tipo.get(id) or i["TIPO DE CENTRO"]
            if exist_etapas and not etapas:
                continue
            if extra.get("latlon"):
                lat, lon = extra["latlon"].split(",")
                lat = lat.split(".")
                lat = lat[0]+"."+lat[1][:10]
                lon = lon.split(".")
                lon = lon[0]+"."+lon[1][:10]
                extra["latlon"] = lat+","+lon
            c = Bunch(
                id=id,
                dat=dat,
                nombre=i["CENTRO"],
                direccion=dir,
                telefono=i["TELEFONO"],
                mail=extra.get("mail"),
                latlon=extra.get("latlon"),
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
                min_distance=None,
                etapas=etapas,
                idiomas=[]
            )
            arreglo = self.arreglos.get(id, {})
            for k, v in arreglo.items():
                c[k]=v
            c.min_distance=self.min_distance(c.latlon)
            if id in self.ingles:
                c.idiomas.append("EN")
            if id in self.aleman:
                c.idiomas.append("DE")
            if id in self.frances:
                c.idiomas.append("FR")
            for k, v in arreglo.items():
                c[k] = v
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

    def centros_candidatos(self):
        candi = self.convocatoria.split(
            "Anexo 12 Institutos de Enseñanza Secundaria, Secciones y Colegios que imparten Enseñanza Secundaria Obligatoria", 1)
        candi = candi[-1]
        candi = candi.split(
            "ANEXO 13 INSTITUTOS DE ENSEÑANZA SECUNDARIA BILINGÚES Y COLEGIOS QUE", 1)
        candi = candi[0]
        candi = re_centro.findall(candi)
        candi = set(int(d) for d in candi)
        cuerpos = re.findall(r"\bCu:\s*(\d+)", self.asignacion)
        destinos = re.findall(r"\bDestino actual:([\s\d]+)", self.asignacion)
        for c, d in zip(cuerpos, destinos):
            c = int(c)
            d = d.strip()
            if c == 590 and d:
                candi.add(int(d))
        tipos = {}
        for c in self.dwn_and_read("fuentes/csv/centros.csv"):
            if c["CODIGO CENTRO"] in candi:
                id = c["CODIGO CENTRO"]
                tipo = self.centro_tipo.get(id)
                col = tipos.get(tipo, [])
                col.append(str(id))
                tipos[tipo] = col
        for t, v in sorted(tipos.items()):
            # if t in Dataset.TIPOS_OK:
            #     continue
            print(t, self.tipos[t])
            print("  ", ", ".join(v))
        # for t in Dataset.TIPOS_OK:
        #      if t not in tipos:
        #          print(t, self.tipos[t])

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
    @TxtCache(file="fuentes/pdf/asignacion.txt")
    def asignacion(self):
        soup = get_soup(self.indice.asignacion)
        td = soup.find("td", text=re.compile(
            r"\s*Listado\s*alfab.*tico\s*de\s*participantes\.\s*"))
        url = td.parent.find("a").attrs["href"]
        self.fuentes.asignacion = url
        return get_pdf(url)

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
                edu = [v]
                for p in ("cdNivelEdu", "cdEnsenanza", "cdEspecialidad", "cdEspecialidadII"):
                    t = kargv.get(p)
                    if t and not t.startsWith("-"):
                        edu.append(t)
                file = "e"+("_".join(edu))
                txt = False
                if "cdLegislacionSE" not in kargv and self.legislacion:
                    kargv["cdLegislacionSE"] = self.legislacion
            elif k == "cdGenerico":
                file = "t"+v
                txt = False
        if file is None:
            raise Exception("No file name associate to: " +
                            ", ".join(sorted(kargv.keys())))
        if txt is True:
            txt = "data/centros/" + file+".txt"
        file = "fuentes/csv/" + file + ".csv"
        col_centros = self.dwn_and_read(file, data=kargv)
        out = set(c["CODIGO CENTRO"] for c in col_centros)
        if txt and isinstance(txt, str):
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
    def ingles(self):
        return self.get_centrosid("ingles",
                                  checkCentroBilingue="S",
                                  checkCentroConvenio="S",
                                  )
    @property
    @lru_cache(maxsize=None)
    def aleman(self):
        return self.get_centrosid("aleman", checkSeccionesLinguisticasAl="S")

    @property
    @lru_cache(maxsize=None)
    def frances(self):
        return self.get_centrosid("frances", checkSeccionesLinguisticasFr="S")

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
        # 036 Aulas hospitalarias no son elegibles por concurso
        for cod in Dataset.TIPOS_OK:
            aux = self.get_centrosid(cdGenerico=cod)
            col = col.union(aux)
        return col

    @property
    @lru_cache(maxsize=None)
    @JsonCache(file="data/tipos.json", reload=True)
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
    @JsonCache(file="data/ensenanzas.json", reload=True)
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
            else:
                tipos[kc] = tuple(c)
        return tipos

    @property
    def geocentros(self):
        coordinates = set()
        geojson = {'type': 'FeatureCollection', 'features': []}
        for c in self.centros:
            if not c.latlon:
                continue
            feature = {'type': 'Feature',
                       'properties': {},
                       'geometry': {'type': 'Point',
                                    'coordinates': []}}
            lat, lon = tuple(map(float, c.latlon.split(",")))
            while (lon, lat) in coordinates:
                lon = lon + 0.0001
            feature['geometry']['coordinates'] = (lon, lat)
            coordinates.add(feature['geometry']['coordinates'])
            properties = feature['properties']
            for k, v in copy.deepcopy(c).items():
                properties[k] = v
            abr, nombre = parse_nombre_centro(c)
            t = parse_tipo(self.tipos[c.tipo])
            properties["direccion"] = parse_dir(properties["direccion"])
            properties["nombre"] = "<span title='{0}'>{1}</span> {2}".format(t, abr, nombre)
            geojson['features'].append(feature)
        return geojson

    def unzip(self):
        for k, d in self.indice.transporte.redes.items():
            unzip("fuentes/transporte/"+k, d.gtfs.data)

    def min_distance(self, latlon):
        if not latlon:
            return None
        lat, lon = tuple(map(float, latlon.split(",")))
        distances = [geopy.distance.vincenty(
            (lat, lon), (e["lat"], e["lon"])).m for e in self.accesos + self.estaciones]
        return round(min(distances))

    @property
    @lru_cache(maxsize=None)
    # @JsonCache(file="data/transporte.json", reload=True)
    def old_transporte(self, reload=True):
        data = {}
        for k in self.indice.transporte.redes.keys():
            trips = {}
            shapes = {}
            for o in read_csv("fuentes/transporte/"+k+"/trips.txt", separator=",", parse=to_num, encoding='utf-8-sig'):
                t = trips.get(o["route_id"], set())
                t.add(o["shape_id"])
                trips[o["route_id"]] = t
            for o in read_csv("fuentes/transporte/"+k+"/shapes.txt", separator=",", parse=to_num, encoding='utf-8-sig'):
                obj = shapes.get(o["shape_id"], [])
                obj.append((o["shape_pt_sequence"],
                            o["shape_pt_lat"], o["shape_pt_lon"]))
                shapes[o["shape_id"]] = obj

            data[k] = []
            for o in read_csv("fuentes/transporte/"+k+"/routes.txt", separator=",", parse=to_num, encoding='utf-8-sig'):
                obj = {}
                route_id = o["route_id"]
                obj["linea"] = o["route_short_name"]
                obj["nombre"] = o["route_long_name"]
                obj["color"] = "#"+o["route_color"]
                obj["url"] = o["route_url"]
                obj["trips"] = {}
                for shape_id in sorted(trips[route_id]):
                    points = []
                    for sec, lat, lon in sorted(shapes[shape_id]):
                        add_point(points, lat, lon)
                    obj["trips"][shape_id] = points
                data[k].append(obj)
        return data

    @lru_cache(maxsize=None)
    @ParamJsonCache(file="fuentes/transporte/{0}/{1}.json", reload=False, maxOld=None)
    def get_transporte_info(self, tipo, field):
        prm = self.indice.transporte.api.default.copy()
        for k, v in self.indice.transporte.api[field].items():
            prm[k] = v
        url = self.indice.transporte.redes[tipo][field].data + prm["path"]
        del prm["path"]
        for k, v in prm.items():
            url = url + "&"+k+"="+v
        r = requests.get(url)
        return r.json()

    @property
    @lru_cache(maxsize=None)
    @JsonCache(file="data/accesos.json", reload=False, maxOld=None)
    def accesos(self):
        data = {}
        for k in self.indice.transporte.redes.keys():
            itinerario = self.get_transporte_info(k, "itinerario")
            accesos = self.get_transporte_info(k, "accesos")
            meta = {}
            cod_demo = {}
            for f in itinerario["features"]:
                a = f["attributes"]
                codigo = a["CODIGOESTACION"]
                if k in ("metro", "metro_ligero"):
                    cod_demo[codigo] = a["DENOMINACION"]
                    codigo = a["DENOMINACION"]
                dt = meta.get(codigo, {"nombres": set(), "lineas": set()})
                cod = get_num_linea(
                    k, a["CODIGOGESTIONLINEA"], a["NUMEROLINEAUSUARIO"])
                meta[codigo] = dt
                dt["nombres"].add(a["DENOMINACION"])
                dt["lineas"].add((k, cod))
            for f in accesos["features"]:
                xy = f["geometry"]
                lat = xy["y"]
                lon = xy["x"]
                cod = f["attributes"]["CODIGOESTACION"]
                if k in ("metro", "metro_ligero"):
                    cod = cod_demo[cod]
                if cod not in meta:
                    #print(lat,lon, f["attributes"]["DENOMINACION"])
                    continue
                key = (lat, lon)
                acceso = data.get(
                    key, {"lat": lat, "lon": lon, "nombre": set(), "lineas": set()})
                data[key] = acceso
                m = meta[cod]
                acceso["nombre"] = acceso["nombre"].union(m["nombres"])
                acceso["lineas"] = acceso["lineas"].union(m["lineas"])
        data = list(data.values())
        for e in data:
            e["nombre"] = parse_nombre(e["nombre"].pop())
            e["lineas"] = list(
                sorted(e["lineas"], key=lambda x: sort_line(x[1])))
            for k, v in list(e.items()):
                if isinstance(v, set):
                    e[k] = list(sorted(v))
        return data

    @property
    @lru_cache(maxsize=None)
    @JsonCache(file="data/estaciones.json", reload=False, maxOld=None)
    def estaciones(self):
        data = {}
        for k in self.indice.transporte.redes.keys():
            meta = {}
            itinerario = self.get_transporte_info(k, "itinerario")
            for f in itinerario["features"]:
                a = f["attributes"]
                codigo = a["CODIGOESTACION"]
                nombre = a["DENOMINACION"]
                if k == "cercanias" and nombre == "ATOCHA":
                    nombre = "ATOCHA RENFE"
                elif k == "cercanias" and nombre == "GETAFE CENTRO":
                    nombre = "GETAFE CENTRAL"
                elif k == "metro_ligero" and nombre == "ESTACION DE ARAVACA":
                    nombre = "ARAVACA"
                dt = meta.get(codigo, {"nombres": set(), "lineas": set()})
                cod = get_num_linea(
                    k, a["CODIGOGESTIONLINEA"], a["NUMEROLINEAUSUARIO"])
                meta[codigo] = dt
                dt["nombres"].add(nombre)
                dt["lineas"].add((k, cod))
            estaciones = self.get_transporte_info(k, "estaciones")
            for f in estaciones["features"]:
                a = f["attributes"]
                xy = f["geometry"]
                lat = xy["y"]
                lon = xy["x"]
                cod = a["CODIGOESTACION"]
                if cod not in meta:
                    #print(lat,lon, f["attributes"]["DENOMINACION"])
                    continue
                m = meta[cod]
                key = (lat, lon)
                estacion = data.get(
                    key, {"lat": lat, "lon": lon, "nombre": set(), "lineas": set()})
                data[key] = estacion
                estacion["nombre"] = estacion["nombre"].union(m["nombres"])
                estacion["lineas"] = estacion["lineas"].union(m["lineas"])
        data = list(data.values())
        for e in data:
            if len(e["nombre"]) > 1:
                print(e["nombre"])
            e["nombre"] = parse_nombre(e["nombre"].pop())
        nombres = set(e["nombre"] for e in data)
        for n in sorted(nombres):
            es = [e for e in data if e["nombre"] == n]
            if len(es) > 1:
                max_dis = 0
                for e1 in es:
                    for e2 in es:
                        if e1 != e2:
                            m = geopy.distance.vincenty(
                                (e1["lat"], e1["lon"]), (e2["lat"], e2["lon"])).m
                            max_dis = max(max_dis, m)
                if max_dis > 1000:
                    continue
                coords = [(e["lat"], e["lon"], 0) for e in es]
                pol = Polygon(coords) if len(
                    coords) > 2 else LineString(coords)
                ct = pol.centroid
                lat, lon = ct.x, ct.y
                es[0]["lat"] = lat
                es[0]["lon"] = lon
                for e in es[1:]:
                    es[0]["lineas"] = es[0]["lineas"].union(e["lineas"])
                    data.remove(e)
        for e in data:
            e["lineas"] = list(
                sorted(e["lineas"], key=lambda x: (x[0], sort_line(x[1]))))
        return data

    @property
    @lru_cache(maxsize=None)
    @JsonCache(file="data/transporte.json", reload=False, maxOld=None)
    def transporte(self):
        datas = {}
        for k in self.indice.transporte.redes.keys():
            colors = {}
            for o in read_csv("fuentes/transporte/"+k+"/routes.txt", separator=",", parse=to_num, encoding='utf-8-sig'):
                color = "#"+o["route_color"]
                line = o["route_short_name"]
                colors[line] = color
            data = {}
            tramos = self.get_transporte_info(k, "tramos")
            lineas = set((f["attributes"]["CODIGOGESTIONLINEA"], f["attributes"]
                          ["NUMEROLINEAUSUARIO"]) for f in tramos["features"])

            for l1, l2 in sorted(lineas):
                cod = get_num_linea(k, l1, l2)
                linea = data.get(
                    cod, {"tipo": k, "linea": cod, "color": colors[cod], "codigos": [], "trips": {}})
                if l1 not in linea["codigos"]:
                    linea["codigos"].append(l1)
                data[cod] = linea
                rutas = {}
                for f in tramos["features"]:
                    if f["attributes"]["CODIGOGESTIONLINEA"] == l1:
                        id_tramo = f["attributes"]["OBJECTID"]
                        sentido = f["attributes"]["SENTIDO"]
                        orden = f["attributes"]["NUMEROORDEN"]
                        paths = f["geometry"]["paths"]
                        if id_tramo not in rutas:
                            rutas[id_tramo] = []
                        rutas[id_tramo].append((orden, paths))
                for ruta, geo in sorted(rutas.items()):
                    points = []
                    for _, paths in sorted(geo):
                        for pts in paths.pop():
                            lon, lat = pts
                            points.append((lat, lon))
                            #add_point(points, lat, lon, k, cod, ruta)
                    linea["trips"][ruta] = points
            datas[k] = sorted(data.values(), key=sort_line)
        datas = {k: v for k, v in sorted(
            datas.items(), key=lambda x: (-len(x[1]), x[0]))}
        return datas

    @property
    @lru_cache(maxsize=None)
    def geotransporte(self):
        geojson = {'type': 'FeatureCollection', 'features': []}
        item = {'type': 'Feature',
                'properties': {},
                'geometry': {'type': 'LineString',
                             'coordinates': []}}
        for red in self.transporte.values():
            for l in red:
                for key, tp in l["trips"].items():
                    pr = copy.deepcopy(l)
                    del pr["trips"]
                    del pr["codigos"]
                    ln = copy.deepcopy(item)
                    ln['properties'] = pr
                    for lat, lon in tp:
                        ln['geometry']['coordinates'].append((lon, lat))
                    geojson['features'].append(ln)

        item["geometry"]["type"] = "Point"
        for e in self.estaciones:
            f = copy.deepcopy(item)
            f['geometry']['coordinates'] = [e["lon"], e["lat"]]
            p = f['properties']
            for k, v in e.items():
                if k not in ("lat", "lon"):
                    p[k] = v
            geojson['features'].append(f)
        return geojson


    @property
    @lru_cache(maxsize=None)
    @JsonCache(file="data/status_web.json")
    def status_web(self):
        cs = read_js("data/centros.json") or []
        stweb = {c["url"]:c["status_web"] for c in cs if c.get("url")}
        return stweb
