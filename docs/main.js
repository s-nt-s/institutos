var main_layer;
var mymap;
var cursorMarker;

function get_msg() {
  var hora = (new Date()).getHours();
  var msg='Buenos días';
  if (hora>12) msg='Buenas tardes';
  if (hora>20) msg='Buenas noches';
  msg = msg + "\n" +`
Soy ... y quería preguntarles ...

Muchas gracias.`
  msg = msg.replace(/\n/g, "%0D%0A");
  msg = msg.replace(/\s+/g, "%20");
  return msg
}

function get_distance(lat1,lon1,lat2,lon2) {
  var R = 6371; // km (change this constant to get miles)
  var dLat = (lat2-lat1) * Math.PI / 180;
  var dLon = (lon2-lon1) * Math.PI / 180;
  var a = Math.sin(dLat/2) * Math.sin(dLat/2) +
    Math.cos(lat1 * Math.PI / 180 ) * Math.cos(lat2 * Math.PI / 180 ) *
    Math.sin(dLon/2) * Math.sin(dLon/2);
  var c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  var d = R * c;
  return d;
}

var observer = new MutationObserver(function(mutations) {
  mutations.forEach(function(mutation) {
    if (mutation.attributeName === "class") {
      elem = $(mutation.target);
      var attributeValue = elem.prop(mutation.attributeName);
      if (attributeValue.indexOf("active")>=0) {
        elem.trigger("active");
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
  $(".active").trigger("active");
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
mymap.on('click', function(e){
  if (!e || !e.originalEvent || !e.originalEvent.ctrlKey) return;
  if (cursorMarker) mymap.removeLayer(cursorMarker);
  let options = {
    radius: 10,
    fillColor: "yellow",
    color: "black",
    weight: 1,
    opacity: 1,
    fillOpacity: 0.8,
    clickable: false,
    keyboard: false
  }
  cursorMarker = L.circleMarker(e.latlng, options );
  cursorMarker.addTo(mymap);
  $(".active").trigger("active");
});
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
$("#messages").bind("active", function(){
  if (!$(this).is(".active")) return;
  var lnk = $("#maillink")
  var href = lnk.data("href");
  var mails=[]
  geomap["features"].forEach(function(f) {
    var mail = f.properties.mail;
    if (mail && make_filter(f) && c.marca!=2) {
      mails.push(mail)
    }
  })
  if (mails.length==0) {
    lnk.attr("disabled", "disabled");
    lnk.attr("title", "No se visualiza ningún centro con correo electrónico");
    lnk.attr("href", "#")
    lnk.attr("onclick","return false;")
  } else {
    lnk.removeAttr("disabled");
    lnk.removeAttr("title");
    lnk.removeAttr("onclick");
    if (mails.length==1) {
      lnk.attr("href",href+"to="+mails[0]+"&body="+get_msg());
    } else{
      lnk.attr("href",href+"bcc="+ mails.join(";")+"&body="+get_msg());
    }
  }
})

$("#lista").bind("active", function(){
  if (!$(this).is(".active")) return;
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

$("#casa").bind("change", function() {
  var latlon = this.value.split(/,/);
  if (latlon.length!=2) return;
  var lat = parseFloat(latlon[0], 10);
  var lon = parseFloat(latlon[1], 10);
  if (Number.isNaN(lat) || Number.isNaN(lon)) return;

  var marker = L.marker([lat, lon],
    {icon: L.icon({iconUrl: "http://maps.google.com/mapfiles/ms/micons/homegardenbusiness.png"})}
  ).addTo(mymap);
})

});

function list_centros(centros, none) {
  if (centros.length==0) {return "<p>"+none+"</p>"}
  var mails=[]
  var html="<ul class='listCentros'>"
  var lis=[];
  centros.forEach(function(c) {
    if (c.mail) mails.push(c.mail);
    var distance="";
    var d=0;
    if (cursorMarker) {
      var ll = cursorMarker._latlng
      var latlon = c.latlon.split(/,/)
      d = get_distance(ll.lat, ll.lng, parseFloat(latlon[0]), parseFloat(latlon[1]));
      if (d>1) distance=Math.round(d)+"km";
      else if (d<=1) distance=Math.round(d*1000)+"m";
      distance = " <small>("+distance+")</small>"
    }
    lis.push(`
      <li data-order="${d}"><img src="${c.icon}" onclick="mymap.flyTo([${c.latlon}], 15);"/><span>${c.id} ${c.nombre}${distance}</span></li>
    `);
  });
  if (cursorMarker && lis.length>1) {
    lis = lis.sort(function(a, b) {
      var d1 = parseFloat(a.split(/"/)[1])
      var d2 = parseFloat(b.split(/"/)[1])
      var d = d1 - d2;
      if (d!=0) return d;
      return a.localeCompare(b);
    })
  }
  html = html + lis.join("")
  html = html +"</ul>"
  if (mails.length) {
    var lnk = $("#maillink")
    var href = lnk.data("href");
    if (mails.length==1) {
      href = href+"to="+mails[0]+"&body="+get_msg();
    } else{
      href = href+"bcc="+ mails.join(";")+"&body="+get_msg();
    }
    html = html + `
    <p><a href="${href}">Pincha aquí para mandar un email a todos los centros de esta lista que tienen correo electrónico</a></p>
    `
  }
  return html
}
