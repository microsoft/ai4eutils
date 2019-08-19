#
# path_utils.py
#
# Miscellaneous useful utils for path manipulation, things that could *almost*
# be in os.path, but aren't.
#
#

#%% Constants and imports

import os
import glob


#%% General path functions

def recursive_file_list(baseDir, bConvertSlashes=True):
    """
    Enumerate files (not directories) in [baseDir], optionally converting \ to /
    """

    allFiles = []

    for root, _, filenames in os.walk(baseDir):
        for filename in filenames: 
            fullPath = os.path.join(root,filename)
            if bConvertSlashes:
                fullPath = fullPath.replace('\\','/')
            allFiles.append(fullPath)

    return allFiles

# http://nicks-liquid-soapbox.blogspot.com/2011/03/splitting-path-to-list-in-python.html
def split_path(path, maxdepth=100):
    """
    Splits [path] into all its constituent tokens, e.g.:
    
    c:\blah\boo\goo.txt
    
    ...becomes:
        
    ['c:\\', 'blah', 'boo', 'goo.txt']
    """
    ( head, tail ) = os.path.split(path)
    return split_path(head, maxdepth - 1) + [ tail ] \
        if maxdepth and head and head != path \
        else [ head or tail ]
        
        
#%% Image-related path functions
        
imageExtensions = ['.jpg','.jpeg','.gif','.png']
    
def is_image_file(s):
    '''
    Check a file's extension against a hard-coded set of image file extensions    '
    '''
    ext = os.path.splitext(s)[1]
    return ext.lower() in imageExtensions
    
    
def find_image_strings(strings):
    '''
    Given a list of strings that are potentially image file names, look for strings
    that actually look like image file names (based on extension).
    '''
    imageStrings = []
    bIsImage = [False] * len(strings)
    for iString,f in enumerate(strings):
        bIsImage[iString] = is_image_file(f) 
        if bIsImage[iString]:
            imageStrings.append(f)
        
    return imageStrings

    
def find_images(dirName,bRecursive=False):
    '''
    Find all files in a directory that look like image file names.  Returns absolute
    paths.
    '''
    if bRecursive:
        strings = glob.glob(os.path.join(dirName,'**','*.*'), recursive=True)
    else:
        strings = glob.glob(os.path.join(dirName,'*.*'))
        
    imageStrings = find_image_strings(strings)
    
    return imageStrings
