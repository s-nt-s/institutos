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


class Dataset():
    def __init__(self, *args, **kargs):
        self.indice = mkBunch("fuentes/indice.yml")
        self.fuentes = mkBunch("fuentes/fuentes.yml") or Bunch()

    def dwn_centros(self, file):
        soup = get_soup(self.indice.centros)
        codCentrosExp = soup.find(
            "input", attrs={"name": "codCentrosExp"}).attrs["value"]
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

    @property
    @JsonCache(file="data/centros.json")
    def centros(self):
        file = "fuentes/csv/centros.csv"
        if False and not os.path.isfile(file):
            self.dwn_centros(file)
        centros = []
        col_centros=list(read_csv(file, start=1, where={"TITULARIDAD":"Público"}, null=("-", 0)))
        total = len(col_centros)
        for count, i in enumerate(col_centros):
            print("Cargando centros %s%% [%s]      " % (int(count*100/total), total-count), end="\r")
            id = i["CODIGO CENTRO"]
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
                dificultad=id in self.dificultad,
                latlon=extra.get("latlon"),
                url=extra["url"],
                info=extra["info"],
                nocturno=extra.get("nocturno")
            )
            centros.append(c)
        centros = sorted(centros, key=lambda c: c.id)
        print("Cargando centros 100%              ")
        return centros

    @property
    @TxtCache(file="fuentes/pdf/vacantes.txt")
    def vacantes(self):
        txt = ''
        for a in get_soup(url_vacantes, select="#textoCuerpo a"):
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

    @property
    @lru_cache(maxsize=None)
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
        dificultad = [int(d) for d in dificultad]
        return dificultad
