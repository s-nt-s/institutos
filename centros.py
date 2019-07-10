# -*- coding: utf-8 -*-
import re
import textwrap

import bs4
import requests
import simplekml
import utm

# pdftotext ANEXO.pdf -table -nopgbrk

centro = re.compile(r"\b(28\d\d\d\d\d\d)\b")
asignatura = re.compile(r"\b(\d\d\d\d\d\d\d)\b")
mates = re.compile(r"\b(MATEMATICAS)\b")


datos = {}
tipos_des = {}
centro1 = None
centro2 = None


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

folders = {}

kml = simplekml.Kml()
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
        folder.name = t + " ("+tipos_des[t]+")"
        folder.description = tipos_des[t]
    folders[t] = folder

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
    ntn = data.get("NOCTURNO", [])
    if len(ntn) > 0:
        pnt.style = style_nocturno
        pnt.description = pnt.description + "<br/>Nocturno en:"
        for n in ntn:
            pnt.description = pnt.description + "<br/>"+n

kml.save("centros.kml")
