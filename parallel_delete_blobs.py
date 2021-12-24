#
# parallel_delete_blobs.py
#
# Given a list of blobs to delete from a single container, 
# execute those delete operations on parallel processes (default) or threads.
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
execute_deletions = True
use_threads = False

n_threads = 100
n_print = 5000
verify_existence = False
blobs_to_skip = 0

# verbose = (debug_max_files > 0)
sleep_time_after_deletion = 0.001

# In blocks, not items
max_queue_size = n_threads*4
producer_block_size = 500


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


#%% Load credentials and create client objects

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
    

#%% Blob functions

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


def delete_blob(container_client, blob_path):
    
    if verify_existence:
        
        if not blob_exists(container_client,blob_path):
           print('Warning: {} does not exist'.format(blob_path))
           return

    if not execute_deletions:
        
        if verbose:
            print('Not deleting {}'.format(blob_path))        
        return
    
    try:

        if verbose:
            print('Deleting {}'.format(blob_path))            
        blob_client = container_client.get_blob_client(blob_path)    
        blob_client.delete_blob()
        
    except Exception as e:

        if verbose:
            s = str(e)
            if 'BlobNotFound' in s:
                print('{} does not exist'.format(blob_path))
            else:
                print('Error deleting {}: {}'.format(blob_path,s))
    
    if sleep_time_after_deletion > 0:
        time.sleep(sleep_time_after_deletion)
        

#%% Producer/consumer functions

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
    
    
def consumer_func(q,container_client):
    
    if verbose:
        print('Consumer starting')
    
    while True:
        block = q.get()
        if verbose:
            print('De-queuing {} paths'.format(len(block)))
        for blob_path in block:
            delete_blob(container_client,blob_path)
        q.task_done()


#%% Thread-based implementation
        
from threading import Thread

def parallel_delete_blobs_threads(container_client,input_file):
    
    q = Queue(max_queue_size)

    producer = Thread(target=producer_func,args=(q,input_file,))
    producer.daemon = False
    producer.start()
    
    for i in range(n_threads):
        if verbose:
            print('Starting thread {}'.format(i))
        t = Thread(target=consumer_func,args=(q,container_client,))
        t.daemon = True
        t.start()
        
    producer.join()
    print('Producer finished')
    q.join()
    print('Queue joined')
    

#%% Process-based implementation

from multiprocessing import Process

def parallel_delete_blobs_processes(container_client,input_file):
    
    q = multiprocessing.JoinableQueue(max_queue_size)
    
    producer = Thread(target=producer_func,args=(q,input_file,))
    producer.daemon = False
    producer.start()
    
    for i in range(n_threads):
        if verbose:
            print('Starting process {}'.format(i))
        p = Process(target=consumer_func,args=(q,container_client,))
        p.daemon = True
        p.start()
        
    producer.join()
    print('Producer finished')
    q.join()
    print('Queue joined')


#%% Main function    
        
def parallel_delete_blobs(container_client,input_file):

    pinit(Counter(-1))
    if use_threads:
        parallel_delete_blobs_threads(container_client,input_file)
    else:
        parallel_delete_blobs_processes(container_client,input_file)
    
       
#%% Interactive driver

if False:
    
    #%%
    
    account_name = 'ai4epublictestdata'
    container_name = 'ai4eutils'
    sas_token_file = os.path.expanduser('~/tokens/ai4epublictestdata-ai4eutils-sas.txt')
    input_file = r'c:\temp\test-blob-deletion.txt'
    
    container_client = get_container_client(account_name,container_name,sas_token_file)
    parallel_delete_blobs(container_client,input_file)

    #%%

    # python parallel_delete_blobs.py ai4edevshare ai4edebug "c:/users/dan/tokens/ai4edevshare_ai4edebug_sas_tokens.txt" "c:\temp\test_deletions.txt"
    
#%% Command-line driver
    
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
      
    parser = argparse.ArgumentParser(
        description='Delete blobs in a container from a list of files')
    
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
        help='List of blobs to delete')
    
    if len(sys.argv[1:]) == 0:
        parser.print_help()
        parser.exit()

    args = parser.parse_args()
    
    assert(os.path.isfile(args.input_file)), 'Could not find file {}'.format(args.iput_file)
    
    container_client = get_container_client(args.account_name,args.container_name,args.sas_token_file)
    parallel_delete_blobs(container_client,args.input_file)
    