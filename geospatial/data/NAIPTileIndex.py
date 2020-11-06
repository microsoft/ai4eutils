import os
import pickle
import urllib.request

import rtree # pip install Rtree; apt install libspatialindex4v5
import shapely # pip install shapely

class NAIPTileIndex:
    '''Utility class for performing NAIP tile lookups by location
    '''
    NAIP_BLOB_ROOT = 'https://naipblobs.blob.core.windows.net/naip/'
    NAIP_INDEX_BLOB_ROOT = "https://naipblobs.blob.core.windows.net/naip-index/rtree/"
    INDEX_FNS = ["tile_index.dat", "tile_index.idx", "tiles.p"]

    def __init__(self, base_path, verbose=False):
        '''Loads the tile index into memory (~400 MB) for use by `self.lookup()`. Downloads the index files from the blob container if they do not exist in the `base_path/` directory.

        Args:
            base_path (str): The path on the local system to look for/store the three files that make up the tile index. This path will be created if it doesn't exist.
            verbose (bool): Whether to be verbose when downloading the tile index files
        '''

        # Download the index files if it doens't exist
        if not os.path.exists(base_path):
            os.makedirs(base_path)
        for fn in NAIPTileIndex.INDEX_FNS:
            if not os.path.exists(os.path.join(base_path, fn)):
                download_url(NAIPTileIndex.NAIP_INDEX_BLOB_ROOT + fn, os.path.join(base_path, fn), verbose)

        self.base_path = base_path
        self.tile_rtree = rtree.index.Index(base_path + "/tile_index")
        self.tile_index = pickle.load(open(base_path  + "/tiles.p", "rb"))

    def lookup_point(self, lat, lon):
        '''Given a lat/lon coordinate pair, return the list of NAIP tiles that *contain* that point.
        
        Args:
            lat (float): Latitude in EPSG:4326
            lon (float): Longitude in EPSG:4326

        Returns:
            intersected_files (list): A list of URLs of NAIP tiles that *contain* the given (`lat`, `lon`) point
        
        Raises:
            IndexError: Raised if no tile within the index contains the given (`lat`, `lon`) point
        '''

        point = shapely.geometry.Point(float(lon), float(lat))
        geom = shapely.geometry.mapping(point)

        return self.lookup_geom(geom)

    def lookup_geom(self, geom):
        '''Given a GeoJSON geometry, return the list of NAIP tiles that *contain* that feature.
        
        Args:
            geom (dict): A GeoJSON geometry in EPSG:4326

        Returns:
            intersected_files (list): A list of URLs of NAIP tiles that *contain* the given `geom`
        
        Raises:
            IndexError: Raised if no tile within the index fully contains the given `geom`
        '''
        shape = shapely.geometry.shape(geom)
        intersected_indices = list(self.tile_rtree.intersection(shape.bounds))

        intersected_files = []
        tile_intersection = False

        for idx in intersected_indices:
            intersected_file = self.tile_index[idx][0]
            intersected_geom = self.tile_index[idx][1]
            if intersected_geom.contains(shape):
                tile_intersection = True
                intersected_files.append(NAIPTileIndex.NAIP_BLOB_ROOT + intersected_file)

        if not tile_intersection and len(intersected_indices) > 0:
            raise IndexError("There are overlaps with tile index, but no tile contains the shape")
        elif len(intersected_files) <= 0:
            raise IndexError("No tile intersections")
        else:
            return intersected_files

def download_url(url, output_fn, verbose=False):
    '''Download a URL to file.

        Args:
            url (str): URL of file to download
            output_fn (str): Filename to save (importantly -- not the directory to save the file to)
            verbose (bool): Whether to print how the download is going

        Returns:
            output_fn (str): Return `output_fn` as is
    '''

    if verbose:
        print("Downloading file {} to {}".format(os.path.basename(url) ,output_fn), end="")

    urllib.request.urlretrieve(url, output_fn)  
    assert(os.path.isfile(output_fn))

    if verbose:
        nBytes = os.path.getsize(output_fn)
        print("...done, {} bytes.".format(nBytes))

    return output_fn


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as base_dir:
        naip_index = NAIPTileIndex(base_dir, verbose=True)

        # Test 1
        lat, lon = 47.644184, -122.139152 # on Microsoft's Redmond campus
        tiles = naip_index.lookup_point(lat, lon)
        assert "https://naipblobs.blob.core.windows.net/naip/v002/wa/2011/wa_100cm_2011/47122/m_4712223_se_10_1_20110826.tif" in tiles

        # Test 2
        lat, lon = -122.139152, 47.644184 # Swapped lat, lon points from the previous example
        try:
            naip_index.lookup_point(lat, lon)
            assert False # We expect the previous line to throw an exception
        except IndexError as e:
            pass

        # Test 3
        lat, lon = 44.606377, -132.860376 # Pacific ocean
        try:
            naip_index.lookup_point(lat, lon)
            assert False # We expect the previous line to throw an exception
        except IndexError as e:
            pass

        # Test 4
        geom = {"type":"Polygon","coordinates":[[[-75.406171,38.451649],[-75.406267,38.468741],[-75.423777,38.468678],[-75.423677,38.451587],[-75.406171,38.451649]]]} # a rectangle on the Delmarva peninsula
        tiles = naip_index.lookup_geom(geom)
        assert "https://naipblobs.blob.core.windows.net/naip/v002/de/2011/de_100cm_2011/38075/m_3807537_ne_18_1_20110602.tif" in tiles
