import re
from functools import lru_cache

import requests
from bunch import Bunch

from .centro import get_data
from .common import get_pdf, get_soup, mkBunch
from .decorators import *

re_bocm = re.compile(r".*(BOCM-[\d\-]+).PDF", re.IGNORECASE)
re_location = re.compile(r"document.location.href=\s*[\"'](.*.csv)[\"']")
re_sp = re.compile(r"\s+", re.MULTILINE | re.UNICODE)
re_centro = re.compile(r"\b(28\d\d\d\d\d\d)\b")
re_pdfs = re.compile(r".*\bapplication%2Fpdf\b.*")

class Dataset():
    def __init__(self, *args, **kargs):
        self.indice = mkBunch("fuentes/indice.yml")
        self.fuentes = mkBunch("fuentes/fuentes.yml") or Bunch()

    def dwn_centros(self, file, data=None):
        if data is None:
            data={}
        data["titularidadPublica"]="S"
        soup = get_soup(self.indice.centros, data=data)
        codCentrosExp = soup.find(
            "input", attrs={"name": "codCentrosExp"}).attrs["value"].strip()
        if not codCentrosExp:
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
        out = read_csv(file, start=1, null=("-", 0), **kargv)
        return list(out)

    @property
    @JsonCache(file="data/centros.json")
    def centros(self):
        centros = []
        col_centros = self.dwn_and_read("fuentes/csv/centros.csv")
        total = len(col_centros)
        for count, i in enumerate(col_centros):
            print("Cargando centros %s%% [%s]      " % (int(count*100/total), total-count), end="\r")
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
            c = Bunch(
                id=id,
                dat=dat,
                tipo=i["TIPO DE CENTRO"],
                nombre=i["CENTRO"],
                direccion=dir,
                telefono=i["TELEFONO"],
                mail=extra.get("tlMail"),
                latlon=extra.get("latlon"),
                nocturno=extra.get("nocturno"),
                dificultad=id in self.dificultad,
                adaptado=id in self.adaptado,
                excelencia=id in self.excelencia,
                tecnico= id in self.tecnico,
                bilingue= id in self.bilingue,
                url=extra["url"],
                info=extra["info"],
            )
            if id in self.nocturno and not c.nocturno:
                print(extra["info"])
            centros.append(c)
        centros = sorted(centros, key=lambda c: c.id)
        print("Cargando centros 100%%: %s        " % len(centros))
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
        return get_pdf(url)
        # bocm = re_bocm.search(url).group(1)
        # self.fuentes.convocatoria = "http://www.bocm.es/" + bocm.lower()
        # return self.fuentes.convocatoria

    @property
    @TxtCache(file="fuentes/pdf/anexo29.txt")
    def anexo29(self):
        return get_pdf(self.indice.anexo29)

    def get_centrosid(self, file, **kargv):
        col_centros = self.dwn_and_read(file, data=kargv)
        out = set(c["CODIGO CENTRO"] for c in col_centros)
        return out

    @property
    @lru_cache(maxsize=None)
    @ListCache(file="data/centros/nocturno.txt", cast=int)
    def nocturno(self):
        return self.get_centrosid("fuentes/csv/nocturno.csv", itRegimenNocturno=4)

    @property
    @lru_cache(maxsize=None)
    @ListCache(file="data/centros/bilingue.txt", cast=int)
    def bilingue(self):
        return self.get_centrosid("fuentes/csv/bilingue.csv",
            checkCentroBilingue="S",
            checkCentroConvenio="S",
            checkSeccionesLinguisticasFr="S",
            checkSeccionesLinguisticasAl="S",
        )

    @property
    @lru_cache(maxsize=None)
    @ListCache(file="data/centros/excelencia.txt", cast=int)
    def excelencia(self):
        return self.get_centrosid("fuentes/csv/excelencia.csv",
            itCentroExcelencia="S",
            itAulaExcelencia="S"
        )

    @property
    @lru_cache(maxsize=None)
    @ListCache(file="data/centros/tecnico.txt", cast=int)
    def tecnico(self):
        return self.get_centrosid("fuentes/csv/tecnico.csv",
            itInTecno="S",
        )

    @property
    @lru_cache(maxsize=None)
    @ListCache(file="data/centros/adaptado.txt", cast=int)
    def adaptado(self):
        return self.get_centrosid("fuentes/csv/adaptado.csv",
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
    @ListCache(file="data/centros/ok.txt", cast=int)
    def centro_ok(self):
        col = set()
        for cod in ("042", "303", "094", "016", "017", "031", "035", "070", "032", "042", "047"):
            aux = self.get_centrosid("fuentes/csv/"+cod+".csv",
                cdGenerico=cod,
            )
            col = col.union(aux)
        return col

    @property
    @lru_cache(maxsize=None)
    @JsonCache(file="data/tipos.json")
    def tipos(self):
        soup = get_soup(self.indice.centros)
        tipos={}
        for o in soup.select("#comboGenericos option"):
            v = o.attrs.get("value")
            if v and v!="0":
                tipos[v]=re_sp.sub(" ",o.get_text()).strip()
        return tipos
