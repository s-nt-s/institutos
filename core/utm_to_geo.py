import math
import sys

import pyproj

ELIPSOIDE = "WGS84"


def get_epsg(datum, huso):
    if huso is None:
        return None
    if datum == "ED50":
        if huso >= 28 and huso <= 38:
            return 23000+huso
        return None
    if datum == "ETRS89":
        if huso >= 28 and huso <= 38:
            return 25800 + huso
        if huso == 27:
            return 4082  # REGCAN95 27
        return None
    if datum == "WGS84":
        if huso == 27:
            return 32627
        if huso == 28:
            return 32628
        if huso == 29:
            return 32629
        if huso == 30:
            return 32630
        if huso == 31:
            return 32631
        return None
    if datum == "REGCAN95":
        if huso == 27:
            return 4082
        if huso == 28:
            return 4083
        return None
    return None


def utm_to_geo(HUSO, UTM_X, UTM_Y, DATUM):
    if HUSO is None or DATUM is None or UTM_X is None or UTM_Y is None:
        return (None, None)
    epsg = get_epsg(DATUM, HUSO)
    if epsg is None:
        return (None, None)
    transformer = pyproj.Transformer.from_crs('epsg:' + str(epsg), 'epsg:4326')
    lat, lon = transformer.transform(UTM_X, UTM_Y)
    return lat, lon
    srcProj = pyproj.Proj(proj="utm", zone=HUSO, ellps=DATUM, units="m")
    dstProj = pyproj.Proj(proj='longlat', ellps='WGS84', datum='WGS84')
    long, lat = pyproj.transform(srcProj, dstProj, UTM_X, UTM_Y)
    if math.isnan(long) or math.isnan(lat) or math.isinf(long) or math.isinf(lat):
        return (None, None)
    return long, lat


if __name__ == "__main__":
    argv = [int(a) if a.isdigit() else a for a in sys.argv[1:]]
    lat, lon = utm_to_geo(30, *argv[1:])
    print(*argv)
    print("=")
    print(lat, lon)
    print("https://www.google.com/maps?q=%s,%s" % (lon, lat))
