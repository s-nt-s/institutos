#!/usr/bin/python3
# -*- coding: utf-8 -*-

import tempfile
import requests
import bs4
import re
import shutil
from urllib.request import urlretrieve
from subprocess import call, check_output

pdfs = re.compile(r".*\bapplication%2Fpdf\b.*")
tmp = tempfile.mkdtemp() + "/"
tpf = tmp+"pdf.pdf"
ttx = tmp+"pdf.txt"

convocatoria = "http://www.bocm.es/boletin/CM_Orden_BOCM/2016/10/27/BOCM-20161027-11.PDF"
puntos = "http://www.madrid.org/cs/Satellite?blobcol=urldata&blobheader=application%2Fpdf&blobheadername1=Content-Disposition&blobheadervalue1=filename%3DParticipantes+sin+destino+por+especialidad_alfabetico-sin+DNI_red.pdf&blobkey=id&blobtable=MungoBlobs&blobwhere=1352931434938&ssbinary=true"
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

def pdf_txt(url, txt):
    urlretrieve(url, tpf)
    call(pdftotext + [tpf])
    shutil.copy(ttx,txt)

pdf_txt(convocatoria, "convocatoria.txt")
pdf_txt(puntos, "puntos.txt")
