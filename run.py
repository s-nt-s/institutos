#!/usr/bin/env python3

import simplekml
from core.dataset import Dataset
from core.map import Map
import textwrap

d = Dataset()

tipos=set()
for c in d.centros:
    tipos.add(c.tipo)

def get_description(c):
    des='''
        [{0} {1}]({3})
        Dirección: {2}
    '''.format(c.id, c.dat, c.direccion, c.info)
    des = textwrap.dedent(des).strip()
    if c.url:
        des=des+"\nURL: [{0}]({1})".format(c.url.split("://")[-1], c.url)
    if c.dificultad:
        des=des+"\n**Centro de especial dificultad**"
    tags=[]
    if c.excelencia:
        tags.append("excelencia")
    if c.tecnico:
        tags.append("tecnico")
    if c.bilingue:
        tags.append("bilingue")
    if tags:
        des=des+"\n**&#35;" + "**, **&#35;".join(tags)+"**"
    if c.nocturno:
        des=des+"\nNocturno en:"
        for n in c.nocturno:
            des=des+"\n- "+n
    des = des.replace("\n", "  \n")
    return des

def color_to_url(color, mod):
    if mod:
        color = color + "-"+mod
    return 'http://maps.google.com/mapfiles/ms/micons/'+color+'.png'

mapa = Map("Colegios - Profesores", color="green",color_to_url=color_to_url)

for t in sorted(tipos):
    tp = d.tipos[t].capitalize()
    print(tp)
    mapa.addFolder(tp)
    for c in d.centros:
        if c.tipo == t and c.latlon:
            lat, lon = tuple(map(float, c.latlon.split(",")))
            color="green"
            mod=None
            if c.tecnico or c.excelencia or c.bilingue:
                mod="dot"
            if c.dificultad:
                color="red"
            elif c.nocturno:
                color="blue"
            description = get_description(c)
            name = c.nombre.title()
            name = " ".join(w if len(w)>2 else w.lower() for w in name.split())
            mapa.addPoint(name, lat, lon, description=description, color=color, mod=None)

mapa.save("data/mapa.kml")
