#
# azcopy_upload_test.py
#
# Uploads a file to a storage account using a SAS URL and reports the transfer bandwidth
#

#%% Constants and imports

import argparse
import tempfile
import os
from subprocess import PIPE, run

default_file_size_gb = 8


#%% Functions

def create_sample_file(input_file_path, input_file_size_gb):
    
    assert not os.path.exists(input_file_path), 'Target file {} already exists'.format(input_file_path)
        
    block_size_bytes = 512    
    count = int((int(input_file_size_gb) * (1024*1024*1024) ) / block_size_bytes)

    print('Generating input file at {} ({} GB)'.format(input_file_path,input_file_size_gb))
    str_command = 'dd if=/dev/urandom of={} bs={} count={}'.format(input_file_path, 
        block_size_bytes, count)        
    command = str_command.split(' ')
    run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    print('Created input file at {}'.format(input_file_path))
        
                
def get_bandwidth(sas_url, input_file_path=None, input_file_size_gb=default_file_size_gb, 
    page_blob=False):

    # If we generate a temporary file, we should delete it when we're done
    input_file_is_temporary = False

    if input_file_path is None:
        input_file_is_temporary = True
        default_tmp_dir = tempfile._get_default_tempdir()
        tmp_folder = os.path.join(default_tmp_dir,'azcopy_upload_test')
        os.makedirs(tmp_folder,exist_ok=True)
        temp_name = next(tempfile._get_candidate_names())
        input_file_path = os.path.join(default_tmp_dir,tmp_folder,temp_name)
        
    if not os.path.exists(input_file_path):
        create_sample_file(input_file_path,input_file_size_gb)
    else:
        assert os.path.isfile(input_file_path), '{} is not a valid file name'.format(input_file_path)
    
    str_command = 'azcopy copy {} {} --output-type text'.format(input_file_path, sas_url)    
    if page_blob:
        str_command += ' --blob-type page_blob'
        
    print('Running command:\n{}'.format(str_command))
    print(str_command)

    command = str_command.split(' ')

    result =  run(command, stdout=PIPE, stderr=PIPE, text=True)
    # print('\nResult:\n{}\n'.format(result.stdout))
   
    print('Finished upload') 
    if input_file_is_temporary:
        print('Deleting temporary file')
        os.remove(input_file_path)
        
    std_out = result.stdout.splitlines()
    for line in std_out:
        if 'Elapsed Time' in line:
            elapsed_time_min = line.split(':')[-1].strip()
        if 'TotalBytesTransferred' in line:
            bytes_transferred = line.split(':')[-1].strip()
    
    elapsed_time_in_seconds = (float(elapsed_time_min) * 60)
    megabytes_transferred = (float(bytes_transferred) / (1024*1024))
    
    bandwidth_MBbps =  megabytes_transferred / elapsed_time_in_seconds

    print('Speed in MB/s: {:.3f}'.format(bandwidth_MBbps))
    
    return bandwidth_MBbps


#%% Command-line driver

def is_int(s):
    
    try: 
        int(s)
        return True
    except ValueError:
        return False

def main():
    
    parser = argparse.ArgumentParser()
    
    parser.add_argument('sas_url', type=str, 
                        help='SAS URL for blob container')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--input_file', type=str, 
                        help='Path of file to upload; if omitted, a file will be generated', 
                        default=None)
    group.add_argument('--size', type=str, 
                        help='Size of file in GB (only relevant if --input_file is omitted)', 
                        default=default_file_size_gb)
    parser.add_argument('--page_blob', action='store_true', 
                        help='Specifies whether the target container uses page blobs',
                        default=False)

    args = parser.parse_args()  

    if not is_int(args.size):
        print('Error: input file size (GB) must be an integer')
        parser.exit()
        
    get_bandwidth(args.sas_url, args.input_file, args.size, args.page_blob)

if __name__ == "__main__":

    main()    
            
    
#%% Interactive driver

if False:
    
    #%%    
    
    sas_url = ''
    input_file_path = None
    input_file_size_gb = 1    
    page_blob = False

    get_bandwidth(sas_url, input_file_path, input_file_size_gb, page_blob)
    
