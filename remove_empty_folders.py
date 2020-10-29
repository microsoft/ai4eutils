#
# Recursively remove empty folders from a folder.
#
# Usage:
#
# remove_empty_folders /top/level/folder
#

#%% Imports

import os
import sys


#%% Functions

def remove_empty_folders(path, removeRoot=True):
    
    try:
        
        # https://www.jacobtomlinson.co.uk/posts/2014/python-script-recursively-remove-empty-folders/directories/
        if not os.path.isdir(path):
            return
    
        # Remove empty subfolders
        files = os.listdir(path)
        if len(files):
            for f in files:
                fullpath = os.path.join(path, f)
                if os.path.isdir(fullpath):
                    remove_empty_folders(fullpath)
    
        # List files again; we may have removed subfolders
        files = os.listdir(path)
        
        # If the folder is still empty, delete it
        if len(files) == 0 and removeRoot:
            print('Removing empty folder: {}'.format(path))
            try:
                os.rmdir(path)
            except:
                print('Error removing {}'.format(path))

    except:
        
        print('Error processing {}'.format(path))
        

#%% Command-line driver
        
if __name__ == '__main__' and '__file__' in globals():
    
    if len(sys.argv) < 2:
        print('No base dir specified')
        sys.exit()
        
    base_dir = sys.argv[1]
    if not os.path.isdir(base_dir):
        print('{} is not a directory'.format(base_dir))
        sys.exit()
        
    remove_empty_folders(base_dir)
