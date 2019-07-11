#!/usr/bin/env python3

import textwrap

import simplekml

from core.confmap import color_to_url, colors, parse_nombre, parse_tipo
from core.dataset import Dataset
from core.map import Map

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
    if c.url:
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

for t in sorted(tipos):
    tp = parse_tipo(d.tipos[t])
    mapa.addFolder(tp)
    for c in d.centros:
        if c.tipo == t and c.latlon:
            lat, lon = tuple(map(float, c.latlon.split(",")))
            color = colors.default
            mod = None
            if c.tecnico or c.excelencia or c.bilingue:
                mod = colors.especial
            if c.dificultad:
                color = colors.dificultad
            elif c.nocturno:
                color = colors.nocturno
            description = get_description(c)
            name = parse_nombre(c.nombre)
            mapa.addPoint(name, lat, lon, description=description,
                          color=color, mod=mod)

mapa.save("data/mapa.kml")
