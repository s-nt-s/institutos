# -*- coding: utf-8 -*-
import simplekml

kml=simplekml.Kml()
kml.document.name = "Pruebas"

style_dificultad = simplekml.Style()
style_dificultad.iconstyle.color = simplekml.Color.red
style_dificultad.iconstyle.icon.href = 'http://maps.google.com/mapfiles/ms/micons/red.png'

kml.document.style = style_dificultad

style_nocturno = simplekml.Style()
style_nocturno.iconstyle.color = simplekml.Color.grey
style_nocturno.iconstyle.icon.href = 'http://maps.google.com/mapfiles/ms/micons/grey.png'

kml.document.style = style_nocturno

for i in range(0,2):
    folder = kml.newfolder(name="Fonder "+str(i))
    d = i * 10
    for c in range(0,3):
        pnt = folder.newpoint(name="Point "+str(c), coords=[(c + d , c + d)])
        if c % 2 == 1:
            pnt.style = style_dificultad
        else:
            pnt.style = style_nocturno
            

kml.save("prueba.kml")
