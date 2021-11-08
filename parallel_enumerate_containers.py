#
# parallel_enumerate_containers.py
#
# Enumerate all blobs in all containers in a storage account, using one
# thread/process per container.
#
# Creates one output file per container, with each row formatted as [name] \t [size] \t [access-tier].
#

#%% Constants and imports

import os
import sys
import time
import argparse
import multiprocessing

from azure.storage.blob import BlobServiceClient

# Assumes that the parent folder of the ai4eutils repo is on the PYTHONPATH
#
# import sys; sys.path.append('/home/dmorris/git/ai4eutils')
# export PYTHONPATH="$PYTHONPATH:/home/dmorris/git/ai4eutils"
import path_utils

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
get_sizes = True
get_access_tiers = True


#%% List containers in a storage account

def list_containers(account_name,sas_token,required_string=None):
    
    # Break URL into URL and token
    if not sas_token.startswith('?'):
        sas_token = '?' + sas_token

    storage_account_url_blob = 'https://' + account_name + '.blob.core.windows.net'
    
    blob_service_client = BlobServiceClient(account_url=storage_account_url_blob, 
                                            credential=sas_token)

    container_iter = blob_service_client.list_containers(include_metadata=False)
    containers = []
    
    for container in container_iter:    
        name = container['name']
        if required_string is None or required_string in name:
            containers.append(name)
        elif required_string is not None:
            print('Skipping container {}'.format(name))
    
    print('Enumerated {} containers:'.format(len(containers)))
    
    print(containers)

    return containers
    

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

def list_blobs_in_container(container_name,account_name,sas_token,output_folder,prefix=None):
    
    if not sas_token.startswith('?'):
        sas_token = '?' + sas_token

    storage_account_url_blob = 'https://' + account_name + '.blob.core.windows.net'
    
    # prefix = prefixes[0]; print(prefix)
    
    print('Starting enumeration for container {}'.format(container_name))
    
    # Open the output file
    fn = path_utils.clean_filename(container_name) + '.log'
    output_file = os.path.join(output_folder,fn)
    
    # Create the container
    blob_service_client = BlobServiceClient(
        account_url=storage_account_url_blob, 
                                        credential=sas_token)

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

    print('Finished enumerating {} blobs for container {}'.format(
        i_blob,container_name))


#%% Thread-based implementation
        
from threading import Thread

def list_blobs_threads(account_name,sas_token,containers,output_folder):
    
    all_threads = []
    
    for container_name in containers:
        # print('Starting thread for prefix {}'.format(s))
        t = Thread(name=container_name,target=list_blobs_in_container,
                   args=(container_name,account_name,sas_token,output_folder,))
        t.daemon = False
        t.start()
        all_threads.append(t)
        
    for t in all_threads:
        t.join()
        # print('Thread {} finished'.format(t.name))
    
    
#%% Process-based implementation

from multiprocessing import Process

def list_blobs_processes(account_name,sas_token,containers,output_folder):
    
    all_processes = []
    
    for container_name in containers:
        # print('Starting process for prefix {}'.format(s))
        p = Process(name=container_name,target=list_blobs_in_container,
                    args=(container_name,account_name,sas_token,output_folder,))
        p.daemon = False
        p.start()
        all_processes.append(p)
        
    for p in all_processes:
        p.join()
        # print('Process {} finished'.format(p.name))
    

#%% Main function    
        
def list_blobs_in_all_containers(account_name,sas_token,output_folder):

    containers = list_containers(account_name,sas_token)
    os.makedirs(output_folder,exist_ok=True)
    
    pinit(Counter(-1))
    if use_threads:
        list_blobs_threads(account_name,sas_token,containers,output_folder)
    else:
        list_blobs_processes(account_name,sas_token,containers,output_folder)
    
       
#%% Command-line driver
    
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
      
    parser = argparse.ArgumentParser(
        description='Enumerate blobs in all containers in a storage account, using one thread/process per container.')
    
    parser.add_argument(
        'account_name',
        help='Name of the target storage account')
    parser.add_argument(
        'sas_token',
        help='Read-/list-capable, account-level SAS token to the target storage account')
    parser.add_argument(
        'output_folder',
        help='Output folder; one flat file per container will be written to this folder')
    
    if len(sys.argv[1:]) == 0:
        parser.print_help()
        parser.exit()

    args = parser.parse_args()
    
    list_blobs_in_all_containers(args.account_name,args.sas_token,args.output_folder)
    

#%% Interactive driver

if False:

    pass

    #%%

    account_name = ''
    sas_token = '?sv='
    output_folder = r'c:\temp\enumeration-test'    
    list_blobs_in_all_containers(args.account_name,args.sas_token,args.output_folder)
