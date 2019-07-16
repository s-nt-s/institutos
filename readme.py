#!/usr/bin/env python3
import textwrap

from core.confmap import color_to_url, colors, parse_nombre, parse_tipo, etapas_ban
from core.dataset import Dataset
from core.parsemd import parsemd

d = Dataset()


def _readme(key):
    i = d.indice
    if key == "datos":
        transporte=''
        for dt in i.transporte.values():
            transporte = transporte + "\n                * La red de [{0}]({1})".format(dt.txt, dt.doc)
        return '''
            * [La última convocatoría]({0})
            * [El anexo 29]({1})
            * [El buscador de centros]({2})
            * Y para determinar la distancia a la estación de transporte más cercana,
            se han usado los datos de: {3}
        '''.format(i.convocatoria, i.anexo29, i.centros, transporte)
    if key == "buscador":
        return i.centros
    if key == "tipos":
        tipos = set((c.tipo for c in d.centros))
        s = ""
        for t in sorted(tipos):
            s = s + "\n* {0} {1}".format(t, parse_tipo(d.tipos[t]))
        return s.strip()
    if key == "excepcion":
        flag = False
        s = "A excepción de los siguientes que han tenido que ser descartados por no tener cooredandas geográficas:\n"
        for c in d.centros:
            if not c.latlon:
                flag = True
                s = s+"\n* [{0} {1}]({2})".format(c.id,
                                                  parse_nombre(c.nombre), c.info)
        return s if flag else ""
    if key == "iconos":
        lgd = [colors.dificultad, colors.nocturno, colors.default]
        lgd = lgd + [color_to_url(c, None) for c in lgd]
        return '''
            * ![{0}]({3}) Centro de especial dificultad
            * ![{1}]({4}) Centro con turnos nocturnos
            * ![{2}]({5}) Color por defecto
            * Y las mismas chinchetas pero con un punto negro en el centro
            cuando además se da alguna característica especial como
            bilingüismo, excelencia o innovación tecnológica
        '''.format(*lgd)
    if key == "enlaces_mail":
        mail = [c.mail for c in d.centros if c.mail]
        return "mailto:?bcc="+";".join(mail)+"&subject=Consulta%20en%20relacción%20al%20concurso%20de%20traslados"
    if key == "etapas_ban":
        s=""
        for e in etapas_ban:
            s=s +"\n* "+e
        return s.strip()

def readme(mtch):
    key = mtch.group(1)
    s = _readme(key)
    return textwrap.dedent(s).strip()


parsemd("template/README.md", "README.md", readme)
