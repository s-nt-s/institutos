#!/usr/bin/python3
# -*- coding: utf-8 -*-

import tempfile
import requests
import bs4
import re
import shutil
from urllib.request import urlretrieve
from subprocess import call, check_output
from urllib.parse import urljoin

re_pdfs = re.compile(r".*\bapplication%2Fpdf\b.*")
re_location = re.compile(r"document.location.href=\s*[\"'](.*.csv)[\"']")
tmp = tempfile.mkdtemp() + "/"
tpf = tmp+"pdf.pdf"
ttx = tmp+"pdf.txt"

def get_soup(url, id=None):
    r = requests.get(url)
    soup = bs4.BeautifulSoup(r.content, "html.parser")
    for n in soup.findAll(["a", "form"]):
        att = "href" if n.name=="a" else "action"
        href = n.attrs.get(att)
        if href and not href.startswith("#"):
            n.attrs[att]=urljoin(url, href)
    if id:
        soup = soup.find("div", attrs={"id": id})
    return soup

url_convocatoria = "http://www.madrid.org/cs/Satellite?c=EDRH_Generico_FA&cid=1354540246227&pagename=PortalEducacionRRHH%2FEDRH_Generico_FA%2FEDRH_generico"
url_centros = "http://www.madrid.org/wpad_pub/run/j/BusquedaAvanzada.icm"
url_vacantes = "http://www.madrid.org/cs/Satellite?c=EDRH_Generico_FA&cid=1354646480519&pagename=PortalEducacionRRHH%2FEDRH_Generico_FA%2FEDRH_generico"

pdftotext = "pdftotext -layout -nopgbrk".split()

with open("data/vacantes.txt", mode="w", encoding="utf-8") as f:
    for a in get_soup(url_vacantes, id="textoCuerpo").findAll("a", attrs={"href": re_pdfs}):
        href = a.attrs["href"]
        print(href, ">> vacantes.txt", )
        urlretrieve(href, tpf)
        call(pdftotext + [tpf])
        with open(ttx, mode="r", encoding="utf-8") as infile:
            f.write(infile.read())

def pdf_txt(url, txt):
    print(url, ">", txt)
    urlretrieve(url, tpf)
    call(pdftotext + [tpf])
    shutil.copy(ttx, "data/"+txt)

url_convocatoria = get_soup(url_convocatoria, id="textoCuerpo").find("a").attrs["href"]
pdf_txt(url_convocatoria, "convocatoria.txt")

print(url_centros, ">", "centros.csv")
soup = get_soup(url_centros)
codCentrosExp = soup.find("input", attrs={"name":"codCentrosExp"}).attrs["value"]
url_centros = soup.find("form", attrs={"id": "frmExportarResultado"}).attrs["action"]
r = requests.post(url_centros, data={"codCentrosExp":codCentrosExp})
soup = bs4.BeautifulSoup(r.content, "html.parser")
script = re_location.search(soup.find("script").string).group(1)
url_centros = urljoin(url_centros, script)
print(url_centros, ">", "centros.csv")
r = requests.get(url_centros)
content = r.content.decode('iso-8859-1')
content = str.encode(content)
with open("data/centros.csv", "wb") as f:
    f.write(content)
