#
# enumerate_folders_at_depth.py
#
# List folders in a blob container at a particular depth (not including
# folders at shallower depths.
#
# Typically used this to prepare a prefix list for parallel_enumerate_blobs.py.
#

#%% Constants and imports

import os
import sys
import datetime
import argparse

from azure.storage.blob import BlobServiceClient

# Assumes that the parent folder of the ai4eutils repo is on the PYTHONPATH
#
# import sys; sys.path.append('/home/dmorris/git/ai4eutils')
# export PYTHONPATH="$PYTHONPATH:/home/dmorris/git/ai4eutils"
from ai4e_azure_utils import walk_container
from ai4e_azure_utils import sas_blob_utils

account_name = ''
container_name = ''
output_file = ''
ro_sas_token = ''
depth = 3


#%% Main function

def enumerate_folders():
        
    #%% Make sure we're going to be able to write to the output file
    
    os.makedirs(os.path.dirname(output_file),exist_ok=True)
    with open(output_file,'w') as f:
        f.write('')
    
    
    #%% Derived constants
    
    storage_account_url_blob = 'https://' + account_name + '.blob.core.windows.net'
    
    
    #%% Create client handle
    
    blob_service_client = BlobServiceClient(account_url=storage_account_url_blob, 
                                            credential=ro_sas_token)
    
    container_client = blob_service_client.get_container_client(container_name)
    
    
    #%% Enumerate folders
    
    start = datetime.datetime.now()
    
    #
    # Uses ContainerClient.walk_blobs()
    #
    folders, _ = walk_container(
            container_client, max_depth=depth, store_blobs=False)
    
    end = datetime.datetime.now()
    elapsed = end - start
    
    folders = [s for s in folders if s.count('/') == (depth-1)]
    
    print("Enumerated {} folders in {}s".format(len(folders),str(elapsed.seconds)))
    
    for s in folders:
        print(s)
            
        
    #%% Write results to file
    
    folders_with_newlines = [s + '\n' for s in folders]
    
    with open(output_file,'w') as f:
        f.writelines(folders_with_newlines)


#%% Interactive driver
        
if False:

    #%%

    enumerate_folders()        
    

#%% Command-line driver

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
      
    parser = argparse.ArgumentParser(
        description='List folders in a blob container at a particular depth (not including folders at shallower depths.')
    
    parser.add_argument(
        '--sas_url',
        help='Container-level SAS URL (exclusive with account_name, container_name, ro_sas_token)')
    parser.add_argument(
        '--account_name',
        help='Storage account name')
    parser.add_argument(
        '--container_name',
        help='Blob container name')
    parser.add_argument(
        '--ro_sas_token',
        help='Read-only SAS token for the container, with or without a leading ?')
    parser.add_argument(
        'depth',
        type=int,
        help='Recursion depth, must be >= 1.  A depth value of 1 enumerates root-level folders.')
    parser.add_argument(
        'output_file',
        help='Output file')
    
    if len(sys.argv[1:]) == 0:
        parser.print_help()
        parser.exit()

    args = parser.parse_args()
    
    # [URL] and [account,container,token] are mutually exclusive
    if args.sas_url is not None:
        assert args.account_name is None and args.container_name is None and args.ro_sas_token is None
        account_name = sas_blob_utils.get_account_from_uri(args.sas_url)
        container_name = sas_blob_utils.get_container_from_uri(args.sas_url)
        ro_sas_token = sas_blob_utils.get_sas_token_from_uri(args.sas_url)
        assert not ro_sas_token.startswith('?')
        ro_sas_token = '?' + ro_sas_token
    else:
        assert args.account_name is not None and args.container_name is not None and args.ro_sas_token is not None    
        account_name = args.account_name
        container_name = args.container_name
        ro_sas_token = args.ro_sas_token
        if not ro_sas_token.startswith('?'):
            ro_sas_token = '?' + ro_sas_token
        
    depth = args.depth
    assert depth > 0, 'Depth must be >= 1'
    
    output_file = args.output_file
    
    enumerate_folders()
