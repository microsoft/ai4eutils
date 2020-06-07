#
# ai4e_azure_utils.py
#
# Miscellaneous Azure utilities
#

import json
import re
from azure.storage.blob._models import BlobPrefix
from azure.storage.blob import BlobServiceClient

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
                # print('F: ' + prefix + short_name)
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


#%% Blob enumeration

def concatenate_json_string_lists(input_files,output_file=None):
    """
    Given several files that contain json-formatted lists of strings (typically filenames),
    concatenate them into one new file.
    """
    output_list = []
    for fn in input_files:
        file_list = json.load(open(fn)) 
        output_list.extend(file_list)
    if output_file is not None:
        s = json.dumps(output_list,indent=1)
        with open(output_file,'w') as f:
            f.write(s)
    return output_list

        
def write_list_to_file(output_file,strings):
    """
    Writes a list of strings to file, either .json or text depending on extension
    """
    if output_file.endswith('.json'):
        s = json.dumps(strings,indent=1)
        with open(output_file,'w') as f:
            f.write(s)
    else:
        with open(output_file,'w') as f:
            for fn in strings:
                f.write(fn + '\n')
                
    # print('Finished writing list {}'.format(output_file))
    
   
def read_list_from_file(filename):
    """
    Reads a json-formatted list of strings from *filename*
    """
    assert filename.endswith('.json')
    file_list = json.load(open(filename))             
    assert isinstance(file_list,list)
    for s in file_list:
        assert isinstance(s,str)
    return file_list
    

def account_name_to_url(account_name):
    storage_account_url_blob = 'https://' + account_name + '.blob.core.windows.net'
    return storage_account_url_blob


def copy_file_to_blob(account_name,sas_token,container_name,
                      local_path,remote_path):
    """
    Copies a local file to blob storage
    """
    blob_service_client = BlobServiceClient(account_url=account_name_to_url(account_name), 
                                            credential=sas_token)
    
    container_client = blob_service_client.get_container_client(container_name)

    with open(local_path, 'rb') as data:
        container_client.upload_blob(remote_path, data)
    
    
def enumerate_blobs(account_name,sas_token,container_name,
                    rmatch=None,prefix=None,max_blobs=None):
    """
    Enumerates blobs in a container, optionally filtering with a regex
    
    Using the prefix parameter is faster than using a regex starting with ^
    
    sas_token should start with st=
    """
    
    folder_string = '{}/{}'.format(account_name,container_name)
    if prefix is not None:
        folder_string += '/{}'.format(prefix)
    if rmatch is not None:
        folder_string += ' (matching {})'.format(rmatch)
    print('Enumerating blobs from {}'.format(folder_string))
        
    blob_service_client = BlobServiceClient(account_url=account_name_to_url(account_name), 
                                            credential=sas_token)
    
    container_client = blob_service_client.get_container_client(container_name)
    
    generator = container_client.list_blobs(name_starts_with=prefix)
    matched_blobs = []

    i_blob = 0
    for blob in generator:
        blob_name = blob.name
        if rmatch is not None:
            m = re.match(rmatch,blob_name)
            if m is None:
                continue
        matched_blobs.append(blob.name)
        i_blob += 1
        if (i_blob % 1000) == 0:
            print('.',end='')
        if (i_blob % 50000) == 0:
            print('{} blobs enumerated ({} matches)'.format(i_blob,len(matched_blobs)))
        
        if (max_blobs is not None) and (i_blob >= max_blobs):
            print('Terminating enumeration after {} blobs'.format(max_blobs))
            break
        
    print('Enumerated {} matching blobs (of {} total) from {}/{}'.format(len(matched_blobs),
          i_blob,account_name,container_name))

    return matched_blobs


def enumerate_blobs_to_file(output_file,account_name,sas_token,container_name,account_key=None,rmatch=None,prefix=None,max_blobs=None):
    """
    Enumerates to a .json string if output_file ends in ".json", otherwise enumerates to a 
    newline-delimited list.
    
    See enumerate_blobs for parameter information.
    """        
    
    matched_blobs = enumerate_blobs(account_name=account_name,
                                    sas_token=sas_token,
                                    container_name=container_name,
                                    rmatch=rmatch,
                                    prefix=prefix,
                                    max_blobs=max_blobs)
    
    write_list_to_file(output_file,matched_blobs)
    return matched_blobs

