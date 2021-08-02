#
# parallel_enumerate_blobs.py
#
# Read a list of prefixes from a text file, then enumerates a blob
# container, parallelizing across those prefixes (on thread/process per prefix).
#
# Creates one output file per prefix, which we typically just cat together 
# after the fact.
#
# In practice, the prefix list is generated using enumerate_folders_at_depth.py,
# but it's just a flat list, so you can generate it however like.
#
# Uses one thread/process per prefix.
#
# Optionally reads the size for each blob, which it separates from the filename
# in the output files with \t .
#

#%% Constants and imports

import os
import sys
import time
import argparse
import multiprocessing
import humanfriendly

from azure.storage.blob import BlobServiceClient
from tqdm import tqdm

# Assumes that the parent folder of the ai4eutils repo is on the PYTHONPATH
#
# import sys; sys.path.append('/home/dmorris/git/ai4eutils')
# export PYTHONPATH="$PYTHONPATH:/home/dmorris/git/ai4eutils"
import path_utils
from ai4e_azure_utils import sas_blob_utils

n_blobs_per_page = 5000
n_print = 10000

# Toggles between threads (True) and processes (False)
use_threads = False
verbose = False

# This is a bit of a hack, but it has a *massive* impact on performance and on
# minimizing storage-account-level throttling.  So... don't set this to zero.
sleep_time_per_page = 0.001

# Limit the number of files to enumerate per thread; used only for debugging
debug_max_files = -1


#%% Read prefix list

def read_prefix_list(prefix_list_file):
    
    with open(prefix_list_file,'r') as f:
        prefixes = f.readlines()
    prefixes = [s.strip() for s in prefixes]
    print('Read {} prefixes from {}'.format(len(prefixes),
                                            prefix_list_file))
    return prefixes
    

#%% Multiprocessing init

def pinit(c):
    
    global cnt
    cnt = c
    
class Counter(object):
    
    def __init__(self, total):
        # 'i' means integer
        self.val = multiprocessing.Value('i', 0)
        self.total = multiprocessing.Value('i', total)
        self.last_print = multiprocessing.Value('i', 0)

    def increment(self, n=1):
        b_print = False
        with self.val.get_lock():
            self.val.value += n
            if ((self.val.value - self.last_print.value) >= n_print):
                self.last_print.value = self.val.value
                b_print = True           
        if b_print:
            total_string = ''
            if self.total.value > 0:
                 total_string = ' of {}'.format(self.total.value)
            print('{}: iteration {}{}'.format(time.strftime("%Y-%m-%d %H:%M:%S"), 
                                                                 self.val.value,total_string),flush=True)
    @property
    def value(self):
        return self.val.value
    def last_print_value(self):
        return self.last_print.value
    
pinit(Counter(-1))


#%% Enumeration function

