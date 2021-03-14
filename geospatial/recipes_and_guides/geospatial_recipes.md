# Geospatial Recipes

This is a list of recipes for working with geospatial data using the GDAL command line tools.

## Table of Contents

- [Clip shapefile to the extent of a raster](#clip-shapefile-to-the-extent-of-a-raster)
- [Create polygon of the extent of a raster](#create-polygon-of-the-extent-of-a-raster)
- [Convert shapefile to geojson](#convert-shapefile-to-geojson)
- [Reproject a raster](#reproject-a-raster)
- [Convert a raster into an XYZ basemap](#convert-a-raster-into-an-xyz-basemap)
- [Crop a raster based on a shapefile](#crop-a-raster-based-on-a-shapefile)
- [Merge several bands into a single raster](#merge-several-bands-into-a-single-raster)
- [Extract a subset of bands from a raster](#extract-a-subset-of-bands-from-a-raster)
- [Max (lossless) compression of a raster](#max-lossless-compression-of-a-raster)
- [Merge many individual rasters into a single file](#merge-many-individual-rasters-into-a-single-file)
- [Make a thumbnail from a raster](#make-a-thumbnail-from-a-raster)
- [Merge aligned multi-channel rasters](#merge-aligned-multi-channel-rasters)
- [Reproject a shapefile](#reproject-a-shapefile)
- [Quantize float32/float64 raster to byte](#quantize-float32-float64-raster-to-byte)
- [Reproject and crop a large raster to the spatial extent and spatial resolution of a smaller raster](#reproject-and-crop-a-large-raster-to-the-spatial-extent-and-spatial-resolution-of-a-smaller-raster)
- [Rasterize shapefile to the extent of a raster](#rasterize-shapefile-to-the-exent-of-a-raster)
- [Convert GeoTIFF to COG](#convert-geotiff-to-cog)

## Quick links to the various GDAL command line tool's documentation 

- [gdalinfo](https://gdal.org/programs/gdalinfo.html) - Displays summary information about raster data files.
- [gdalwarp](https://gdal.org/programs/gdalwarp.html) - Reprojects and warps raster data files.
- [gdal_translate](https://gdal.org/programs/gdal_translate.html) - Converts raster data between different raster data formats.
- [gdaltindex](https://gdal.org/programs/gdaltindex.html) - Builds a shapefile with a record for each input raster file, an attribute containing the filename, and a polygon geometry outlining the raster.  
- [gdalbuildvrt](https://gdal.org/programs/gdalbuildvrt.html) - Constructs a virtual dataset (VRT) from a set of input raster data files. GDAL based tools (like the `rasterio` library in Python) will be able to open the VRT as a single dataset.
- [gdal2tiles.py](https://gdal.org/programs/gdal2tiles.html) - Creates a basemap out of input raster data.
- [ogr2ogr](https://gdal.org/programs/ogr2ogr.html) - Program for manipulating (converting between filetypes, reprojecting, clipping, etc.) vector data files.
- [ogrinfo](https://gdal.org/programs/ogrinfo.html) - Program for displaying summary information about vector data files.


## Recipes

### Clip shapefile to the extent of a raster
<a name="clip-shapefile-to-the-extent-of-a-raster"></a>

```
gdaltindex -t_srs epsg:4326 -f GeoJSON OUTPUT_EXTENT.geojson INPUT_RASTER.tif
ogr2ogr -f GeoJSON -clipsrc OUTPUT_EXTENT OUTPUT_SHAPES_CLIPPED.geojson INPUT_SHAPES.shp
```


### Create polygon of the extent of a raster
<a name="create-polygon-of-the-extent-of-a-raster"></a>

```
gdaltindex -t_srs epsg:4326 -f GeoJSON OUTPUT_EXTENT.geojson INPUT_RASTER.tif
```


### Convert shapefile to geojson
<a name="convert-shapefile-to-geojson"></a>

```
ogr2ogr -f GeoJSON -t_srs epsg:4326 OUTPUT.geojson INPUT.shp
```


### Reproject a raster
<a name="reproject-a-raster"></a>

```
gdalwarp -t_srs epsg:4326 INPUT.tif OUTPUT.tif
```


### Convert a raster into an XYZ basemap
<a name="convert-a-raster-into-an-xyz-basemap"></a>

```
gdal2tiles.py -z 10-16 INPUT_BYTE.tif OUTPUT/
```

Note: The script works as expected when `INPUT_BYTE.tif` is a three band BYTE typed GeoTIFF (where the three bands are RGB).

Note: The `-z` flag sets the zoom levels that are generated in the OUTPUT basemap. See table [here](https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Zoom_levels) for details on what these numbers mean (e.g. to see "zoom level 8" means 1 cm onscreen corresponds to 21.7 km on the ground).


### Crop a raster based on a shapefile
<a name="crop-a-raster-based-on-a-shapefile"></a>

```
gdalwarp -cutline INPUT.shp -crop_to_cutline -dstalpha INPUT.tif OUTPUT.tif
```


### Merge several bands into a single raster
<a name="merge-several-bands-into-a-single-raster"></a>

```
gdalbuildvrt -separate OUTPUT.vrt BAND_1.tif BAND_2.tif BAND_3.tif ...
gdal_translate OUTPUT.VRT OUTPUT.tif
```


### Extract a subset of bands from a raster
<a name="extract-a-subset-of-bands-from-a-raster"></a>

```
gdal_translate -b 1 -b 2 -b 3 INPUT.tif OUTPUT.tif
```

This is useful for extracting the RGB bands from multi-spectral satellite imagery (e.g. for visualization, or use with `gdal2tiles.py`).


### Max (lossless) compression of a raster
<a name="max-lossless-compression-of-a-raster"></a>

```
gdal_translate -co BIGTIFF=YES -co NUM_THREADS=ALL_CPUS -co COMPRESS=LZW -CO PREDICTOR=2 OUTPUT.vrt OUTPUT.tif
```

TODO: Check to make sure this is correct.


### Merge many individual rasters into a single file
<a name="merge-many-individual-rasters-into-a-single-file"></a>

```
gdalbuildvrt OUTPUT.vrt path/to/tiffs/*.tif
```

or

```
gdalbuildvrt OUTPUT.vrt -input_file_list INPUT_FILES.txt
```

then

```
gdal_translate -co BIGTIFF=YES -co NUM_THREADS=ALL_CPUS -co COMPRESS=LZW -CO PREDICTOR=2 OUTPUT.vrt OUTPUT.tif
```

Alternatively, you can use [gdal_merge.py](https://gdal.org/programs/gdal_merge.html).

```
gdal_merge.py -o OUTPUT.tif path/to/tiffs/*.tif
```

Note: These different methods have trade-offs. For a discussion about the differences see [this StackOverflow QA](https://gis.stackexchange.com/questions/44717/whats-the-difference-between-gdalwarp-and-gdal-merge-for-mosaicing).


### Make a thumbnail from a raster
<a name="make-a-thumbnail-from-a-raster"></a>

```
gdal_translate -b 1 -b 2 -b 3 -of JPEG -outsize 400 0 INPUT.tif OUTPUT.jpg
```

Note: this assumes that the first three channels of the raster are RGB.

Note: adjust "400" to control the width of the output, the "0" for height will maintain the original file's aspect ratio.

Example: The following command will create a decent thumbnail from Sentinel 2 multi-channel imagery `gdal_translate -b 4 -b 3 -b 2 -scale 0 4000 0 255 -ot Byte -of JPEG -outsize 1024 0 INPUT_S2.tif OUTPUT.jpg`

### Merge aligned multi-channel rasters
<a name="merge-aligned-multi-channel-rasters"></a>

```python

import rasterio

with rasterio.open(INPUT_FN1,"r") as f:
    data1 = f.read()
    profile1 = f.profile

with rasterio.open(INPUT_FN2,"r") as f:
    data2 = f.read()
    profile2 = f.profile

stacked = np.concatenate([data1,data2], axis=0)

assert profile1["height"] == profile2["height"]
assert profile1["width"] == profile2["width"]

profile = profile1.copy()
profile["count"] = data1.shape[0] + data2.shape[0]

with rasterio.open(OUTPUT_FN, "w", **profile) as f:
    f.write(stacked)
```


### Reproject a shapefile
<a name="reproject-a-shapefile"></a>

```
ogr2ogr -f GeoJSON -t_srs epsg:4326 OUTPUT.geojson INPUT.shp
```

Note: this is identical to the "Convert shapefile to geojson" recipe.


### Quantize float32/float64 raster to byte
<a name="quantize-float32-float64-raster-to-byte"></a>

```
gdal_translate -of GTiff -ot Byte -scale 0 4000 0 255 -co COMPRESS=LZW -co BIGTIFF=YES INPUT_RASTER.tif OUTPUT_RASTER.tif
```

Note: For `-scale 0 4000 0 255`, the first two numbers set the range from `INPUT.tif` that will be compressed to the range specified by the second two numbers in `OUTPUT_RASTER.tif`.


### Reproject and crop a large raster to the spatial extent and spatial resolution of a smaller raster
<a name="reproject-and-crop-a-large-raster-to-the-spatial-extent-and-spatial-resolution-of-a-smaller-raster"></a>

```
gdalwarp -overwrite -ot Byte -t_srs TARGET_CRS -r near -of GTiff -te TARGET_BOUNDS_LEFT TARGET_BOUNDS_BOTTOM TARGET_BOUNDS_RIGHT TARGET_BOUNDS_TOP  -ts TARGET_WIDTH TARGET_HEIGHT -co COMPRESS=LZW -co BIGTIFF=YES INPUT.tif OUTPUT.tif
```

The above is the general format of the command, however I don't think there is an easy way to get the bound information from the command line. The following python code will do this with `rasterio`:

```python
import rasterio
import subprocess

with rasterio.open(TARGET_FN, "r") as f:
    left, bottom, right, top = f.bounds
    crs = f.crs.to_string()
    height, width = f.height, f.width

command = [
    "gdalwarp",
    "-overwrite",
    "-ot", "Byte",
    "-t_srs", crs,
    "-r", "near",
    "-of", "GTiff",
    "-te", str(left), str(bottom), str(right), str(top),
    "-ts", str(width), str(height),
    "-co", "COMPRESS=LZW",
    "-co", "BIGTIFF=YES",
    INPUT_FN,
    OUTPUT_FN
]
subprocess.call(command)
```


### Rasterize shapefile to the extent of a raster
<a name="rasterize-shapefile-to-the-exent-of-a-raster"></a>

```
gdal_rasterize -burn 1.0  -ts TARGET_WIDTH TARGET_HEIGHT -te TARGET_BOUNDS_LEFT TARGET_BOUNDS_BOTTOM TARGET_BOUNDS_RIGHT TARGET_BOUNDS_TOP -ot Byte -of GTiff -co COMPRESS=LZW -co BIGTIFF=YES INPUT_SHAPEFILE.shp OUTPUT.tif
```

Note: `gdal_rasterize` will create the output in the same CRS as `INPUT_SHAPEFILE.shp`.

```python
import rasterio
import subprocess

f = rasterio.open(TARGET_FN,"r")
left, bottom, right, top = f.bounds
crs = f.crs.to_string()
height, width = f.height, f.width
f.close()

command = [
    "gdal_rasterize",
    "-ot", "Byte",
    "-burn", "1.0",
    "-of", "GTiff",
    "-te", str(left), str(bottom), str(right), str(top),
    "-ts", str(width), str(height),
    "-co", "COMPRESS=LZW",
    "-co", "BIGTIFF=YES",
    INPUT_SHAPEFILE_FN,
    OUTPUT_FN
]
subprocess.call(command)
```

Another example for when you would like to specify an attribute field ("label" here) on the features to be used for a burn-in value:
```
gdal_rasterize -a label -a_nodata 0 -ot Byte -tr 0.000269494585236 0.000269494585236 -co COMPRESS=LZW INPUT_SHAPEFILE.shp OUTPUT.tif
```
`tr` is the target resolution ("Pixel Size" in `gdalinfo` if you already have an example raster file of the desired resolution).


### Convert GeoTIFF to COG
<a name="convert-geotiff-to-cog"></a>

```
gdalwarp -co BIGTIFF=YES -co NUM_THREADS=ALL_CPUS -co COMPRESS=LZW -CO PREDICTOR=2 -of COG INPUT.tif OUTPUT.tif
```

Note: This requires GDAL version >= 3.1
