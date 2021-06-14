# Best practices for using `rasterio`

This is based on tests from [here](https://github.com/pangeo-data/cog-best-practices). If you are using `rasterio` to load data over HTTP(S), add the following to your script before you use `rasterio`:
```
import os
# Some tricks to make rasterio faster when using vsicurl -- see https://github.com/pangeo-data/cog-best-practices
RASTERIO_BEST_PRACTICES = dict(
    CURL_CA_BUNDLE='/etc/ssl/certs/ca-certificates.crt',
    GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',
    AWS_NO_SIGN_REQUEST='YES',
    GDAL_MAX_RAW_BLOCK_CACHE_SIZE='200000000',
    GDAL_SWATH_SIZE='200000000',
    VSI_CURL_CACHE_SIZE='200000000'
)
os.environ.update(RASTERIO_BEST_PRACTICES)
```