def enumerate_prefix(prefix,sas_url,output_folder,get_sizes=False,get_access_tiers=False):
    
    account_name = sas_blob_utils.get_account_from_uri(sas_url)
    container_name = sas_blob_utils.get_container_from_uri(sas_url)
    ro_sas_token = sas_blob_utils.get_sas_token_from_uri(sas_url)
    
    if ro_sas_token is not None:
        assert not ro_sas_token.startswith('?')
        ro_sas_token = '?' + ro_sas_token

    storage_account_url_blob = 'https://' + account_name + '.blob.core.windows.net'
    
    # prefix = prefixes[0]; print(prefix)
    
    print('Starting enumeration for prefix {}'.format(prefix))
    
    # Open the output file
    fn = path_utils.clean_filename(prefix)
    output_file = os.path.join(output_folder,fn)
    
    # Create the container
    blob_service_client = BlobServiceClient(
        account_url=storage_account_url_blob, 
                                        credential=ro_sas_token)

    container_client = blob_service_client.get_container_client(container_name)
    
    # Enumerate
    with open(output_file,'w') as output_f:
    
        continuation_token = ''
        hit_debug_limit = False
        i_blob = 0
        
        while (continuation_token is not None) and (not hit_debug_limit):
            
            blobs_iter = container_client.list_blobs(
                name_starts_with=prefix,
                results_per_page=n_blobs_per_page).by_page(
                continuation_token=continuation_token)
            
            # This is a paged list of BlobProperties objects
            blobs = next(blobs_iter)
            
            n_blobs_this_page = 0
            
            for blob in blobs:
                i_blob += 1
                n_blobs_this_page += 1
                if (debug_max_files > 0) and (i_blob > debug_max_files):
                    print('Hit debug path limit for prefix {}'.format(prefix))
                    i_blob -= 1
                    hit_debug_limit = True
                    break
                else:                    
                    size_string = ''
                    if get_sizes:
                        size_string = '\t' + str(blob.size)
                    tier_string = ''
                    if get_access_tiers:
                        s = blob.blob_tier                        
                        # This typically indicates a GPv1 Storage Account, with no tiering support
                        if s is None:
                            s = 'Unknown'
                        tier_string = '\t' + s
                    output_f.write(blob.name + size_string + tier_string + '\n')
                    
            # print('Enumerated {} blobs'.format(n_blobs_this_page))
            cnt.increment(n=n_blobs_this_page)
            
            continuation_token = blobs_iter.continuation_token
            
            if sleep_time_per_page > 0:
                time.sleep(sleep_time_per_page)
                
        # ...while we're enumerating                
            
    # ...with open(output_file)

    print('Finished enumerating {} blobs for prefix {}'.format(
        i_blob,prefix))


#%% Thread-based implementation
        
from threading import Thread

def enumerate_blobs_threads(prefixes,sas_url,output_folder,
                            get_sizes=False,get_access_tiers=False):
    
    all_threads = []
    
    for s in prefixes:
        # print('Starting thread for prefix {}'.format(s))
        t = Thread(name=s,target=enumerate_prefix,args=(s,sas_url,output_folder,
                                                        get_sizes,get_access_tiers,))
        t.daemon = False
        t.start()
        all_threads.append(t)
        
    for t in all_threads:
        t.join()
        # print('Thread {} finished'.format(t.name))
    
    
#%% Process-based implementation

from multiprocessing import Process

def enumerate_blobs_processes(prefixes,sas_url,output_folder,
                              get_sizes=False,get_access_tiers=False):
    
    all_processes = []
        
    for s in prefixes:
        # print('Starting process for prefix {}'.format(s))
        p = Process(name=s,target=enumerate_prefix,args=(s,sas_url,output_folder,
                                                         get_sizes,get_access_tiers,))
        p.daemon = False
        p.start()
        all_processes.append(p)
        
    for p in all_processes:
        p.join()
        # print('Process {} finished'.format(p.name))
    

#%% Main function    
        
def enumerate_blobs(prefix_list_file,sas_url,output_folder,get_sizes=False,get_access_tiers=False):

    assert(os.path.isfile(prefix_list_file))
    os.makedirs(output_folder,exist_ok=True)
    
    pinit(Counter(-1))
    prefixes = read_prefix_list(prefix_list_file)
    if use_threads:
        enumerate_blobs_threads(prefixes,sas_url,output_folder,get_sizes,get_access_tiers)
    else:
        enumerate_blobs_processes(prefixes,sas_url,output_folder,get_sizes,get_access_tiers)
    

#%% Test driver

