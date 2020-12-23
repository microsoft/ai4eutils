# Downloading Geospatial Data Using Google Earth Engine

While working on geospatial applications we often need to download satellite data. Google Earth Engine (GEE) offers tools to download common geospatial data including LandSat and Sentinel imagery among others. Check out the data catalog [here.](https://developers.google.com/earth-engine/datasets)

There are several ways to use GEE. In this document we will discuss the [Javascript-based code editor](https://developers.google.com/earth-engine/playground) and the Python API.

## GEE Javascript-based Code Editor

The GEE Javascript code editor is very well documented [here](https://developers.google.com/earth-engine/playground). Take some time to review the documentation. The code editor is the most popular way to interact with the GEE. It offers a visualization tool that let's you see the imagery before downloading it. Let's go through an example of how to use the code editor to download Sentinel data.

### Downloading Sentinel Data Using GEE Code Editor

The code editor is available to anyone, and can be found at [this site](https://code.earthengine.google.com/). If you have not already, you will need to enable access by logging in using a registered Google account. You should see an empty new script on the top-middle part of the screen.



#### Selecting Area of Interest

With satellite imagery you can investigate any spot on Earth. Select a region in the world you are interested on. Make sure that the projection for the coordinates is epsg:4326 (i.e. simple lat/lons).

```
var geometry = ee.Geometry.Polygon([ [ [ 73.371701190307323441, 16.3614302290214900118745 ], [ 73.369360101473, 16.36413022805 ], [ 73.3724101022093, 16.37065038004363329949862 ], [ 73.375780231141, 16.370000408038201353 ], [ 73.376640119030, 16.36753022902 ],  [ 73.371701190307323441, 16.3614302290214900118745 ] ] ]);
```

As an alternative you can paste the GeoJSON feature for the area, and get the geometry as follows:

```
var feature = ee.Feature({
  "type": "Feature",
  "properties": { "geometry": {
    "type": "Polygon",
    "coordinates": [ [ [ 73.371701190307323441, 16.3614302290214900118745 ], [ 73.369360101473, 16.36413022805 ], [ 73.3724101022093, 16.37065038004363329949862 ], [ 73.375780231141, 16.370000408038201353 ], [ 73.376640119030, 16.36753022902 ],  [ 73.371701190307323441, 16.3614302290214900118745 ] ] ] 
  }
});

var geometry = feature.geometry();

```


#### The Sentinel 2 Collection

In GEE each collection has its own id and you can find them in the [GEE catalog](https://developers.google.com/earth-engine/datasets). The snippet id for the Sentinel-2 MSI: MultiSpectral Instrument, Level-2A product is "COPERNICUS/S2_SR" as described [here](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR). 

You can have access to the Sentinel 2 collection with the following code:

```
var sentinel2_collection = ee.ImageCollection('COPERNICUS/S2_SR');
```

For other data sources just change the snippet id to the one corresponding to your collection of interest.

#### Filtering the collection

There are many filters you can apply to the collection. Let's discuss the most common ones.

##### Filtering to the area of interest

The "ee.filter.bounds()" method allows to select the geometry defined above.

```
// filter area
var sentinel2_aoi = sentinel2_collection.filter(ee.Filter.bounds(geometry));
```

##### Filtering by date range

The ".filterDate()" method allows to filter by date range.

```
//filter by date range
var startDate = "2019-04-01";
var endDate = "2019-10-31";
var data = sentinel2_collection.filterDate(startDate, endDate);


```

#### Masking out clouds 

Most satellite imagery comes with cloud mask that can be used to mask out clouds from imagery. The following function mask out clouds for Sentinel 2 images.

```
/**
 * Function to mask clouds using the Sentinel-2 QA band
 * @param {ee.Image} image Sentinel-2 image
 * @return {ee.Image} cloud masked Sentinel-2 image
 */

function maskS2clouds(image) {
  var qa = image.select('QA60');
  // Bits 10 and 11 are clouds and cirrus, respectively.
  var cloudBitMask = 1 << 10;
  var cirrusBitMask = 1 << 11;
  // Both flags should be set to zero, indicating clear conditions.
  var mask = qa.bitwiseAnd(cloudBitMask).eq(0).and(qa.bitwiseAnd(cirrusBitMask).eq(0));
  return image.updateMask(mask);
}

var data = sentinel2_collection.map(maskS2clouds);
```
##### Filtering by Max Percentage of Cloud
The `ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', use_scenes_with_max_cloud_percentage_of)` method allows to filter by cloud percentage.

```
var use_scenes_with_max_cloud_percentage_of = 3;

var data = sentinel2_collection.filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', use_scenes_with_max_cloud_percentage_of));
```

#### Combining all filters and getting median image from all images in a date range

Filters can be combined. Let's do an example:


```
var sentinel2_median_image = ee.ImageCollection('COPERNICUS/S2_SR')
                  .filterDate(startDate, endDate)
                  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', use_scenes_with_max_cloud_percentage_of))
                  .filter(ee.Filter.bounds(geometry))
                  .map(maskS2clouds)
                  .median();
```

#### Visualizing the data on the GEE map 
```
var center = geometry().centroid().coordinates();
Map.setCenter(center.get(0).getInfo(), center.get(1).getInfo(), 10);
var rgbVis = {
  min: 0.0,
  max: 3000.0,
  bands: ['B4', 'B3', 'B2'],
};

Map.addLayer(geometry, {color: "#CCCCCC"}, "AOI", true, 1.0);
Map.addLayer(sentinel2_median_image, rgbVis, 'Sentinel RGB');
```

#### Exporting Data to Google Drive

You can export images, map tiles, tables and video from Earth Engine. The exports can be sent to your Google Drive account, to Google Cloud Storage or to a new Earth Engine asset. Read [here](https://developers.google.com/earth-engine/exporting) for more details. [rclone](https://rclone.org/) is useful for programmatically downloading exported scenes from Google Drive.

```
Export.image.toDrive({
    image: sentinel2_median_image.select('B.+'), # we just want the imagery bands, i.e. bands with names that start with "B"
    scale: 10,
    region: geometry
});

```

#### Entire Script

```
/**
 * Function to mask clouds using the Sentinel-2 QA band
 * @param {ee.Image} image Sentinel-2 image
 * @return {ee.Image} cloud masked Sentinel-2 image
 */

function maskS2clouds(image) {
  var qa = image.select('QA60');
  // Bits 10 and 11 are clouds and cirrus, respectively.
  var cloudBitMask = 1 << 10;
  var cirrusBitMask = 1 << 11;
  // Both flags should be set to zero, indicating clear conditions.
  var mask = qa.bitwiseAnd(cloudBitMask).eq(0).and(qa.bitwiseAnd(cirrusBitMask).eq(0));
  return image.updateMask(mask);
}

// Select AOI
var geometry = ee.Geometry.Polygon([ [ [ 73.371701190307323441, 16.3614302290214900118745 ], [ 73.369360101473, 16.36413022805 ], [ 73.3724101022093, 16.37065038004363329949862 ], [ 73.375780231141, 16.370000408038201353 ], [ 73.376640119030, 16.36753022902 ],  [ 73.371701190307323441, 16.3614302290214900118745 ] ] ]);

var startDate = "2019-04-01";
var endDate = "2019-10-31";
var use_scenes_with_max_cloud_percentage_of = 3;

//----------------------------------------------------

/**
 * Function to mask clouds using the Sentinel-2 QA band
 * @param {ee.Image} image Sentinel-2 image
 * @return {ee.Image} cloud masked Sentinel-2 image
 */
var sentinel2_median_image = ee.ImageCollection('COPERNICUS/S2_SR')
                  .filterDate(startDate, endDate)
                  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', use_scenes_with_max_cloud_percentage_of))
                  .filter(ee.Filter.bounds(geometry))
                  .map(maskS2clouds)
                  .median();

var rgbVis = {
  min: 0.0,
  max: 3000.0,
  bands: ['B4', 'B3', 'B2'],
};

var center = geometry.centroid().coordinates();
Map.setCenter(center.get(0).getInfo(), center.get(1).getInfo(), 10);

Map.addLayer(geometry, {color: "#CCCCCC"}, "AOI", true, 1.0);
Map.addLayer(sentinel2_median_image, rgbVis, 'Sentinel RGB');

// set this to "true" when you find the settings you want
var doExport = true;
if(doExport){
  Export.image.toDrive({
    image: sentinel2_median_image.select('B.+'),
    scale: 10,
    region: geometry
  });
}
```

## GEE Python API

GEE also offers a python API to download geospatial data.

Note: Some of the steps on this document are borrowed from [here](https://towardsdatascience.com/a-quick-introduction-to-google-earth-engine-c6a608c5febe).

### Downloading Sentinel Data Using Python API

To use the GEE python API you need to install the necessary package. After [signing up](https://signup.earthengine.google.com/#!/), you can install the Earth Engine Python API with pip:

```pip install earthengine-api```

#### GEE authentication

After the api is installed, you need to set up your authentication credentials on your computer. The entire process is described in detail in the [here](https://developers.google.com/earth-engine/python_install). 

#### Other Useful Packages

The Earth Engine Package is simply called ```ee```, and with that, you can start to set up your toolbox. Apart from ```ee```. Unfortunely, the python api misses functionality to visualize the date you will download. Two very useful packages to compensate for that include Folium for interactive maps and geehydro. Geehydro is intended to be a package for inundation dynamics in the GEE platform but is extraordinarily useful as it emulates some of the functions from the Javascript API. You can install these other packages using pip:

```
pip install folium
pip install geehydro
```

#### Example: Downloading Sentinel 2 Data using GEE Python API

In this [Jupyter notebook](https://github.com/microsoft/ai4eutils/blob/master/geospatial/notebooks/GEE_python_api.ipynb) we reproduce the same previously presented example using the GEE python API. A html version is available [here](https://htmlpreview.github.io/?https://github.com/microsoft/ai4eutils/blob/master/geospatial/notebooks/GEE_python_api.html)