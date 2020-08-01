import sys

import numpy as np

import rasterio
from rasterio.windows import Window
from rasterio.errors import RasterioIOError

import torch 
from torchvision import transforms
from torch.utils.data.dataset import IterableDataset


class ClusterTileStreamingDataset(IterableDataset):
    
    def __init__(self, fns, means, stdevs, cluster_model, patch_size=256, num_patches_per_tile=200, windowed_sampling=False, infinite_sample=False, transform=None, verbose=False):
        self.fns = sorted(list(fns))
        
        # I pass the means and stdevs into the Dataset (instead of through a torchvision.transform) as I want
        # to standardize the images before using the cluster_model. After the image goes through the transform it will
        # be a torch tensor and not useable in the sklearn model.
        self.means = means
        self.stdevs = stdevs
        
        # This is an sklearn.cluster.MiniBatchKMeans model
        self.cluster_model = cluster_model
        self.cluster_model.verbose = False
        
        self.patch_size = patch_size
        self.num_patches_per_tile = num_patches_per_tile
        self.windowed_sampling = windowed_sampling # if windowed_sampling is True, then we will crop chips from the tiles by using
        # rasterio's Window reader, if False, then we will read the entire raster into memory and crop chips by indexing. 
        
        self.infinite = infinite_sample
        self.transform = transform
        self.verbose = verbose
        
        if self.verbose:
            print("Constructed ClusterTileStreamingDataset")
        
    def stream_tile_fns(self):
        # This method is called every time we call something like an `enumerate(dataloader)` (e.g. which happens every epoch).
        # Shuffling the filenames at the beginning of this method will ensure that we don't traverse the same tiles in every worker.        
        seed = torch.randint(low=0,high=2**32-1,size=(1,)).item()
        np.random.seed(seed) # when different workers spawn, they have the same numpy random seed...
        local_fns = list(self.fns)
        np.random.shuffle(local_fns)
        
        worker_info = torch.utils.data.get_worker_info()
        if worker_info is None: # In this case we are not loading through a DataLoader with multiple workers
            worker_id = 0
            num_workers = 1
        else:
            worker_id = worker_info.id
            num_workers = worker_info.num_workers
        
        if self.verbose:
            print("Creating a filename stream for worker %d" % (worker_id))
        
        N = len(local_fns)
        idx = 0
        if self.infinite:
            while True:
                if self.verbose:
                    print("Worker %d, using %s" % (worker_id, local_fns[idx]))
                yield local_fns[idx]
                idx = (idx + 1) % N
        else:
            for fn in local_fns:
                if self.verbose:
                    print("Worker %d, using %s" % (worker_id, fn))
                yield fn
            
    def stream_chips(self):
        for fn in self.stream_tile_fns():
            with rasterio.open(fn, "r") as f:
                height, width = f.shape                
                try:
                    if not self.windowed_sampling:
                        data = np.rollaxis(f.read(), 0, 3)

                    for i in range(self.num_patches_per_tile):
                        x = np.random.randint(0, width-self.patch_size)
                        y = np.random.randint(0, height-self.patch_size)

                        if self.windowed_sampling:
                            img = np.rollaxis(f.read(window=Window(x, y, self.patch_size, self.patch_size)), 0, 3)
                        else:
                            img = data[y:y+self.patch_size, x:x+self.patch_size, :]

                        # Throw away the chip if it has >50% of nodata
                        num_nan = np.sum(np.sum(img == 0, axis=2) == 12)
                        if num_nan / (self.patch_size * self.patch_size) > 0.5:
                            continue
                        img[np.isnan(img)] = 0

                        # standardize
                        img = (img - means) / stdevs
                        img = img.astype(np.float32)

                        # assign each pixel in the input a label based on its cluster index as determined by self.cluster_model
                        targets = img.copy().reshape(-1,12)
                        targets = self.cluster_model.predict(targets)
                        targets = targets.reshape(self.patch_size, self.patch_size)
                        targets = targets.astype(np.int64)
                        targets = transforms.ToTensor()(targets).squeeze()

                        if self.transform is not None:
                            img = self.transform(img)

                        yield img, targets
                except RasterioIOError as e:
                    print("Reading %s failed, skipping..." % (fn))
                    
    def __iter__(self):
        return iter(self.stream_chips())
    
    def __len__(self):
        if self.infinite:
            return sys.maxint
        else:
            return len(self.fns) * self.num_patches_per_tile
