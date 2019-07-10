# -*- coding: utf-8 -*-
import re

# pdftotext Participantes.pdf -table -nopgbrk

num = re.compile(r".*?(\d+).*")
sp = re.compile(r"\s+", re.MULTILINE | re.UNICODE)
spc = re.compile(r"\s*Especialidad:\s*(\d+-.*)\s*")
prs = re.compile(r"(.*)\bPuntos:\s(Total:\s.*)")
campos = ["Total", "Año Opos.", "Ptos. Opos.", "Origen", "Mod"]
dec = re.compile(r"^\d+,\d+$")


def get_data(linea):
    data = {}
    z = len(campos)
    for i in range(0, z, 1):
        cmp1 = campos[i]
        a = linea.index(cmp1 + ":") + len(cmp1) + 1
        if i < z - 1:
            cmp2 = campos[i + 1]
            b = linea.index(cmp2 + ":")
        else:
            b = len(linea)
        valor = linea[a:b].strip()
        if len(valor) == 0 and cmp1 in ["Total", "Ptos. Opos."]:
            valor = 0
        elif valor.isdigit():
            valor = int(valor)
        elif dec.match(valor):
            valor = float(valor.replace(",", "."))
        data[cmp1] = valor
    return data


datos = {}
especialidad = None

with open("puntos.txt", mode="r", encoding="utf-8") as f:
    for linea in f.readlines():
        linea = linea.strip()
        m = spc.match(linea)
        if m:
            especialidad = m.group(1).strip()
            datos[especialidad] = []
            continue
        if linea and especialidad is not None:
            m = prs.match(linea)
            if m:
                nombre = sp.sub(" ", m.group(1)).strip(
                ).replace(",", ", ").title()
                info = sp.sub(" ", m.group(2)).strip()
                data = get_data(info)
                data["score"] = data["Total"]
                if data["score"] == 0:
                    data["score"] = data["Ptos. Opos."]
                data["nombre"] = nombre
                datos[especialidad].append(data)

matematicas = sorted(datos["006-MATEMÁTICAS"],
                     key=lambda s: s["score"], reverse=True)
p = len(str(len(matematicas)))
s = len(str(int(matematicas[0]["score"]))) + 3
formato = "%" + str(p) + "d - %4d: %" + str(s) + ".2f %s"
for i in range(0, len(matematicas), 1):
    d = matematicas[i]
    print(formato % (i + 1, d["Año Opos."], d["score"], d["nombre"]))
