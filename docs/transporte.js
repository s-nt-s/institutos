var mymap = L.map("map");
L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token={accessToken}', {
    attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors, <a href="https://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, Imagery © <a href="https://www.mapbox.com/">Mapbox</a>',
    maxZoom: 18,
    id: 'mapbox.streets',
    accessToken: 'pk.eyJ1Ijoia2lkdHVuZXJvIiwiYSI6ImNqeTBjeG8zaTAwcWYzZG9oY2N1Z3VnazgifQ.HKixpk5HNX-svbNYxYSpsw'
}).addTo(mymap);


L.geoJSON(geojson_transporte, {
  style:function(f){
    return {
      "color":f.properties.color,
      weight: 3,
      opacity: .7,
      lineJoin: 'round'
    }
  },
  onEachFeature: function(f, l) {
    l.bindPopup(f.properties.linea+"<br/>"+f.properties.shape_id);
  },
  filter: function (f, layer) {
    c=f.properties;
    return true;
    return c.linea!="C3"
    return c.shape_id=="5__2____1__IT_1";
  }
}).addTo(mymap);

mymap.setView([40.4165000, -3.7025600], 12)
