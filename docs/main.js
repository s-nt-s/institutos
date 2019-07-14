var main_layer;
var mymap;

function toUrl(url, txt) {
  if (!txt) txt = url.split(/:\/\//)[1]
  return `<a href="${url}">${txt}</a>`
}

function getPopUp(c) {
  var body = [`Código: ${c.id}`,`Dirección: ${c.direccion}`]
  if (c.status_web == 200)
    body.push(toUrl(c.url))
  if (c.dificultad)
    body.push("<b>Centro de especial dificultad<b>")

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

  html = html.trim()
  return html
}

function getIcon(url) {
  return {icon: L.icon({
    iconUrl: url
  })}
}
function make_filter(f, layer) {
  c=f.properties;
  var id = c.id + ""
  if ($("#siempre").val().split(/\s+/).indexOf(id)>-1) return true;
  if ($("#nunca").val().split(/\s+/).indexOf(id)>-1) return false;
  if (!$("#t"+c.tipo).is(":checked")) return false;
  if (c.bilingue && !$("#bilingue").is(":checked")) return false;
  if (c.excelencia && !$("#excelencia").is(":checked")) return false;
  if (c.tecnico && !$("#tecnico").is(":checked")) return false;
  if (c.dificultad && !$("#dificultad").is(":checked")) return false;
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
      return L.marker(latlng, getIcon(f.properties.icon));
    },
    onEachFeature: function(f, l) {
      l.bindPopup(getPopUp(f.properties));
    },
    filter: make_filter
  })
}


$(document).ready(function() {

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
    var lnk = $("#maillink")
    var href = lnk.data("href");
    lnk=lnk[0];
    var pos = href.indexOf("&");
    href = href.substr(0,pos+1);
    var mails=[]
    geomap["features"].forEach(function(f) {
      var mail = f.properties.mail;
      if (mail && make_filter(f)) {
        mails.push(mail)
      }
    })
    var l = $("#lkMessages, #maillink");
    if (mails.length==0) {
      l.attr("disabled", "disabled");
      l.attr("title", "No hay ningún centro con mail seleccionado");
      lnk.href="#"
    } else {
      l.removeAttr("disabled");
      l.removeAttr("title");
      if (mails.length==1) {
        lnk.href=href+"to="+mails[0];
      } else{
        lnk.href=href+"bcc="+ mails.join(";");;
      }
    }
}).click();

});
