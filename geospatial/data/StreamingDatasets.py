import sys

import numpy as np

import rasterio
from rasterio.windows import Window
from rasterio.errors import RasterioIOError

import torch 
from torchvision import transforms
from torch.utils.data.dataset import IterableDataset

class StreamingGeospatialDataset(IterableDataset):
    
    def __init__(self, imagery_fns, label_fns=None, chip_size=256, num_chips_per_tile=200, windowed_sampling=False, transform=None, verbose=False):
        """A torch Dataset for randomly sampling chips from a list of tiles. When used in conjunction with a DataLoader that has `num_workers>1` this Dataset will assign each worker to sample chips from disjoint sets of tiles.

        Args:
            imagery_fns: A list of filenames (or web addresses -- anything that `rasterio.open()` can read) pointing to imagery tiles.
            label_fns: A list of filenames of the same size as `imagery_fns` pointing to label mask tiles or `None` if the Dataset should operate in "imagery only mode". Note that we expect `imagery_fns[i]` and `label_fns[i]` to have the same dimension and coordinate system.
            chip_size: Desired size of chips (in pixels).
            num_chips_per_tile: Desired number of chips to sample for each tile.
            windowed_sampling: Flag indicating whether we should sample each chip with a read using `rasterio.windows.Window` or whether we should read the whole tile into memory, then sample chips.
            transform: The torchvision.transform object to apply to each chip.
            verbose: If `False` we will be quiet.
        """

        if label_fns is None:
            self.fns = imagery_fns
            self.use_labels = False
        else:
            self.fns = list(zip(imagery_fns, label_fns)) 
            self.use_labels = True

        self.chip_size = chip_size
        self.num_chips_per_tile = num_chips_per_tile
        self.windowed_sampling = windowed_sampling
        
        self.transform = transform
        self.verbose = verbose
        
        if self.verbose:
            print("Constructed StreamingGeospatialDataset")
        
    def stream_tile_fns(self):    
        worker_info = torch.utils.data.get_worker_info()
        if worker_info is None: # In this case we are not loading through a DataLoader with multiple workers
            worker_id = 0
            num_workers = 1
        else:
            worker_id = worker_info.id
            num_workers = worker_info.num_workers
        
        # We only want to shuffle the order we traverse the files if we are the first worker (else, every worker will shuffle the files...)
        if worker_id == 0:
            np.random.shuffle(self.fns) # in place
        # NOTE: A warning, when different workers are created they will all have the same numpy random seed, however will have different torch random seeds. If you want to use numpy random functions, seed appropriately.
        #seed = torch.randint(low=0,high=2**32-1,size=(1,)).item()
        #np.random.seed(seed) # when different workers spawn, they have the same numpy random seed...

        if self.verbose:
            print("Creating a filename stream for worker %d" % (worker_id))
        
        N = len(self.fns)
        num_files_per_worker = int(np.ceil(N / num_workers))
        lower_idx = worker_id * num_files_per_worker
        upper_idx = min(N, (worker_id+1) * num_files_per_worker)
        for idx in range(lower_idx, upper_idx):
            
            label_fn = None
            if self.use_labels:
                img_fn, label_fn = self.fns[idx]
            else:
                img_fn = self.fns[idx]

            if self.verbose:
                print("Worker %d, yielding file %d" % (worker_id, idx))
            
            yield (img_fn, label_fn)
            
    def stream_chips(self):
        for img_fn, label_fn in self.stream_tile_fns():
            
            # Open file pointers
            img_fp = rasterio.open(img_fn, "r")
            label_fp = rasterio.open(label_fn, "r") if self.use_labels else None

            height, width = img_fp.shape                
            if self.use_labels: # garuntee that our label mask has the same dimensions as our imagery
                t_height, t_width = label_fp.shape
                assert height == t_height and width == t_width  
            
            try:
                # If we aren't in windowed sampling mode then we should read the entire tile up front
                if not self.windowed_sampling:
                    img_data = np.rollaxis(img_fp.read(), 0, 3)
                    if self.use_labels:
                        label_data = label_fp.read().squeeze() # assume the label geotiff has a single channel


                for i in range(self.num_chips_per_tile):
                    # Select the top left pixel of our chip randomly
                    x = np.random.randint(0, width-self.chip_size)
                    y = np.random.randint(0, height-self.chip_size)

                    if self.windowed_sampling:
                        img = np.rollaxis(img_fp.read(window=Window(x, y, self.chip_size, self.chip_size)), 0, 3)
                        if self.use_labels:
                            labels = label_fp.read(window=Window(x, y, self.chip_size, self.chip_size)).squeeze()
                    else:
                        img = img_data[y:y+self.chip_size, x:x+self.chip_size, :]
                        if self.use_labels:
                            labels = label_data[y:y+self.chip_size, x:x+self.chip_size]

                    # TODO: check for nodata and throw away the chip if necessary. Not sure how to do this in a dataset independent way.
                    
                    if self.use_labels:
                        labels = transforms.ToTensor()(labels).squeeze()

                    if self.transform is not None:
                        img = self.transform(img)
                    
                    if self.use_labels:
                        yield img, labels
                    else:
                        yield img
            except RasterioIOError as e: # NOTE(caleb): I put this here to catch weird errors that I was seeing occasionally when trying to read from COGS - I don't remember the details though
                print("Reading %s failed, skipping..." % (fn))
            
            # Close file pointers
            img_fp.close()
            if self.use_labels:
                label_fp.close()
                    
    def __iter__(self):
        if self.verbose:
            print("Creating a new StreamingGeospatialDataset iterator")
        return iter(self.stream_chips())
