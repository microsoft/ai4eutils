#
# path_utils.py
#
# Miscellaneous useful utils for path manipulation, things that could *almost*
# be in os.path, but aren't.
#
# Owner: Dan Morris (dan@microsoft.com)
#

import os

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