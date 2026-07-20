# Baltic Offline Basemap Attribution

The `baltic-land.geojson` asset is derived from Natural Earth 1:50m land data,
clipped to 9–31°E and 53–66°N and simplified for the AegisAIS offline festival
demonstration.

Natural Earth data is in the public domain. The project attribution is:

> Made with Natural Earth. Free vector and raster map data @ naturalearthdata.com.

Source repository:
https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_50m_land.geojson

Downloaded and transformed on 2026-07-20. The geometry must remain a local
build asset; the offline application does not fetch Natural Earth at runtime.
