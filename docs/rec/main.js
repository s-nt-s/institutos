var centros_layer;
var transpo_layer;
var mymap;
var cursorMarker;
var mailLink = "mailto:?subject=Consulta%20en%20relación%20al%20concurso%20de%20traslados&";

var myweb = window.location.href;
myweb = myweb.substr(document.location.protocol.length+2)
if (myweb.endsWith("/")) myweb = myweb.substr(0, myweb.length-1);

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

function toUrl(url, txt, title) {
  if (!txt) txt = url.split(/:\/\//)[1]
  if (title==null) title = " title='"+url.split(/:\/\//)[1]+"'";
  return `<a href="${url}"${title}>${txt}</a>`
}

function getPopUp(c) {
  var body = [`Código: <b>${c.id}</b>`,`<a href="geo:${c.latlon}" title="Coordenadas: ${c.latlon}">${c.direccion}</a>`]
  var links=[]
  if (c.status_web == 200)
    links.push(toUrl(c.url, "Web"))
  if (c.mail) {
    mailto=mailLink+"to="+c.mail+"&body="+get_msg();
    links.push(`<a href='${mailto}' title="${c.mail}">Mail</a>`);
  }
  if (c.telefono) {
    var telefono = c.telefono.toString()
    if (telefono.length==9) {
      if (telefono.startsWith("91")) telefono = telefono.replace(/(..)(...)(..)(..)/, "$1 $2 $3 $4");
      else telefono = telefono.replace(/(...)(...)(...)/, "$1 $2 $3");
    }
    links.push(`<a href='tel:${c.telefono}' title="Teléfono: ${telefono}">${telefono}</a>`);
  }
  body.push(links.join(" - "))

  body =body.join("<br/>")
  url = toUrl(c.info, c.nombre)
  var html= `
  <h1>${url}</h1>
  <p>${body}</p>
  `;

  body = []
  if (c.dificultad)
    body.push("<b>Centro de especial dificultad</b>")
  if (c.nocturno && c.nocturno_en == null)
    body.push("<b>Nocturno</b>")
  var tags=[];
  if (c.excelencia)
      tags.push("<b>&#35;excelencia</b>")
  if (c.tecnico)
      tags.push("<b>&#35;tecnológico</b>")
  // if (c.bilingue)
  //     tags.push("bilingue")
  c.idiomas.forEach(function(i) {
    var t=idiomas[i];
    tags.push(`<b class="tag_${i} flag" title="Bilingüe o sección de ${t}">&#35;${i}</b>`)
  });
  if (tags.length) {
    body.push("\n"+tags.join(", "))
  }
  if (body.length) {
    body = body.join("<br/>")
    html = html + `<p>${body}</p>`
  }
  if (c.etapas!=null && c.etapas.length) {
    var li = []
    c.etapas.sort().forEach(function(e) {
      li.push("<li>"+e+"</li>")
    });
    li = li.join("\n")
    html = html + `<p>Etapas educativas:</p>\n<ul>\n${li}\n</ul>`
  }
  if (c.nocturno_en!=null && c.nocturno_en.length) {
    var li = []
    c.nocturno_en.sort().forEach(function(e) {
      li.push("<li>"+e+"</li>")
    });
    li = li.join("\n")
    html = html + `<p><b>Nocturno</b> en:</p>\n<ul>\n${li}\n</ul>`
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
    km = km.toString().replace(".", ",");
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
  geocentros["features"].forEach(function(f) {
    var _id = f.properties.id;
    if (_id==id) {
      f.properties.marca=marca;
    }
  })
  mymap.removeLayer(centros_layer)
  centros_layer = get_centros_layer();
  mymap.addLayer(centros_layer);
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
  var count;
  var c=f.properties;
  var id = c.id + ""
  if (c.marca==1) return true;
  //if ($("#siempre").val().split(/\s+/).indexOf(id)>-1) return true;
  //if ($("#nunca").val().split(/\s+/).indexOf(id)>-1) return false;
  if (!$("#t"+c.tipo).is(":checked")) return false;
  //if (c.bilingue && !$("#bilingue").is(":checked")) return false;
  for (count=0; count<c.idiomas.length; count++) {
    if (!$("#blg_"+c.idiomas[count]).is(":checked")) return false;
  };
  if (c.excelencia && !$("#excelencia").is(":checked")) return false;
  if (c.tecnico && !$("#tecnico").is(":checked")) return false;
  if (c.dificultad && !$("#dificultad").is(":checked")) return false;
  var km = parseInt($("#kms").val(), 10);
  if (!Number.isNaN(km) && c.min_distance>km) return false;
  
  if (c.nocturno_en && c.nocturno_en.length) {
    var ok=0;
    $("#nocturnos input:checked").each(function(){
      if (c.nocturno_en.indexOf(this.title)>-1) ok = ok + 1;
    })
    if (c.nocturno_en.length != ok) return false;
  } else if (c.nocturno) {
    if (!$("#ncTrue").is(":checked")) return false;
  }
  if (c.etapas==null || c.etapas.length==0) {
    if (!$("#etNull").is(":checked")) return false;
  }
  else if ($("#etapas input").not("#etNull").not(":checked").length) {
    var ok=0;
    var or_ok=false;
    $("#etapas input:checked").each(function(){
      if (c.etapas.indexOf(this.title)>-1) {
        or_ok = true;
        ok = ok + 1;
      }
    })
    //if (or_ok) return true;
    if (c.etapas.length != ok) return false;
  }
  return true;
}

function get_centros_layer() {
  return L.geoJSON(geocentros,{
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
      l.bindTooltip(f.properties.nombre);
    },
    filter: make_filter
  })
}


function get_transpo_layer() {
  return L.geoJSON(geotransporte,{
    style:function(f){
      return {
        "color":f.properties.color,
        weight: 3,
        opacity: .7,
        lineJoin: 'round'
      }
    },
    pointToLayer: function (f, latlng) {
      var p = f.properties;
      let options = {
        radius: 4,
        fillColor: "black",
        color: "black",
        weight: 1,
        opacity: 1,
        fillOpacity: 0.5
      }
      return L.circleMarker( latlng, options );
    },
    onEachFeature: function(f, l) {
      var p = f.properties;
      if (f.geometry.type == "LineString") {
        var tp = p.tipo.replace("_", " ");
        tp = tp.charAt(0).toUpperCase() + tp.slice(1)
        l.bindPopup("Linea "+p.linea+" de "+tp);
      } else if (f.geometry.type == "Point") {
        var i;
        txt=[]
        for (i=0;i<p.lineas.length; i++) {
          var ln=p.lineas[i];
          txt.push(ln[1]);
        }
        if (txt.length==1) txt="Linea "+txt[0];
        else txt = "Lineas "+txt.join(", ");
        body=`<h1>${p.nombre}</h1><p>${txt}</p>`;
        l.bindPopup(body);
      }
    },
    filter: function (f, layer) {
      var p = f.properties;
      if (f.geometry.type == "LineString") {
        var id = "#"+p.tipo+"_"+p.linea;
        return $(id).is(":checked");
      } else if (f.geometry.type == "Point") {
        if (!$("#estaciones").is(":checked")) return false;
        var i;
        for (i=0;i<p.lineas.length; i++) {
          var ln=p.lineas[i]
          var id = "#"+ln[0]+"_"+ln[1];
          if($(id).is(":checked")) return true;
        }
      }
      return false;
    }
  })
}

function setMark(e) {
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
  console.log(e.latlng.lat+","+e.latlng.lng)
  cursorMarker = L.circleMarker(e.latlng, options );
  cursorMarker.addTo(mymap);
  $(".active").trigger("active");
}

$(document).ready(function() {
$(".sidebar-pane").each(function(){
  observer.observe(this, {attributes: true});
});
mymap = L.map("map");
/*
L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token={accessToken}', {
    attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors, <a href="https://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, Imagery © <a href="https://www.mapbox.com/">Mapbox</a>',
    maxZoom: 18,
    id: 'mapbox.streets',
    accessToken: 'pk.eyJ1Ijoia2lkdHVuZXJvIiwiYSI6ImNqeTBjeG8zaTAwcWYzZG9oY2N1Z3VnazgifQ.HKixpk5HNX-svbNYxYSpsw'
}).addTo(mymap);
*/
/* https://www.ign.es/wmts/ign-base?request=GetCapabilities&service=WMTS */
var ign = new L.TileLayer.WMTS("https://www.ign.es/wmts/ign-base", {
  id: 'capa.base',
	layer: "IGNBaseTodo",
	tilematrixSet: "GoogleMapsCompatible",
	format: "image/png",
	attribution: "CC BY 4.0 <a href='http://www.scne.es/'>SCNE</a>, <a href='http://www.ign.es'>IGN</a>",
	maxZoom: 20,
	crossOrigin: true
}).addTo(mymap);
mymap.on('click', function(e){
  if (!e || !e.originalEvent || !e.originalEvent.ctrlKey) return;
  setMark.apply(this, arguments)
}).on('contextmenu',function(e){
  setMark.apply(this, arguments);
});
centros_layer = get_centros_layer();
centros_layer.addTo(mymap);
bounds = centros_layer.getBounds()
if (Object.keys(bounds).length) mymap.fitBounds(bounds);
else mymap.setView([40.4165000, -3.7025600], 12)
var sidebar = L.control.sidebar('sidebar').addTo(mymap);

$("#transporte input").bind("click keypress change", function() {
    if(transpo_layer) mymap.removeLayer(transpo_layer)
    transpo_layer=null;
    if($("#transporte fieldset input:checked").length==0) return;
    transpo_layer = get_transpo_layer();
    mymap.addLayer(transpo_layer);
}).change();

$("div.filter input").bind("click keypress change", function() {
    if(centros_layer) mymap.removeLayer(centros_layer)
    centros_layer=null;
    //if($("#settings fieldset input:checked").length==0 && $("#kms").val().length==0) return;
    centros_layer = get_centros_layer();
    mymap.addLayer(centros_layer);
    var estadistica=get_estadistica();
    $("#count").text(estadistica.seleccionados.length+estadistica.showen.length);
}).change();
$("#messages").bind("active", function(){
  if (!$(this).is(".active")) return;
  var mails=[]
  geocentros["features"].forEach(function(f) {
    var mail = f.properties.mail;
    if (mail && make_filter(f) && c.marca!=2) {
      mails.push(mail)
    }
  })
  var lnk = $("#maillink");
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
      lnk.attr("href",mailLink+"to="+mails[0]+"&body="+get_msg());
    } else{
      lnk.attr("href",mailLink+"bcc="+ mails.sort().join(";")+"&body="+get_msg());
    }
  }
})

function get_estadistica(mrk) {
  var seleccionados=[];
  var descartados=[];
  var hidden=[];
  var showen=[];
  if (mrk && mrk._latlng) mrk = mrk._latlng;
  if (mrk && !(mrk.lat && mrk.lng)) mrk = null;
  geocentros["features"].forEach(function(f) {
    c=f.properties;
    if (mrk) {
      var latlon = c.latlon.split(/,/)
      c.dis_to_mrk = get_distance(mrk.lat, mrk.lng, parseFloat(latlon[0]), parseFloat(latlon[1]));
    }
    if (!make_filter(f)) {
      hidden.push(c)
    } else {
      if (c.marca==1) seleccionados.push(c);
      else if (c.marca==2) descartados.push(c);
      else showen.push(c)
    }
  })
  if (mrk) {
    var fSort = function(a,b) { return a.dis_to_mrk - b.dis_to_mrk }
    seleccionados.sort(fSort);
    descartados.sort(fSort);
    hidden.sort(fSort);
    showen.sort(fSort);
  }
  return {
    "seleccionados":seleccionados,
    "descartados":descartados,
    "hidden": hidden,
    "showen": showen
  }
}

$("#lista").bind("active", function(){
  if (!$(this).is(".active")) return;
  var estadistica=get_estadistica();
  $("#count").text(estadistica.seleccionados.length+estadistica.showen.length);
  $("#cSel").html(list_centros(estadistica.seleccionados, "Aún no has seleccionado ningún centro"));
  $("#cShw").html(list_centros(estadistica.showen, "Tu filtro oculta todos los centros"));
  $("#cHdn").html(list_centros(estadistica.hidden, "Tu filtro muestra todos los centros"));
  $("#cDsc").html(list_centros(estadistica.descartados, "Aún no has descartados ningún centro"));
  $("#cSel,#cShw,#cHdn,#cDsc").each(function() {
    var t=$(this);
    var count=t.find("li").length;
    var h2=t.prev("h2");
    if (count==0) {
      h2.find("small").remove();
    }
    else {
      var small = h2.find("small");
      if (small.length) small.text("("+count+")")
      else h2.append(" <small>("+count+")</small>")
    }
  })
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

$("#download").bind("click", function(){
  var estadistica=get_estadistica(cursorMarker);
  var ahora = new Date();
  var date = ahora.getFullYear() + "." + ahora.getMonth().pad(2) + "." + ahora.getDate().pad(2);
  this.download = date+"_centros.txt"
  var txt='Fecha: '+date+"\n";
  if (cursorMarker) {
    txt=txt+`Punto de refrencia: ${cursorMarker._latlng.lat},${cursorMarker._latlng.lng}\n`
  }
  var filtros=$("#settings");
  var fltDis=filtros.find("#kms");
  var inputs=filtros.find("input").not(fltDis)
  if (inputs.length==inputs.filter(":checked").length && fltDis.val().length==0) {
    txt=txt+"Filtro: Ver todos\n";
  } else if (inputs.length==inputs.not(":checked").length) {
    txt=txt+"Filtro: Ocultar todos\n";
  } else {
    txt=txt+"Filtro => Ver todos menos:";
    inputs.not(":checked").closest("fieldset").each(function(){
      var t=$(this);
      txt=txt+"\n* "+t.find("legend").text().trim()+":";
      t.find("input").not(":checked").each(function(){
        txt=txt+"\n    * "+this.title;
      })
    })
    if (fltDis.val().length) {
      txt=txt+"\n* Centros a más de "+fltDis.val()+" metros de una estación";
    }
    txt = txt+"\n";
  }
  var cols=[
    ["Centros seleccionados por mi", estadistica.seleccionados],
    ["Centros seleccionados por el filtro", estadistica.showen],
    ["Centros descartados por el filtro", estadistica.hidden],
    ["Centros descartados por mi", estadistica.descartados]
  ];
  cols.forEach(function(item) {
    var col = item[1];
    if (col && col.length) {
      txt=txt+"\n"+item[0]+":\n";
      col.forEach(function(c) {
        txt=txt+`\n* ${c.id} ${c.nombre}`
        if (cursorMarker) {
          var dis;
          if (c.dis_to_mrk>1) {
            dis=(Math.round(c.dis_to_mrk*100)/100)+"km";
            dis=dis.replace(".", ",");
          }
          else {
            dis=Math.round(c.dis_to_mrk*1000)+"m";
          }
          txt = txt + ` (${dis})`
        }
      });
      txt = txt + "\n"
    }
  })
  txt = txt.replace(/<.*?>/g , "");
  txt = txt+"\n---\n"+myweb;
  txt = txt.trim()
  txt = txt.replace(/\n/g, "\r\n");
  this.href='data:text/plain;charset=utf-8,' + encodeURIComponent(txt);
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
    var title="";
    var d=0;
    if (cursorMarker) {
      var ll = cursorMarker._latlng
      var latlon = c.latlon.split(/,/)
      d = get_distance(ll.lat, ll.lng, parseFloat(latlon[0]), parseFloat(latlon[1]));
      if (d>1) {
        distance=Math.round(d)+"km";
        title=(Math.round(d*100)/100)+"km";
        title=title.replace(".", ",");
        title=" title='"+title+"'";
      }
      else if (d<=1) {
        distance=Math.round(d*1000)+"m";
      }
      distance = ` <small${title}>(${distance})</small>`
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
    var href;
    if (mails.length==1) {
      href = mailLink+"to="+mails[0]+"&body="+get_msg();
    } else{
      href = mailLink+"bcc="+ mails.sort().join(";")+"&body="+get_msg();
    }
    html = html + `
    <p><a href="${href}">Pincha aquí para mandar un email a todos los centros de esta lista que tienen correo electrónico</a></p>
    `
  }
  return html
}
