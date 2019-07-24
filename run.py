#!/usr/bin/env python3


from core.common import create_script
from core.confmap import (color_to_url, colors, etapas_ban, parse_nombre,
                          parse_tipo)
from core.dataset import Dataset
from core.j2 import Jnj2, post_parse
from core.map import Map
from core.parsemd import parsemd
from core.readme import readme
import bs4

d = Dataset()
d.unzip()

latlon = {}
etapas = set()
ok_tipos = {}
ok_etapas = set()
nocturnos = set()
notlatlon = []
mails = []
for c in d.centros:
    ok_tipos[c.tipo]=parse_tipo(d.tipos[c.tipo])
    if c.etapas:
        etapas = etapas.union(set(c.etapas))
    if c.mail:
        mails.append(c.mail)
    if c.latlon:
        col = latlon.get(c.latlon, [])
        col.append(c)
        latlon[c.latlon] = col
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
        c.nombre = parse_nombre(c.nombre)
        c.color = color
        c.icon = color_to_url(color, mod)
    else:
        notlatlon.append((c.id, parse_nombre(c.nombre), c.info))

print("Etapas educativas:")
for e in sorted(etapas):
    print(" ", e)

latlon = [(ltln, col) for ltln, col in latlon.items() if len(col) > 1]
if len(latlon) > 0:
    print("Centros con misma coordenadas:")
    for ltln, col in sorted(latlon):
        print(ltln)
        if len(col) > 1:
            for c in col:
                print(" ", c.nombre)
                print(" ", c.direccion)
                print(" ", c.info)

def create_sup(soup, n, title=None):
    sup = soup.new_tag("sup")
    a = soup.new_tag("a")
    a.string=str(n)
    a.attrs["href"]="#nota"+str(n)
    a.attrs["target"]="_self"
    if title:
        if title.endswith("."):
            title=title[:-1]
        title = bs4.BeautifulSoup(title,'html.parser').get_text()
        sup.attrs["title"]=title
    sup.append(a)
    return sup

def get_checks(soup, pre, *args):
    for t in args:
        id = pre+t
        inp = soup.find("input", id=id)
        if inp:
            yield inp, soup.find("label", attrs={"for":id})

def create_notas(html, **kargv):
    notas={}
    soup = bs4.BeautifulSoup(html, 'lxml')
    num=len(notas)+1
    for inp, lab in get_checks(soup, "t", "036"):
        notas[num]="Este tipo de centro no sale en los concursos, solo es accesible via comisión de servicios."
        del inp.attrs["checked"]
        lab.append(create_sup(soup, num, title=notas[num]))
    num=len(notas)+1
    for inp, lab in get_checks(soup, "t", "204", "205", "206"):
        notas[num]="Parece que este tipo de centro solo es para la especialidad 018. Si no es así avisame con un <a href='https://github.com/s-nt-s/institutos-map/issues'>issue</a>."
        del inp.attrs["checked"]
        lab.append(create_sup(soup, num, title=notas[num]))
    if notas:
        nt = bs4.BeautifulSoup('''
        <fieldset>
            <legend>Notas</legend>
            <ol>
            </ol>
        </fieldset>
        ''', 'html.parser')
        ul = nt.find("ol")
        for num, txt in sorted(notas.items()):
            li = bs4.BeautifulSoup('''
                <li id="nota{0}">{1}</li>
            '''.format(num, txt), 'html.parser')
            ul.append(li)
        div = soup.select("#settings div.content")[0]
        div.append(nt)
    return str(soup)

create_script("docs/geocentros.js", geocentros=d.geocentros)
create_script("docs/geotransporte.js", geotransporte=d.geotransporte)

lgd = [colors.dificultad, colors.nocturno, colors.default]
lgd = lgd + [color_to_url(c, None) for c in lgd]

j2 = Jnj2("template/", "docs/", post=post_parse)
j2.save(
    "index.html",
    tipos=sorted(ok_tipos.items(), key=lambda x: (x[1], x[0])),
    etapas=sorted(ok_etapas),
    nocturnos=sorted(nocturnos),
    lgd=lgd,
    indice=d.indice,
    mails=";".join(sorted(mails)),
    count=len(d.centros),
    transporte=d.transporte,
    notlatlon=notlatlon,
    sin_etapas=len([c for c in d.centros if not c.etapas]) > 0,
    parse=create_notas
)

parsemd("template/README.md", "README.md", readme)