if False:
    
    #%%
    
    prefixes = set()
    
    # Generate test data
    test_data_folder = r'C:\temp\test-data'
    n_files = 100
    for i_file in range(0,n_files):
        fname = 'file_' + str(i_file).zfill(4) + '.txt'
        prefixes.add(fname[0:8])
        filename = os.path.join(test_data_folder,fname)
        with open(filename,'w') as f:
            f.write('This is a sample file.')
    
    with open(os.path.join(test_data_folder,'prefixes.txt'),'w') as f:
        prefixes = list(prefixes)
        prefixes.sort()
        for s in prefixes:
            f.write(s + '\n')
        
    #%%
    
    prefix_list_file = r'c:\temp\test-data\prefixes.txt'
    sas_url = 'https://ai4epublictestdata.blob.core.windows.net/ai4eutils'
    output_folder = r'c:\temp\test-data\enumeration'
    get_sizes = True
    get_access_tiers = True
    use_threads = True
    if False:
        prefixes = read_prefix_list(prefix_list_file)
        prefix = prefixes[0]
    enumerate_blobs(prefix_list_file,sas_url,output_folder,get_sizes,get_access_tiers)
    
    # python parallel_enumerate_blobs.py "c:\temp\prefixes.txt" "https://lilablobssc.blob.core.windows.net/nacti-unzipped?sv=" "c:\temp\enumeration_test" --get_sizes
    

#%% Command-line driver
    
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
      
    parser = argparse.ArgumentParser(
        description='Enumerate blobs in a container, using one thread/process per prefix from a specified list of prefixes.')
    
    parser.add_argument(
        'prefix_list_file',
        help='Text file containing one prefix per line')
    parser.add_argument(
        'sas_url',
        help='Read-/list-capable, container-level SAS URL to the target container')
    parser.add_argument(
        'output_folder',
        help='Output folder; one flat file per prefix will be written to this folder')
    parser.add_argument(
        '--get_sizes',action='store_true',
        help='Include sizes for each blob in the output files (default: False)')
    parser.add_argument(
        '--get_access_tiers',action='store_true',
        help='Include access tiers for each blob in the output files (default: False)')
    
    if len(sys.argv[1:]) == 0:
        parser.print_help()
        parser.exit()

    args = parser.parse_args()
    
    enumerate_blobs(args.prefix_list_file,args.sas_url,args.output_folder,
                    args.get_sizes,args.get_access_tiers)


#%% Handy functions for working with the output files/folders from this script

# import os; import humanfriendly; from tqdm import tqdm

def parse_filenames_and_sizes(list_file):
    """
    Takes a file with tab-delimited filename/size pairs and returns a 
    filename-->size dict.
    """
    
    filename_to_size = {}
    
    with open(list_file,'r') as f:
        
        for line in f:
            if ('catalog.json' in line) or ('stac.json' in line):
                continue
            tokens = line.split('\t')
            assert len(tokens) == 2
            fn = tokens[0]            
            size_str = tokens[1]
            size = int(size_str)
            if size == 0:
                continue
            filename_to_size[fn] = size
            
        # ...for each line
        
    # ...with open()        

    return filename_to_size


def parse_enumeration_folder(folder_name):
    """
    Takes a folder full of files with tab-delimited filename/size pairs
    and returns a filename-->size dict.
    """
    
    filename_to_size = {}
    enumeration_files = os.listdir(folder_name)
    for fn in enumeration_files:
        filename_to_size.update(parse_filenames_and_sizes(os.path.join(folder_name,fn)))
    return filename_to_size


def summarize_enumeration_folder(folder_name):
    """
    Takes a folder full of files with tab-delimited filename/size pairs
    and prints the number of files and total size.
    """
    
    enumeration_files = os.listdir(folder_name)
    total_files = 0
    total_size = 0
    
    enumeration_files = os.listdir(folder_name)
    for fn in tqdm(enumeration_files):
        filename_to_size  = parse_filenames_and_sizes(os.path.join(folder_name,fn))
        total_files += len(filename_to_size)
        size_this_file = sum(filename_to_size .values())
        assert isinstance(size_this_file,int) and size_this_file > 0
        total_size += size_this_file
    
    print('Read {} files totaling {}'.format(total_files,humanfriendly.format_size(total_size)))
