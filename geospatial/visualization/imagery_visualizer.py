"""
Visualize multi-band spectral imagery data that rasterio can load.

Mainly catering to Landsat, Sentinel-2 and SRTM DEM.
"""

import math
import statistics
from collections import namedtuple
from io import BytesIO
from typing import Union, Tuple, Iterable

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from PIL import Image
from skimage import exposure, img_as_ubyte

Numeric = Union[int, float]

# Output is darker for gamma > 1, lighter if gamma < 1. This is not the same as GEE visParams' gamma!
DefaultVisParams = namedtuple('DefaultVisParams', ['min', 'max', 'gamma'])


class ImageryVisualizer(object):
    # using class variables to give default values works well so long as you do it with immutable types (floats, int)
    # reference: https://stackoverflow.com/questions/2681243/how-should-i-declare-default-values-for-instance-variables-in-python

    # Landsat Surface Reflectance
    # ee.ImageCollection("LANDSAT/LC08/C01/T1_SR")
    default_landsat_sr_viz_params = DefaultVisParams(
        min=0.0,
        max=3000.0,
        gamma=0.7
    )

    # ee.ImageCollection('COPERNICUS/S2_SR')
    default_sentinel2_sr_viz_params = DefaultVisParams(
        min=0.0,
        max=3000.0,
        gamma=0.7
    )

    # the band combinations assume that while downloading the scenes, bands are selected in its original order.

    # Landsat 8 band combinations
    landsat8_visible = (4, 3, 2)  # band numbers start from 1
    landsat8_swir = (7, 5, 1)  # shortwave infrared SWIR as red, NIR as green, and deep blue as blue

    sentinel2_visible = (4, 3, 2)

    # to be used with e.g. already normalized elevation data
    normalized_band_normalizer = mcolors.Normalize(vmin=-1, vmax=1)

    @staticmethod
    def show_single_band(raster: np.ndarray,
                         size_inches: Tuple[Numeric, Numeric] = (4, 4),
                         cmap: Union[mcolors.Colormap, str] = 'gist_yarg',
                         normalizer: mcolors.Normalize = normalized_band_normalizer) -> Tuple[Image.Image, BytesIO]:
        """Visualizes a single band passed in as a numpy array.

        Args:
            raster: numpy array of imagery values; needs to be 2D after squeezing
            size: matplotlib size in inches (h, w)
            cmap: matplotlib recognized color map str or custom matplotlib colormap object
            normalizer: a matplotlib.colors.Normalize object. Default is one that has min value at -1
                and max at 1.

        Returns:
            (im, buf) - (PIL image of the matplotlib figure, a BytesIO buf containing the matplotlib Figure
                saved as a PNG)
        """
        raster = raster.squeeze()
        assert len(raster.shape) == 2, 'Single band should be a 2D array after squeezing.'

        _ = plt.figure(figsize=size_inches)
        _ = plt.imshow(raster, cmap=cmap, norm=normalizer)

        buf = BytesIO()
        plt.savefig(buf, format='png')
        plt.close()
        buf.seek(0)
        im = Image.open(buf)
        return im, buf

    @staticmethod
    def _norm_band(bands: np.ndarray,
                   band_min: Numeric = 0,
                   band_max: Numeric = 7000,
                   gamma: Numeric = 1.0) -> np.ndarray:
        """Clip, normalize by band_min and band_max, and gamma correct a tile. All bands use the
        same band_min, band_max and gamma. If each band should be processed differently, call this function
        with each band and its normalization parameters, and stack afterwards.

        Args:
            bands: a numpy array of dims (num_bands, w, h), representing a tile or chip
            band_min: minimum value the pixels are clipped tp
            band_max: maximum value the pixels are clipped to
            gamma: the gamma value to use in gamma correction. Output is darker for gamma > 1, lighter if gamma < 1.
                This is not the same as GEE visParams' gamma!

        Returns:
            clipped, normalized by min and max, and gamma corrected version of the single-band image,
            as an array with dtype float32.
        """
        assert band_max > band_min, f'invalid range specified by band_min {band_min} and band_max {band_max}'
        bands = np.clip(bands, band_min, band_max)

        bands = (bands - band_min) / (band_max - band_min)

        bands = exposure.adjust_gamma(bands, gamma)
        return bands

    @staticmethod
    def get_landsat8_ndvi(tile_reader: rasterio.DatasetReader,
                           window: Union[rasterio.windows.Window, Tuple] = None) -> np.ndarray:
        """Computes the NDVI (Normalized Difference Vegetation Index) over a tile or a section
        on the tile specified by the window, for Landsat 8 tiles.

        NDVI values are between -1.0 and 1.0 (hence "normalized"), mostly representing greenness, where any
        negative values are mainly generated from clouds, water, and snow, and values
        near zero are mainly generated from rock and bare soil. Very low values (0.1 and below)
        of NDVI correspond to barren areas of rock, sand, or snow. Moderate values (0.2 to 0.3)
        represent shrub and grassland, while high values (0.6 to 0.8) indicate temperate
        and tropical rainforests. Source: https://desktop.arcgis.com/

        For surface reflectance products, there are some out of range values in the red and near infrared bands
        for areas around water/clouds. We should get rid of these before NDVI calculation,
        otherwise the NDVI will also be out of range.
        Source: https://www.researchgate.net/post/Why_Landsat_8_NDVI_Values_are_out_of_Range_Not_in_between-1_to_1

        If we decide not to get rid of invalid values in the red and NIR bands and see some out-of-range NDVI values,
        we can check to see if these out-of-range NDVI values are a small minority in all pixels in the dataset.

        Args:
            tile_reader: a rasterio.io.DatasetReader object returned by rasterio.open()
            window: a tuple of four (col_off x, row_off y, width delta_x, height delta_y)
                to specify the section of the tile to compute NDVI over, or a rasterio Window object

        Returns:
            2D numpy array of dtype float32 of the NDVI values at each pixel
            Pixel value is set to 0 if the sum of the red and NIR value there is 0 (empty).
        """
        if window and isinstance(window, Tuple):
            window = rasterio.windows.Window(window[0], window[1], window[2], window[3])

        band_red = tile_reader.read(4, window=window, boundless=True, fill_value=0).squeeze()
        band_nir = tile_reader.read(5, window=window, boundless=True, fill_value=0).squeeze()

        sum_red_nir = band_nir + band_red

        # sum of the NIR and red bands being zero is most likely because this section is empty
        # this workaround means that the final NDVI at such pixels are 0.
        sum_red_nir[sum_red_nir == 0.0] = 1

        ndvi = (band_nir - band_red) / sum_red_nir
        return ndvi

    @staticmethod
    def show_patch(tile_reader: rasterio.DatasetReader,
                   bands: Union[Iterable, int],
                   window: Union[rasterio.windows.Window, Tuple] = None,
                   band_min: Numeric = 0,
                   band_max: Numeric = 7000,
                   gamma: Numeric = 1.0,
                   size: Tuple[Numeric, Numeric] = (256, 256),
                   return_array: bool = False) -> Union[np.ndarray, Image.Image]:
        """Show a patch of imagery.

        Args:
            tile_reader: a rasterio.io.DatasetReader object returned by rasterio.open()
            bands: list or tuple of ints, or a single int, indicating which band(s) to read. See notes
                below regarding the order of band numbers to pass in
            window: a tuple of four (col_off x, row_off y, width delta_x, height delta_y)
                to specify the section of the tile to return, or a rasterio Window object
            band_min: minimum value the pixels are clipped tp
            band_max: maximum value the pixels are clipped to
            gamma: the gamma value to use in gamma correction. Output is darker for gamma > 1, lighter if gamma < 1.
                This is not the same as GEE visParams' gamma!
            size: Used when this function is called to produce a PIL Image, i.e. only when
                `return_array` is False.
                None if do not resize, otherwise a (w, h) tuple in pixel unit.
                Default is (256, 256). (500, 500) looks better in notebooks
            return_array: True will cause this function to return a numpy array of dtype float32;
                False (default) to get a PIL Image object (values scaled to be uint8 values)

        Returns:
            a PIL Image object, resized to `size`, or the (not resized, float32) numpy array
            if `return_array` is true. The dims start with height and width, optionally
            with the channel dim at the end if greater than 1.

            rasterio read() does not pad with 0. The array returned may be smaller than the window specified

        Notes:
            - PIL renders the bands in RGB order; keep that in mind when passing in `bands` as a list or tuple
              so that the bands are mapped to Red, Green and Blue in the desired order.
            - Band index starts with 1
        """
        if isinstance(bands, int):
            bands = [bands]  # otherwise rasterio read will return a 2D array instead of 3D

        if window and isinstance(window, Tuple):
            window = rasterio.windows.Window(window[0], window[1], window[2], window[3])

        # read as (bands, rows, columns) or (c, h, w)
        bands = tile_reader.read(bands, window=window, boundless=True, fill_value=0)  # dtype is float32

        bands = ImageryVisualizer._norm_band(bands, band_min=band_min, band_max=band_max, gamma=gamma)

        # need to rearrange to (h, w, channel/bands)
        bands = np.transpose(bands, axes=[1, 2, 0])

        bands = bands.squeeze()  # PIL accepts (h, w, 3) or (h, w), not (h, w, 1)

        if return_array:
            return bands

        # skimage.img_as_ubyte: negative input values will be clipped. Positive values are scaled between 0 and 255
        # fine to use here as we already got rid of negative values by normalizing above
        bands = img_as_ubyte(bands)

        im = Image.fromarray(bands)
        if size:
            im = im.resize(size)
        return im

    @staticmethod
    def show_landsat8_patch(tile_reader: rasterio.DatasetReader,
                            bands: Union[Iterable, int] = landsat8_visible,
                            window: Union[rasterio.windows.Window, Tuple] = None,
                            band_min: Numeric = 0,
                            band_max: Numeric = 3000,
                            gamma: Numeric = 0.7,
                            size: Tuple[Numeric, Numeric] = (256, 256),
                            return_array: bool = False) -> Union[np.ndarray, Image.Image]:
        """Show a patch of imagery, with default options sensible for Landsat 8 imagery.

        For arguments and return value, see show_patch()
        """
        return ImageryVisualizer.show_patch(tile_reader, bands=bands, window=window,
                                            band_min=band_min, band_max=band_max, gamma=gamma,
                                            size=size, return_array=return_array)

    @staticmethod
    def show_sentinel2_patch(tile_reader: rasterio.DatasetReader,
                             bands: Union[Iterable, int] = sentinel2_visible,
                             window: Union[rasterio.windows.Window, Tuple] = None,
                             band_min: Numeric = 0,
                             band_max: Numeric = 7000,
                             gamma: Numeric = 1.0,
                             size: Tuple[Numeric, Numeric] = (256, 256),
                             return_array: bool = False) -> Union[np.ndarray, Image.Image]:
        """Show a patch of imagery, with default options sensible for Sentinel 2 imagery.

        For arguments and return value, see show_patch()
        """
        return ImageryVisualizer.show_patch(tile_reader, bands=bands, window=window,
                                            band_min=band_min, band_max=band_max, gamma=gamma,
                                            size=size, return_array=return_array)

    @staticmethod
    def stat_landsat_tile(tile_tif, n_bins=40):
        band_stats = {}

        # band index starts with 1 as in GDAL
        for b in range(1, tile_tif.count + 1):
            band = tile_tif.read(b).flatten()  # returns a numpy.ndarray; flatten otherwise hist is "2D"
            band_stats[b] = {
                'min': band.min(),
                'max': band.max(),
                'mean': band.mean(),
                'std_dev': math.sqrt(band.var()),
                'medium': statistics.median(band)
            }

            fig = plt.figure()
            ax = fig.add_subplot(1, 1, 1)
            n, bins, patches = ax.hist(band, bins=n_bins)
            ax.set_title(f'Band count {b}')
            ax.set_xlabel('pixel value')
            ax.set_ylabel('count')
            band_stats[b]['hist'] = fig

        return band_stats
