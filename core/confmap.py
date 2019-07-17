from bunch import Bunch

etapas_ban=(
    "Formación Profesional de grado medio",
    "Formación Profesional de grado superior",
    "Segundo Ciclo de Educación Infantil (LOE)",
    "Educación Primaria (LOE - LOMCE)",
    "Idiomas (LOE 1)",
    "Artísticas (LOE)",
    "Artísticas (LOGSE)",
    "Enseñanzas Iniciales Básicas para personas adultas (LOE)",
    "Programas Profesionales (LOE-LOMCE)",
    "Técnico Profesional",
    "Educación Especial Infantil (Adaptac. LOE)",
    "Educación Especial Primaria (Adaptac. LOE)"
)

def index(literal, arr):
    if literal in arr:
        return arr.index(literal)
    return None

def parse_etapas(etapas):
    iBachillerato = index("Bachillerato", etapas)

def parse_tipo(name):
    name = name.capitalize()
    for p in ("Centros públicos ", "Centro público "):
        if name.startswith(p):
            name = "Centro "+name[len(p):]
            return name
    return name

def parse_word(w, first=False):
    if first:
        return w.capitalize()
    l=w.lower()
    if l in ("i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xii", "xiii", "xiv", "xv", "xvi", "xvii", "xviii", "xix", "xx"):
        return l.upper()
    if len(l)<3 or l in ("del", "las", "los"):
        return l
    return w.capitalize()

def parse_nombre(name):
    words=name.split()
    for i, w in enumerate(words):
        words[i]=parse_word(w, first=(i==0))
    return " ".join(words)

def color_to_url(color, mod):
    if mod:
        color = color + "-"+mod
    return 'http://maps.google.com/mapfiles/ms/micons/'+color+'.png'

colors = Bunch(
    dificultad="red",
    nocturno="blue",
    default="green",
    especial="dot"
)
