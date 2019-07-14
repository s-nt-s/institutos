#!/usr/bin/env python3

import textwrap

import simplekml

from core.confmap import color_to_url, colors, parse_nombre, parse_tipo
from core.dataset import Dataset
from core.map import Map
from core.common import create_script

from core.j2 import Jnj2

d = Dataset()

tipos = set()
for c in d.centros:
    tipos.add(c.tipo)


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
        c.icon = pnt.style.iconstyle.icon.href

mapa.save("data/mapa.kml")
create_script("docs/geojson.js", geomap=d.geojson, tipos=ok_tipos, nocturnos=sorted(nocturnos))


lgd = [colors.dificultad, colors.nocturno, colors.default]
lgd = lgd + [color_to_url(c, None) for c in lgd]
mail = [c.mail for c in d.centros if c.mail]

j2 = Jnj2("template/", "docs/")
j2.save(
    "index.html",
    tipos=ok_tipos,
    nocturnos=sorted(nocturnos),
    lgd=lgd,
    indice=d.indice,
    mails=";".join(mail)
)
