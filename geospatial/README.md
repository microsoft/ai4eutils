# Geospatial shared code components


## Capabilities we hope to develop

1. Visualization
2. Data loading (patches of labels and imagery to be used in a Random forest, PyTorch or TF model)
3. Data downloading (documentation walk-throughs mostly)
4. Interactive map for displaying and discussing input and model output
5. Interactive re-labeling tool (see the the landcover [repo](https://github.com/microsoft/landcover))
6. Bring your own data (BYOD)
7. "Default" models for segmentation and detection
8. Model evaluation metrics computataion over an area / split


## Content

- [recipes_and_guides](recipes_and_guides): various tutorials on how to do things with GDAL, Google Earth Engine, QGIS, and other Python packages.
  - [Creating basemaps from imagery or predictions](recipes_and_guides/basemap_creation.md)
  - [Downloading data from Google Earth Engine](recipes_and_guides/geospatial_data_download_using_GEE.md)
  - [Collection of GDAL command line recipes](recipes_and_guides/geospatial_recipes.md)
  - [Collection of QGIS tips and tricks](recipes_and_guides/qgis_recipes.md)
- [visualization](visualization):
  - RasterLabelVisualizer: a class for visualizing raster mask labels and hardmax or softmax model predictions, instantiated with a user-provided category name and color mapping.
  - ImageryVisualizer: a collection of static methods for chipping and viewing multi-band spectral imagery data that rasterio can load, such as Landsat 8, Sentine-2, NAIP and SRTM DEM.


## Satellite data terminology

Here we define various terms we use internally to describe satellite data. Throughout, we use the term _imagery_ to mean both multispectral satellite/aerial imagery, and other types of raster based data sources (e.g. digital elevation maps, synthetic apeture radar data, gridded weather data, etc.) that may be consumed by a model or used as labels.

### Scene

Source imagery that were sectioned by the data provider to not exceed some maximally convinient size for downloads. We do not modify these; they are stored for archival purposes.

Scenes in this sense does not have to correspond to the original "scenes" that the satellite sensor imaged (e.g. a Landsat scene); they can be cloud-masked and composited and cut along arbitrary boundaries.

Examples:
- Landsat 8 imagery downloaded over certain extents from Google Earth Engine
- SRTM DEM data over an extent
- A GeoTIFF of commercial satellite imagery from a partner

### Tile

Large-ish image _patches_ and label masks that are generated from _scenes_ and vector data sources, and stored as "analysis-ready" data. Labels that come as polygons in the shapefile or geoJSON format are turned into pixel masks at this stage.

These should be of a size convinient for blobfuse caching and manual inspection in desktop GIS applications. Reasonable sizes are on the order of millions of pixels, e.g. can range from 2000 by 2000 pixels to 20,000 by 20,000 pixels.

### Chip

Smaller image _patches_ and label masks sized specifically to be consumed by a model during training/evaluation. These can be cut from _tiles_ on-the-fly during training and evaluation, or offline in a _chipping_ step. If the latter, chips are stored in _shards_.

### Shard

A shard is a set of homogenously sized image chips that are stored together on disk - as a numpy array, TFRecord, or pickle file, etc - with dimensions `(num_chips_in_shard, channels, chip_height, chip_width)`.

### Patch

Any unit of imagery. It can be a _tile_ or a _chip_ or an area that does not conform to the other more precisely defined units.


### Preprocessing

Preprocessing, which may include 
- combining different sources of data (Landsat 8 and DEM) by resampling
- re-projecting them to a common coordinate system
- and normalizing and gamma correcting pixel values. 

can happen either during the creation of _tiles_ from _scenes_ or the creation of _chips_ from _tiles_. 

To ensure reproducibility:
- A set of _tiles_, and _shards_ of _chips_ if they were made, should be treated as immutable once an experiment has been run using them as input data
- **Fully document the procedures** used to create _tiles_ and _chips_ from original _scenes_ (ideally the steps should be entirely programmatic). 
- The queries and steps used to obtain the _scenes_ from the data provider should also be well-documented and repeatable.


#### Preparing data to use with the interactive re-training tool

You should be aware that in order to use the [interactive re-training tool](https://github.com/Microsoft/landcover), the **_tiles_ need to contain all the data required by your model**. For example, if you have two overlapping _scenes_ where one contains Landsat 8 imagery at a 30m spatial resolution and the other contains digital elevation data at a 1m spatial resolution, then you can write a script to re-project both to 1m spatial resolution in a shared coordinate system and create multiple 2,000 by 2,000 pixel GeoTIFF _tiles_ containing the two data sources stacked together. The tool will pass extends of these tiles to your model.

Other preprocessing steps such as normalizing pixel values can still be carried out in the _tiles_ to _chips_ step, and you should just be aware that in that case, these steps add latency when using the tool.

