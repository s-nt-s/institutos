# Objetivo

El objetivo es crear un mapa para ayudar a elegir destino
a los funcionarios de carrera o interinos del cuerpo 0590,
profesores de enseñanza secundaria, en la Comunidad de Madrid.

# Fuente de datos

Los datos que se han usado han sido:

* La última [convocatoria]({{indice.convocatoria}}) y [asignación de plazas]({{indice.asignacion}})
* [El anexo 29]({{indice.anexo29}})
* [El buscador de centros]({{indice.centros}})
* [El portal de datos abiertos de CRTM]({{indice.transporte.opendata}})

# Centros mostrados en el mapa

De todos los centros que devuelve [el buscador]({{indice.centros}}) solo se muestran
aquellos que son de alguno de los siguientes tipos:

{% for key, text in tipos|sort %}
* {{key}} {{text}}
{% endfor %}

y que (en caso de que este la información disponible) ofrezcan al menos alguna de estas etapas educativas:

{% for etapa in etapas %}
* {{etapa}}
{% endfor %}

{% if notlatlon %}
A excepción de los siguientes que han tenido que ser descartados por no tener coordenadas geográficas:

{% for id, nombre, info in notlatlon %}
* [{{id}} {{nombre}}]({{info}})
{% endfor %}
{% endif %}

# Iconos

Se han usado los siguientes iconos para dar información extra:

* ![{{lgd[0]}}]({{lgd[3]}}) Centro de especial dificultad
* ![{{lgd[1]}}]({{lgd[4]}}) Centro con turnos nocturnos
* ![{{lgd[2]}}]({{lgd[5]}}) Color por defecto
* Y las mismas chinchetas pero con un punto negro en el centro
cuando además se da alguna característica especial como
bilingüismo, excelencia o innovación tecnológica

# Resultado

El mapa se puede ver aquí: [institutos.ml](https://institutos.ml).

# Contactar con los centros

Si quieres lanzar una consulta al máximo número de centros posibles de una
sola vez puedes usar [este enlace]({{mails}}).
