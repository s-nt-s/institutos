#!/usr/bin/env python3

import textwrap

import simplekml

from core.confmap import color_to_url, colors, parse_nombre, parse_tipo, etapas_ban
from core.dataset import Dataset
from core.map import Map
from core.common import create_script

from core.j2 import Jnj2

d = Dataset()
d.unzip()

tipos = set()
latlon={}
etapas=set()
for c in d.centros:
    tipos.add(c.tipo)
    if c.latlon:
        col = latlon.get(c.latlon,[])
        col.append(c)
        latlon[c.latlon]=col
    if c.etapas:
        etapas = etapas.union(set(c.etapas))

print("Etapas educativas:")
for e in sorted(etapas):
    print(" ", e)

latlon = [(ltln, col) for ltln, col in latlon.items() if len(col)>1]
if len(latlon)>0:
    print("Centros con misma coordenadas:")
    for ltln, col in sorted(latlon):
        print(ltln)
        if len(col)>1:
            for c in col:
                print(" ",c.nombre)
                print(" ",c.direccion)
                print(" ",c.info)

def get_description(c):
    des = '''
        {0} {1}
        Dirección: {2}
        FICHA: {3}
    '''.format(c.id, c.dat, c.direccion, c.info)
    des = textwrap.dedent(des).strip()
    if c.status_web == 200:
        des = des+"\nURL: {0}".format(c.url.split("://")[-1])
    if c.dificultad:
        des = des+"\n**Centro de especial dificultad**"
    tags = []
    if c.excelencia:
        tags.append("excelencia")
    if c.tecnico:
        tags.append("tecnico")
    if c.bilingue:
        tags.append("bilingue")
    if tags:
        des = des+"\n**&#35;" + "**, **&#35;".join(tags)+"**"
    if c.nocturno:
        des = des+"\nNocturno en:"
        for n in c.nocturno:
            des = des+"\n- "+n
    des = des.replace("\n", "  \n")
    return des


mapa = Map("Colegios - Profesores", color="green", color_to_url=color_to_url)

ok_tipos = {}
ok_etapas = set()
nocturnos=set()
for t in sorted(tipos):
    centros = [c for c in d.centros if c.tipo == t and c.latlon]
    if not centros:
        continue
    tp = parse_tipo(d.tipos[t])
    ok_tipos[t]=tp
    mapa.addFolder(tp)
    for c in centros:
        lat, lon = tuple(map(float, c.latlon.split(",")))
        color = colors.default
        mod = None
        for et in (c.etapas or []):
            ok_etapas.add(et)
        if c.tecnico or c.excelencia or c.bilingue:
            mod = colors.especial
        if c.dificultad:
            color = colors.dificultad
        elif c.nocturno:
            for n in c.nocturno:
                nocturnos.add(n)
            color = colors.nocturno
        description = get_description(c)
        c.nombre = parse_nombre(c.nombre)
        pnt = mapa.addPoint(c.nombre, lat, lon, description=description,
                      color=color, mod=mod)
        c.color=color
        c.icon = pnt.style.iconstyle.icon.href

mapa.save("data/mapa.kml")
create_script("docs/geojson.js", geomap=d.geojson, tipos=ok_tipos, nocturnos=sorted(nocturnos))
create_script("docs/geojson_transporte.js", geojson_transporte=d.geojson_transporte)

lgd = [colors.dificultad, colors.nocturno, colors.default]
lgd = lgd + [color_to_url(c, None) for c in lgd]
mail = [c.mail for c in d.centros if c.mail]

j2 = Jnj2("template/", "docs/")
j2.save(
    "index.html",
    tipos=ok_tipos,
    etapas=sorted(ok_etapas),
    nocturnos=sorted(nocturnos),
    lgd=lgd,
    indice=d.indice,
    mails=";".join(mail),
    count=len(d.centros)
)
