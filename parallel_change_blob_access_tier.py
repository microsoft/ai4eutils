#
# parallel_change_blob_acces_tier.py
#
# Given a list of blobs in a single container and a specified access
# tier, set each of those blobs to that access tier (parallelizing across
# threads or processes).
#
# Note to self:
#
# The set_standard_blob_tier_blobs supports lists of blobs, but 
# I decided not to use that because a deeper looked shows that it's
# still making a separate http request per blob anyway, and I hit some
# issues trying to make this syntax work.
#

#%% Constants and imports

import multiprocessing
import sys
import os
import time
import argparse

from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError
from queue import Queue        

# Set to -1 to process all files
debug_max_files = -1
verbose = False
execute_changes = True
force_tier_on_inferred_blobs = False
use_threads = False
verify_existence = False
verify_access_tier = True

n_threads = 100
n_print = 5000
blobs_to_skip = 0

sleep_time_after_op = 0.001

# In blocks, not items
max_queue_size = n_threads*4
producer_block_size = 500

# Tiers are case-sensitive; the API expects this case
valid_tiers = set(['Hot','Cool','Archive'])


### Multiprocessing init

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


#%% Support functions

def get_container_client(account_name,container_name,sas_token_file):
    
    storage_account_url_blob = 'https://' + account_name + '.blob.core.windows.net'
    
    assert(os.path.isfile(sas_token_file))
    
    with open(sas_token_file) as f:
        content = f.readlines()
        content = [x.strip() for x in content] 
    
    # Not required
    # ro_sas_token = content[0]
    # assert ro_sas_token.startswith('?')
    
    rw_sas_token = content[1]    
    assert rw_sas_token.startswith('?')
    
    blob_service_client = BlobServiceClient(account_url=storage_account_url_blob, 
                                            credential=rw_sas_token)
    
    container_client = blob_service_client.get_container_client(container_name)

    return container_client
    

def blob_exists(container_client,blob_path):
    """
    Checks whether [blob_path] exists in the blob container [container_client]
    """
    
    blob_client = container_client.get_blob_client(blob_path)
    try:
        blob_client.get_blob_properties()
    except ResourceNotFoundError:
        return False
    return True


def is_iterable(x):
    try:
        iter(x)
    except TypeError:
        return False
    return True


def set_access_tier(container_client, blob_path, access_tier):
    
    assert access_tier in valid_tiers
    
    if verify_existence:
        
        if not blob_exists(container_client,blob_path):
           print('Warning: {} does not exist'.format(blob_path))
           return

    if verify_access_tier:
        
        try:
            
            blob_client = container_client.get_blob_client(blob_path)
            properties = blob_client.get_blob_properties()
            tier = properties['blob_tier']
            
            assert tier is not None, 'Error retrieving blob tier; is this a GPv1 storage account?'
            assert tier in valid_tiers, 'Unrecognized tier {} for {}'.format(
                tier,blob_path)
            
            # If this blob is already at the tier we want it
            if tier == access_tier:
                
                # Force the tier if tier forcing is requested *and* the 
                # tier is inferred, otherwise there's nothing to do here
                force_tier = force_tier_on_inferred_blobs and properties['tier_inferred']
                if not force_tier:
                    print('Skipping {}, already at tier {}'.format(
                        blob_path,access_tier))
                    return
                    
        except Exception as e:
            print('Error verifying access tier for {}: {}'.format(
                blob_path,str(e)))
                
    # ...if we're verifying the access tier
 
    if not execute_changes:
        
        if verbose:
            print('Debug: not setting {} to {}'.format(blob_path,access_tier))
        return
    
    try:

        check_archive_rehydration = (access_tier == 'Archive')
        
        if check_archive_rehydration:
            blob_client = container_client.get_blob_client(blob_path)
            properties = blob_client.get_blob_properties()
            original_tier = properties['blob_tier']
        
        if verbose:
            print('Setting {} to {}'.format(blob_path,access_tier))
            
        container_client.set_standard_blob_tier_blobs(access_tier,blob_path)
        
        # Verify that we've started rehydrating
        if check_archive_rehydration and (original_tier == 'Archive'):
            archive_status = properties['archive_status']
            if 'rehydrate-pending' not in archive_status:
                print('Error: blob {} not re-hydrating'.format(blob_path))
        
    except Exception as e:

        if verbose:
            s = str(e)
            if 'BlobNotFound' in s:
                print('{} does not exist'.format(blob_path))
            else:
                print('Error setting {} to {}: {}'.format(
                    blob_path,access_tier,s))
    
    if sleep_time_after_op > 0:
        time.sleep(sleep_time_after_op)

# ...def set_access_tier(...)        


### Producer/consumer functions

