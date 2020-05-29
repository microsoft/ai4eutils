#
# ai4e_azure_utils.py
#
# Miscellaneous Azure utilities
#

from azure.storage.blob._models import BlobPrefix

# Based on:
#
# https://github.com/Azure/azure-sdk-for-python/blob/master/sdk/storage/azure-storage-blob/samples/blob_samples_walk_blob_hierarchy.py
def walk_container(container_client, max_depth=-1, prefix='', 
                   store_folders=True, store_blobs=True, debug_max_items=-1):
    """
    Recursively walk folders in the ContainerClient object *container_client*
    """
    
    depth =  1
    
    def walk_blob_hierarchy(prefix=prefix, folders=None, blobs=None):
    
        if folders is None:
            folders = []
        if blobs is None:
            blobs = []
                    
        nonlocal depth
        
        if max_depth > 0 and depth > max_depth:
            return folders, blobs
                
        for item in container_client.walk_blobs(name_starts_with=prefix):
            short_name = item.name[len(prefix):]
            if isinstance(item, BlobPrefix):
                print('F: ' + prefix + short_name)
                if store_folders:
                    folders.append(prefix + short_name)
                depth += 1
                walk_blob_hierarchy(prefix=item.name,folders=folders,blobs=blobs)
                if (debug_max_items > 0) and (len(folders)+len(blobs) > debug_max_items):
                    return folders, blobs        
                depth -= 1
            else:
                if store_blobs:
                    blobs.append(prefix + short_name)
                
        return folders,blobs
                
    folders,blobs = walk_blob_hierarchy()
    
    assert(all([s.endswith('/') for s in folders]))
    folders = [s.strip('/') for s in folders]

    return folders,blobs
    

def list_top_level_blob_folders(container_client):
    """
    List all top-level folders in the ContainerClient object *container_client*
    """
    top_level_folders,_ = walk_container(container_client,max_depth=1,store_blobs=False)
    return top_level_folders


