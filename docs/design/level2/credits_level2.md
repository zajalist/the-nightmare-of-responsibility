# Level 2 credits: data attribution

The research lane wrote this on 2026-11-10. These lines must appear in the game's credits and the project report.
Following the in-game text style, each one is plain text on its own line.

## Lines for the credits screen

```
Toronto city scan
Contains information licensed under the Open Government Licence – Canada.
LiDAR Point Clouds, CanElevation Series, Natural Resources Canada (Toronto and Region Conservation Authority, GTA 2023 acquisition)

Toronto building footprints
Contains information licensed under the Open Government Licence – Toronto.
3D Massing, City of Toronto

Dream worlds generated with Aholo SpatialGen by Manycore
```

Notes on the lines:
- **The two "Contains information..." sentences** are the default statements each licence requires. Quote them
  exactly, including the en dash.
- **The producer names** (NRCan, TRCA, City of Toronto) are courtesy credits. They aren't required, but they're
  expected.
- **The Aholo line** isn't a licence requirement. It's there for the hackathon's tool criterion. Lux3D credits stay
  wherever level 1's credits put them.

## Where each line comes from

| Data | Source and download | Licence (version) | What it requires |
|---|---|---|---|
| Lidar, tiles `E6290_N48330` and `E6290_N48340` (the Queen St W corridor) | CanElevation S3, e.g. `https://canelevation-lidar-point-clouds.s3.ca-central-1.amazonaws.com/pointclouds_nuagespoints/TRCA/GTA_2023/ON_TRCA2023_20230511_NAD83CSRS_UTMZ17_1km_E6290_N48340_CLASS.copc.laz`. Catalogue record: https://open.canada.ca/data/en/dataset/7069387e-9986-4297-9f55-0288e9676947, licence field `ca-ogl-lgo` | Open Government Licence – Canada 2.0, https://open.canada.ca/en/open-government-licence-canada | Attribution statement, plus a link to the licence where possible. Use is free "for any lawful purpose", including commercial use. **No implied endorsement or official status** |
| 3D Massing footprints, 2025 Shapefile | https://open.toronto.ca/dataset/3d-massing/ (`3DMassingShapefile_2025_WGS84.zip`, 81.4 MB) | Open Government Licence – Toronto 1.0, https://open.toronto.ca/open-data-licence/ | Attribution statement. Commercial use allowed. **City names, crests and logos are excluded from the licence**, and no City endorsement may be implied |

## Optional line

Expanded city pass (2026-11-10): anonymous COPC range reads from the same NRCan/TRCA GTA 2023 source for tiles `E6290_N48330`, `E6290_N48340`, `E6290_N48350`, `E6300_N48330`, `E6300_N48340`, and `E6300_N48350`. The matching 2025 Toronto 3D Massing archive is reused. The Canada and Toronto attribution lines above apply unchanged to the expanded monochrome splats, footprint colours, shadows, ground textures, and blurred edge extension. These are modified visual derivatives, not official mapping products.

Ontario's catalogue lists the same GTA 2023 capture under the Open Government Licence – Ontario. We take the NRCan
copy, so that line isn't required. If any file ever comes from Ontario GeoHub, add:
`Contains information licensed under the Open Government Licence – Ontario.`

## Do not

- Use the City of Toronto, Government of Canada or TRCA logos, crests or wordmarks anywhere in the game.
- Word any line in a way that implies endorsement, such as "in partnership with" or "official".
