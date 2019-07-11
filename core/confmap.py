from bunch import Bunch


def parse_tipo(name):
    name = name.capitalize()
    for p in ("Centros públicos ", "Centro público "):
        if name.startswith(p):
            name = "Centro "+name[len(p):]
            return name
    return name


def parse_nombre(name):
    name = name.title()
    name = " ".join(w if len(w) > 2 and w not in (
        "Del", "Los", "Las") else w.lower() for w in name.split())
    return name


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
