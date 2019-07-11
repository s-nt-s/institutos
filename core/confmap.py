from bunch import Bunch

def color_to_url(color, mod):
    if mod:
        color = color + "-"+mod
    return 'http://maps.google.com/mapfiles/ms/micons/'+color+'.png'

colors=Bunch(
    dificultad="red",
    nocturno="blue",
    default="green",
    especial="dot"
)
