var main_layer;
var mymap;

var observer = new MutationObserver(function(mutations) {
  mutations.forEach(function(mutation) {
    if (mutation.attributeName === "class") {
      elem = $(mutation.target);
      var attributeValue = elem.prop(mutation.attributeName);
      if (attributeValue.indexOf("active")>=0) {
        elem.trigger("activate");
      }
    }
  });
});

function toUrl(url, txt) {
  if (!txt) txt = url.split(/:\/\//)[1]
  return `<a href="${url}">${txt}</a>`
}

function getPopUp(c) {
  var body = [`Código: ${c.id}`,`Dirección: ${c.direccion}`]
  if (c.status_web == 200)
    body.push(toUrl(c.url))
  if (c.dificultad)
    body.push("<b>Centro de especial dificultad</b>")

  body =body.join("<br/>")
  url = toUrl(c.info, c.nombre)
  var html= `
  <h1>${url}</h1>
  <p>${body}</p>
  `;

  body = []
  var tags=[];
  if (c.excelencia)
      tags.push("excelencia")
  if (c.tecnico)
      tags.push("tecnico")
  if (c.bilingue)
      tags.push("bilingue")
  if (tags.length)
      body.push("\n<b>&#35;" + tags.join("</b>, <b>&#35;")+"</b>")

  if (body.length) {
    body = body.join("<br/>")
    html = html + `<p>${body}</p>`
  }
  body = []
  if (c.nocturno!=null && c.nocturno.length) {
    var li = []
    c.nocturno.forEach(function(e) {
      li.push("<li>"+e+"</li>")
    });
    li = li.join("\n")
    html = html + `<p>Nocturno en:</p>\n<ul>\n${li}\n</ul>`
  }
  var chk1 = ""
  var chk2 = ""
  var chk3 = "checked='checked'"
  if (c.marca) {
    if (c.marca==1) {
      chk1 = chk3;
      chk3 = ""
    } else if (c.marca==2) {
      chk2 = chk3;
      chk3 = ""
    }
  }
  html = html + "<p>Estación más cercana a ";
  if (c.min_distance<1000) {
    html = html + Math.round(c.min_distance) + " metros</p>"
  } else {
    var km = Math.round(c.min_distance / 100)/10;
    html = html + km + " kms</p>"
  }
  html = html + `
    <p>
      <input value="1" onchange="marcar(this, ${c.id})" class="marcar" type="radio" id="sel${c.id}" ${chk1}/> <label for="sel${c.id}">Marcar como seleccionado</label><br/>
      <input value="2" onchange="marcar(this, ${c.id})" class="marcar" type="radio" id="des${c.id}" ${chk2}/> <label for="des${c.id}">Marcar como descartado</label><br/>
      <input value="" onchange="marcar(this, ${c.id})" class="marcar" type="radio" id="no${c.id}" ${chk3}/> <label for="no${c.id}">No marcar</label>
    </p>
  `
  html = html.trim()
  return html
}

function marcar(t, id) {
  if (!t.checked) {
    return;
  }
  var marca = t.value;
  if (marca.length) marca = Number(marca);
  else marca=null;
  geomap["features"].forEach(function(f) {
    var _id = f.properties.id;
    if (_id==id) {
      f.properties.marca=marca;
    }
  })
  mymap.removeLayer(main_layer)
  main_layer = get_layer();
  mymap.addLayer(main_layer);
  $("#lista").trigger("activate");
}

function getIcon(p) {
  var url = p.icon;
  var iconSize = [32, 32];
  if (p.marca==1) {
    if (p.color=="green") url = "http://maps.google.com/mapfiles/ms/micons/grn-pushpin.png"
    else url = "http://maps.google.com/mapfiles/ms/micons/"+p.color+"-pushpin.png"
  } else if (p.marca==2) {
    url = "http://maps.gstatic.com/mapfiles/ridefinder-images/mm_20_black.png"
  }
  return {icon: L.icon({
    iconUrl: url,
    iconSize:iconSize
  })}
}
function make_filter(f, layer) {
  c=f.properties;
  var id = c.id + ""
  if (c.marca==1) return true;
  //if ($("#siempre").val().split(/\s+/).indexOf(id)>-1) return true;
  //if ($("#nunca").val().split(/\s+/).indexOf(id)>-1) return false;
  if (!$("#t"+c.tipo).is(":checked")) return false;
  if (c.bilingue && !$("#bilingue").is(":checked")) return false;
  if (c.excelencia && !$("#excelencia").is(":checked")) return false;
  if (c.tecnico && !$("#tecnico").is(":checked")) return false;
  if (c.dificultad && !$("#dificultad").is(":checked")) return false;
  var km = parseInt($("#kms").val(), 10);
  if (!Number.isNaN(km) && c.min_distance>km) return false;
  if (!c.nocturno || !c.nocturno.length) return true;
  var ok=0;
  $("#nocturnos input:checked").each(function(){
    var lb = $("label[for='"+this.id+"']");
    var txt = lb.text().replace(/^\s*|\s*$/g, "");
    if (c.nocturno.indexOf(txt)>-1) ok = ok + 1;
  })
  return c.nocturno.length == ok;
}

function get_layer() {
  return L.geoJSON(geomap,{
    pointToLayer: function (f, latlng) {
      var p = f.properties;
      if (p.marca==2) {
        let options = {
          radius: 5,
          fillColor: p.color,
          color: "black",
          weight: 1,
          opacity: 1,
          fillOpacity: 0.8
        }
        return L.circleMarker( latlng, options );
      }
      return L.marker(latlng, getIcon(p));
    },
    onEachFeature: function(f, l) {
      l.bindPopup(getPopUp(f.properties));
    },
    filter: make_filter
  })
}


$(document).ready(function() {
$(".sidebar-pane").each(function(){
  observer.observe(this, {attributes: true});
});
mymap = L.map("map");
L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token={accessToken}', {
    attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors, <a href="https://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, Imagery © <a href="https://www.mapbox.com/">Mapbox</a>',
    maxZoom: 18,
    id: 'mapbox.streets',
    accessToken: 'pk.eyJ1Ijoia2lkdHVuZXJvIiwiYSI6ImNqeTBjeG8zaTAwcWYzZG9oY2N1Z3VnazgifQ.HKixpk5HNX-svbNYxYSpsw'
}).addTo(mymap);
main_layer = get_layer();
main_layer.addTo(mymap);
bounds = main_layer.getBounds()
if (Object.keys(bounds).length) mymap.fitBounds(bounds);
else mymap.setView([40.4165000, -3.7025600], 12)
var sidebar = L.control.sidebar('sidebar').addTo(mymap);

$("div.filter input").bind("click keypress change", function() {
    mymap.removeLayer(main_layer)
    main_layer = get_layer();
    mymap.addLayer(main_layer);
}).change();
$("#messages").bind("activate", function(){
  var lnk = $("#maillink")
  var href = lnk.data("href");
  var mails=[]
  geomap["features"].forEach(function(f) {
    var mail = f.properties.mail;
    if (mail && make_filter(f)) {
      mails.push(mail)
    }
  })
  if (mails.length==0) {
    lnk.attr("disabled", "disabled");
    lnk.attr("title", "No hay ningún centro con mail seleccionado");
    lnk.attr("href", "#")
  } else {
    lnk.removeAttr("disabled");
    lnk.removeAttr("title");
    if (mails.length==1) {
      lnk.attr("href",href+"to="+mails[0]);
    } else{
      lnk.attr("href",href+"bcc="+ mails.join(";"));
    }
  }
})

$("#lista").bind("activate", function(){
  var seleccionados=[];
  var descartados=[];
  var hidden=[];
  var showen=[];
  geomap["features"].forEach(function(f) {
    c=f.properties;
    if (!make_filter(f)) {
      hidden.push(c)
    } else {
      if (c.marca==1) seleccionados.push(c);
      else if (c.marca==2) descartados.push(c);
      else showen.push(c)
    }
  })
  $("#cSel").html(list_centros(seleccionados, "Aún no has seleccionado ningún centro"));
  $("#cShw").html(list_centros(showen, "Tu filtro oculta todos los centros"));
  $("#cHdn").html(list_centros(hidden, "Tu filtro muestra todos los centros"));
  $("#cDsc").html(list_centros(descartados, "Aún no has descartados ningún centro"));
});

});

function list_centros(centros, none) {
  if (centros.length==0) {return "<p>"+none+"</p>"}
  var mails=[]
  var html="<ul class='listCentros'>"
  centros.forEach(function(c) {
    if (c.mail) mails.push(c.mail);
    html = html + `
      <li onclick="mymap.flyTo([${c.latlon}], 15);">${c.id} ${c.nombre}</li>
    `;
  });
  html = html +"</ul>"
  if (mails.length) {
    var lnk = $("#maillink")
    var href = lnk.data("href");
    if (mails.length==1) {
      href = href+"to="+mails[0];
    } else{
      href = href+"bcc="+ mails.join(";");
    }
    html = html + `
    <p><a href="${href}">Pincha aquí para mandar un email a todos los centros de esta lista que tienen correo electrónico</a></p>
    `
  }
  return html
}
