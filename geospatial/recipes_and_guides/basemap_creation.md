# Basemap creation

Often our geospatial ML models will operate on a _patch_ level, where a _patch_ is a small crop of satellite imagery - 256x256 for example. Patches, however, are not useful for sharing results over large areas, and are not particularly useful to look at for qualitatively evaluating how well a model is performing over large areas. Instead, we would like to have an interactive map that lets us pan/zoom around the area that we are studying and switch between different layers of imagery and predictions. This page documents two way to do this: with the [gdal2tiles script](https://gdal.org/programs/gdal2tiles.html), and with [GeoServer](http://geoserver.org/).

## Installing GDAL

The easiest way I've found to install GDAL is through anaconda. Here we create a new environment with GDAL version greater than 2.3 (this is important as 2.3 introduced multi-processing support for `gdal2tiles.py`) for running the examples on this page:
```
conda create --name gdal python "gdal>=2.3" 
conda activate gdal
```

## Using gdal2tiles to turn *model predictions* into an interactive map

Assuming that you have a directory of model predictions (**values in a GeoTIFF format with an attached color palette and uint8 data type**) in `output_tiles/` that completely tile your area of study, you can use the following steps to create a basemap and view it in a web browser:

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

Skip this step if your TIFFs are already RGBA or RGB images.

### Create a basemap from the RGBA version of your dataset

```
gdal2tiles.py --processes=NB_PROCESSES -z 8-15 temp.vrt output_tiles_basemap/
```

Set `NB_PROCESSES` to the number of cores you have on your machine.

Note: This command can take hours depending on the size of your dataset and the zoom levels you choose to generate. Larger areas and higher zoom levels will respectively take quadratically and exponentially longer times to generate. **See the first section of [this page](https://wiki.openstreetmap.org/wiki/Zoom_levels) for a description of how large a pixel is at each zoom level.**

This step will create a directory `output_tiles_basemap/` that contains a _basemap_ in XYZ format, as well as several HTML files for viewing the basemap with several common web mapping libraries (including `leaflet.html` used in the next step). The contents of the basemap are many 256x256 PNG images arranged into a structure `output_tiles_basemap/{Z}/{X}/{Y}.png` where Z, X, and Y represent the zoom level, row, and column in a grid that maps to location on Earth, and the PNG files themself contain a rendering of what was stored in your patches from different zoom levels. This structure will be used by the different web mapping libraries to render the content in your patches in a web browser.

### Modify the `leaflet.html` file with some sane defaults.

- Replace `opacity: 0.7` with `opacity: 1.0`
- Replace `temp.vrt` with the name of your dataset.
- Replace `layers: [osm]` with `layers: [white, lyr]`
- Rename `leaflet.html` to `index.html`

### Add a legend

Towards the end of the `<script>` section, add these lines and replace `"legend.png"` with the image of your legend.

```javascript
  // Legend
  var src = '<img src="legend.png">';
  var title = L.control({position: 'bottomright'});
  title.onAdd = function(map) {
      this._div = L.DomUtil.create('div', 'ctl legend');
      this.update();
      return this._div;
  };
  title.update = function(props) {
      this._div.innerHTML = src;
  };
  title.addTo(map);
```

### Host the directory on a web server

Locally, you can simply open `index.html` (previously `leaflet.html`) in a web browser to see the final map, however to share it with partners it is helpful to host it somewhere.

For example, to setup a web server on an Ubuntu 18.04 machine:
```
sudo apt update
sudo apt install apache2
sudo chown -R $USER /var/www/html
```
Now, after ensuring that port 80 is open (e.g. by adding a rule in the Networking tab for the VM on Azure Portal), you should be able to see an example page at `http://<your public ip or domain>/`. If you copy the `leaflet.html` page and basemap directories to `/var/www/html/` then they will be accessible to the world.

Alternatively, for a quick but less performant solution, you can use the `http.server` module that comes with Python 3. Navigate to the basemap output folder `output_tiles_basemap` and execute
```
python -m http.server 6001
```
to start the webserver on port 6001 (you might want to do this in a `tmux` session if you plan to leave it up for a while). The map will be viewable at `http://<your public ip or domain>:6001`. You need to open port 6001 on Azure Portal. 


## Using gdal2tiles to turn *satellite imagery* into an interactive map

Assuming your imagery as a set of .tif files from the data provider or resulting from a preprocessing/tiling step are stored in a directory, you can use the following steps to create a basemap and view it in a web browser:


### Create a VRT out of your multiple .tif imagery files

```bash
gdalbuildvrt imagery.vrt imagery/*.tif
```

Same as in the above instructions for model predictions, this will create a VRT view of your dataset so we can reference your set of .tif files as one entity. This and the next step should finish quickly.


### Create a RGB version of the VRT

```bash
gdal_translate imagery.vrt imagery_rgb.vrt -of vrt -ot Byte -scale_1 0 3000 -scale_2 0 3000 -scale_3 0 3000 -exponent 0.7 -co PHOTOMETRIC=RGB -b 4 -b 3 -b 2 -colorinterp red,green,blue 
```

In this example, we extract the RGB bands of some Landsat 8 scene where band 4 is the red band, band 3 the green band and band 2 the blue band, specified with the `-b` arguments. 

Note that we apply a min/max scaling (`-scale_[band]`) to each band (although here they are the same so no need to specify separately) and a non-linear scaling with a power function (`-exponent`, values greater than 1 will make image look darker; smaller than 1 will make image look brighter). Values in this example are chosen to make Landsat 8 surface reflectance imagery look good. See the documentation on `gdal_translate` [here](https://gdal.org/programs/gdal_translate.html).


### Create a basemap from the RGB version of your dataset

```bash
gdal2tiles.py --processes=NB_PROCESSES -z 8-13 imagery_rgb.vrt imagery_basemap/
```

Set `NB_PROCESSES` to the number of cores you have on your machine.

See the corresponding section above for model predictions to understand this step and how to view the resulting basemap.

The path to the directory `imagery_basemap` can be given to a tile map service to display your imagery.


## Using GeoServer

TODO

