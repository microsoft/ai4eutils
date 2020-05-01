# 
# ai4e_web_utils.py
#
# Functions for interacting with http requests
#

#%% Imports

import os

# pip install progressbar2, not progressbar
import progressbar
import urllib
import tempfile


#%% Functions

class DownloadProgressBar():
    """
    Console progress indicator for downloads.
    
    stackoverflow.com/questions/37748105/how-to-use-progressbar-module-with-urlretrieve
    """
    
    def __init__(self):
        self.pbar = None

    def __call__(self, block_num, block_size, total_size):
        if not self.pbar:
            self.pbar = progressbar.ProgressBar(max_value=total_size)
            self.pbar.start()
            
        downloaded = block_num * block_size
        if downloaded < total_size:
            self.pbar.update(downloaded)
        else:
            self.pbar.finish()
            
            
def download_url(url, destination_filename=None, progress_updater=None, 
                 force_download=False, output_dir=None, verbose=False):
    """
    Download a URL, optionally downloading to a temporary file
    """

    # if progress_updater is None:
    #    progress_updater = DownloadProgressBar()
        
    # This is not intended to guarantee uniqueness, we just know it happens to guarantee
    # uniqueness for this application.
    if destination_filename is None:
    
        if output_dir is None:
            output_dir = os.path.join(tempfile.gettempdir(),'ai4e')
            os.makedirs(output_dir,exist_ok=True)
        
        url_as_filename = url.replace('://', '_').replace('.', '_').replace('/', '_')
        destination_filename = \
            os.path.join(output_dir,url_as_filename)
            
    if (not force_download) and (os.path.isfile(destination_filename)):
        if verbose:
            print('Bypassing download of already-downloaded file {}'.format(os.path.basename(url)))
        return destination_filename
    
    if verbose:
        print('Downloading file {}'.format(os.path.basename(url)),end='')
    urllib.request.urlretrieve(url, destination_filename, progress_updater)  
    assert(os.path.isfile(destination_filename))
    nBytes = os.path.getsize(destination_filename)
    if verbose:
        print('...done, {} bytes.'.format(nBytes))
    
    return destination_filename
