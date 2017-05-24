#!/usr/bin/python3
# -*- coding: utf-8 -*-

import tempfile
import requests
import bs4
import re
from urllib.request import urlretrieve
from subprocess import call, check_output

pdfs = re.compile(r".*\bapplication%2Fpdf\b.*")
tmp = tempfile.mkdtemp() + "/"
tpf = tmp+"pdf.pdf"
ttx = tmp+"pdf.txt"

centros = "http://www.madrid.org/cs/Satellite?c=EDRH_Generico_FA&cid=1354646480519&pagename=PortalEducacionRRHH%2FEDRH_Generico_FA%2FEDRH_generico"
pdftotext = "pdftotext -layout -nopgbrk".split()

r = requests.get(centros)
soup = bs4.BeautifulSoup(r.text, "html.parser")

cuerpo = soup.find("div", attrs={"id": "textoCuerpo"})

with open("centros.txt", mode="w", encoding="utf-8") as f:
    for a in cuerpo.findAll("a", attrs={"href": pdfs}):
        href = a.attrs["href"]
        urlretrieve(href, tpf)
        call(pdftotext + [tpf])
        with open(ttx, mode="r", encoding="utf-8") as infile:
            f.write(infile.read())
