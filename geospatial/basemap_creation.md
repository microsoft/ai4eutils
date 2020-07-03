# Basemap creation

Often our geospatial ML models will operate on a _patch_ level, where a _patch_ is a small crop of satellite imagery - 256x256 for example. Patches, however, are not useful for sharing results over large areas, and are not particularly useful to look at for qualitatively evaluating how well a model is performing over large areas. Instead, we would like to have an interactive map that lets us pan/zoom around the area that we are studying and switch between different layers of imagery and predictions. This page documents two way to do this: with the [gdal2tiles script](https://gdal.org/programs/gdal2tiles.html), and with [GeoServer](http://geoserver.org/).


## Using gdal2tiles to turn *model predictions* into an interactive map

Assuming that you have a directory of model predictions (values in a GeoTIFF format with an attached color pallete and uint8 data type) in `output_tiles/` that completely tile your area of study, you can use the following steps to create a basemap and view it in a web browser:

### Create a VRT out of the preditions

```
gdalbuildvrt labels.vrt output_tiles/*.tif
```

This will create a VRT view of your dataset. A VRT is a "virtual" dataset, or, more specifically, an XML file with pointers to other component datasets. With this step you are combining all of the individual patches in `output_tiles/` into a single contiguous layer that you can address as one file in future commands. Importantly this will *not* copy all of your data.  

### Create a RGB version of the VRT

```
gdal_translate -of vrt -expand rgba labels.vrt temp.vrt
```

When you create the VRT in the previous step it will contain a single channel with predicted class values, however we need an RGB(A) version of this to render into a basemap in the next step. This command will create another VRT file called `temp.vrt` that contains 4 bands of RGBA values describing the class color for each pixel, instead of the original single band of class values. This step relies on the color pallete you include when saving the original GeoTIFF patch predictions.


### Create a basemap from the RGBA version of your dataset

```
gdal2tiles.py -z 8-15 temp.vrt output_tiles_basemap/
```

Note: This command can take hours depending on the size of your dataset and the zoom levels you choose to generate. Larger areas and higher zoom levels will respectively take quadratically and exponentially longer times to generate. **See the first section of [this page](https://wiki.openstreetmap.org/wiki/Zoom_levels) for a description of how large a pixel is at each zoom level.**

This step will create a directory `output_tiles_basemap/` that contains a _basemap_ in XYZ format, as well as several HTML files for viewing the basemap with several common web mapping libraries (including `leaflet.html` used in the next step). The contents of the basemap are many 256x256 PNG images arranged into a structure `output_tiles_basemap/{Z}/{X}/{Y}.png` where Z, X, and Y represent the zoom level, row, and column in a grid that maps to location on Earth, and the PNG files themself contain a rendering of what was stored in your patches from different zoom levels. This structure will be used by the different web mapping libraries to render the content in your patches in a web browser.

### Modify the `leaflet.html` file with some sane defaults.

- Replace `opacity: 0.7` with `opacity: 1.0`
- Replace `temp.vrt` with the name of your dataset.
- Replace `layers: [osm]` with `layers: [white, lyr]`
- Rename `leaflet.html` to `index.html`

### Host the directory on a web server

Locally, you can simply open `index.html` (previously `leaflet.html`) in a web browser to see the final map, however to share it with partners it is helpful to host it somewhere.

For example, to setup a web server on an Ubuntu 18.04 machine:
```
sudo apt update
sudo apt install apache2
sudo chown -R $USER /var/www/html
```
Now, after ensuring that port 80 is open (e.g. by adding a rule in the Networking tab for the VM on Azure), you should be able to see an example page at `http://<your public ip or domain>/`. If you copy the `leaflet.html` page and basemap directories to `/var/www/html/` then they will be accessible to the world.


## Using gdal2tiles to turn *satellite imagery* into an interactive map

TODO

## Using GeoServer

TODO

