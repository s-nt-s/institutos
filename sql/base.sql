select InitSpatialMetadata(1);
create table LINEA (
  tipo TEXT,
  nombre TEXT,
  shape_id TEXT,
  trip_id TEXT,
  route_id TEXT,
  orden INTEGER
);

SELECT AddGeometryColumn('LINEA', 'point', 4326, 'POINT', 2);
SELECT CreateSpatialIndex('LINEA', 'point');