def producer_func(q,input_file):
    
    current_block = []
    
    with open(input_file,'r') as f_in:
        
        for i_line, line in enumerate(f_in):
        
            if blobs_to_skip > 0 and i_line < blobs_to_skip:
                continue
            
            line = line.strip()
            
            if len(line) == 0:
                continue
        
            n_lines = i_line
            if blobs_to_skip > 0:
                n_lines -= blobs_to_skip
            
            if (debug_max_files > 0) and (n_lines >= debug_max_files):
                    print('Hit debug path limit')                    
                    break
            else:
                current_block.append(line)
                if len(current_block) == producer_block_size:
                    if verbose:
                        print('Queuing {} paths'.format(len(current_block)))
                    cnt.increment(n=len(current_block))
                    q.put(current_block)
                    current_block = []        
                    
        # ...for each line in the file
                    
    # ...with open()
    
    print('Queuing {} paths at termination'.format(len(current_block)))
    q.put(current_block)
    
    print('Finished file processing')
    
    
def consumer_func(q,container_client,access_tier):
    
    if verbose:
        print('Consumer starting')
    
    while True:
        try:
            block = q.get()
            if verbose:
                print('De-queuing {} paths'.format(len(block)))
            for blob_path in block:
                set_access_tier(container_client,blob_path,access_tier)
        except Exception as e:
            print('Consumer error: {}'.format(str(e)))
        q.task_done()


### Thread-based implementation
        
from threading import Thread

def parallel_set_access_tier_threads(container_client,input_file,access_tier):
    
    assert os.path.isfile(input_file), 'File {} does not exist'.format(input_file)
    
    q = Queue(max_queue_size)

    producer = Thread(target=producer_func,args=(q,input_file,))
    producer.daemon = False
    producer.start()
    
    for i in range(n_threads):
        if verbose:
            print('Starting thread {}'.format(i))
        t = Thread(target=consumer_func,args=(q,container_client,access_tier,))
        t.daemon = True
        t.start()
        
    producer.join()
    print('Producer finished')
    q.join()
    print('Queue joined')
    

### Process-based implementation

from multiprocessing import Process

def parallel_set_access_tier_processes(container_client,input_file,access_tier):
    
    assert os.path.isfile(input_file), 'File {} does not exist'.format(input_file)
    
    q = multiprocessing.JoinableQueue(max_queue_size)
    
    producer = Thread(target=producer_func,args=(q,input_file,))
    producer.daemon = False
    producer.start()
    
    for i in range(n_threads):
        if verbose:
            print('Starting process {}'.format(i))
        p = Process(target=consumer_func,args=(q,container_client,access_tier,))
        p.daemon = True
        p.start()
        
    producer.join()
    print('Producer finished')
    q.join()
    print('Queue joined')


### Main function    
        
def parallel_set_access_tier(container_client,input_file,access_tier):

    assert os.path.isfile(input_file), 'File {} does not exist'.format(input_file)
    
    pinit(Counter(-1))
    if use_threads:
        parallel_set_access_tier_threads(container_client,input_file,access_tier)
    else:
        parallel_set_access_tier_processes(container_client,input_file,access_tier)
    
       
#%% Interactive driver

if False:
    
    #%%
    
    account_name = 'ai4epublictestdata'
    container_name = 'ai4eutils'
    sas_token_file = os.path.expanduser('~/tokens/ai4epublictestdata-ai4eutils-sas.txt')
    input_file = r'c:\temp\test-access-tier-changes.txt'
    access_tier = 'Archive'
    n_threads = 1
    
    container_client = get_container_client(account_name,container_name,sas_token_file)
    parallel_set_access_tier(container_client,input_file,access_tier)
    
    #%%

    # python parallel_change_blob_access_tier.py ai4epublictestdata ai4eutils "c:/users/dan/tokens/ai4epublictestdata-ai4eutils-sas.txt" "c:\temp\test-access-tier-changes.txt" "Archive"
    
#%% Command-line driver
    
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
      
    parser = argparse.ArgumentParser(
        description='Set a list of blobs in a container to a specific access tier')
    
    parser.add_argument(
        'account_name',
        help='Storage account name')
    parser.add_argument(
        'container_name',
        help='Container name')
    parser.add_argument(
        'sas_token_file',
        help='Credentials file, with a read/write SAS token (starting with "?" on the second line)')
    parser.add_argument(
        'input_file',
        help='List of blobs to change')
    parser.add_argument(
        'access_tier',
        help='Target access tier, one of "Archive", "Hot", or "Cool" (case-sensitive)')
    
    if len(sys.argv[1:]) == 0:
        parser.print_help()
        parser.exit()

    args = parser.parse_args()
    
    assert(os.path.isfile(args.input_file)), 'Could not find file {}'.format(args.iput_file)
    
    assert args.access_tier in valid_tiers, 'Invalid access tier: {}, valid values are Hot, Cool, Archive (case-sensitive)'.format(args.access_tier)
    container_client = get_container_client(args.account_name,args.container_name,args.sas_token_file)
    parallel_set_access_tier(container_client,args.input_file,args.access_tier)
    
