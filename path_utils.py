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
import datetime
import ntpath


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


def split_path(path, maxdepth=100):
    """
    Splits [path] into all its constituent tokens, e.g.:
    
    c:\blah\boo\goo.txt
    
    ...becomes:
        
    ['c:\\', 'blah', 'boo', 'goo.txt']
    
    http://nicks-liquid-soapbox.blogspot.com/2011/03/splitting-path-to-list-in-python.html
    """
    
    ( head, tail ) = os.path.split(path)
    return split_path(head, maxdepth - 1) + [ tail ] \
        if maxdepth and head and head != path \
        else [ head or tail ]
        
def fileparts(n):
    """
    p,n,e = fileparts(filename)    
     
    fileparts(r'c:\blah\BLAH.jpg') returns ('c:\blah','BLAH','.jpg')
     
    Note that the '.' lives with the extension, and separators have been removed.
    """
    
    p = ntpath.dirname(n)
    basename = ntpath.basename(n)
    n,e = ntpath.splitext(basename)
    return p,n,e
    

if False:

    ##%% Test driver for fileparts()
    # from matlab_porting_tools import fileparts
    
    TEST_STRINGS = [
            r'c:\blah\BLAH.jpg',
            r'c:\blah.jpg',
            r'blah',
            r'c:\blah',
            r'c:\blah\BLAH',
            r'blah.jpg'
            ]
    
    for s in TEST_STRINGS:
        p,n,e = fileparts(s)
        print('{}:\n[{}],[{}],[{}]\n'.format(s,p,n,e))
        

def insert_before_extension(filename,s=''):
    """
    function filename = insert_before_extension(filename,s)
    
    Inserts the string [s] before the extension in [filename], separating with '.'.  
    
    If [s] is empty, generates a date/timestamp.
    
    If [filename] has no extension, appends [s].    
    """
    
    assert len(filename) > 0
    
    if len(s) == 0:
        s = datetime.datetime.now().strftime('%Y.%m.%d.%H.%M.%S')

    p,n,e = fileparts(filename);
    
    fn = n + '.' + s + e
    filename = os.path.join(p,fn);
    
    return filename


if False:

    ##%% Test driver for insert_before_extension
    
    # from matlab_porting_tools import insert_before_extension
    
    TEST_STRINGS = [
            r'c:\blah\BLAH.jpg',
            r'c:\blah.jpg',
            r'blah',
            r'c:\blah',
            r'c:\blah\BLAH',
            r'blah.jpg'
            ]
    
    for s in TEST_STRINGS:
        sOut = insert_before_extension(s)
        print('{}: {}'.format(s,sOut))


def top_level_folder(p):
    """
    Gets the top-level folder from the path *p*; on Windows, will use the top-level folder
    that isn't the drive.  E.g., top_level_folder(r"c:\blah\foo") returns "c:\blah".  Does not
    include the leaf node, i.e. top_level_folder('/blah/foo') returns '/blah'.
    """
    if p == '':
        return ''
    
    # Path('/blah').parts is ('/','blah')
    parts = split_path(p)
    
    if len(parts) == 1:
        return parts[0]
    
    drive = os.path.splitdrive(p)[0]
    if parts[0] == drive or parts[0] == drive + '/' or parts[0] == drive + '\\' or parts[0] in ['\\','/']: 
        return os.path.join(parts[0],parts[1])    
    else:
        return parts[0]
    
if False:        
    p = 'blah/foo/bar'; s = top_level_folder(p); print(s); assert s == 'blah'
    p = '/blah/foo/bar'; s = top_level_folder(p); print(s); assert s == '/blah'
    p = 'bar'; s = top_level_folder(p); print(s); assert s == 'bar'
    p = ''; s = top_level_folder(p); print(s); assert s == ''
    p = 'c:\\'; s = top_level_folder(p); print(s); assert s == 'c:\\'
    p = r'c:\blah'; s = top_level_folder(p); print(s); assert s == 'c:\\blah'
    p = r'c:\foo'; s = top_level_folder(p); print(s); assert s == 'c:\\foo'
    p = r'c:/foo'; s = top_level_folder(p); print(s); assert s == 'c:/foo'
    p = r'c:\foo/bar'; s = top_level_folder(p); print(s); assert s == 'c:\\foo'
    
            
#%% Image-related path functions
        
imageExtensions = ['.jpg','.jpeg','.gif','.png']
    
def is_image_file(s):
    """
    Check a file's extension against a hard-coded set of image file extensions    '
    """
    
    ext = os.path.splitext(s)[1]
    return ext.lower() in imageExtensions
    
    
def find_image_strings(strings):
    """
    Given a list of strings that are potentially image file names, look for strings
    that actually look like image file names (based on extension).
    """
    
    imageStrings = []
    bIsImage = [False] * len(strings)
    for iString,f in enumerate(strings):
        bIsImage[iString] = is_image_file(f) 
        if bIsImage[iString]:
            imageStrings.append(f)
        
    return imageStrings

    
def find_images(dirName,bRecursive=False):
    """
    Find all files in a directory that look like image file names.  Returns absolute
    paths.
    """
    
    if bRecursive:
        strings = glob.glob(os.path.join(dirName,'**','*.*'), recursive=True)
    else:
        strings = glob.glob(os.path.join(dirName,'*.*'))
        
    imageStrings = find_image_strings(strings)
    
    return imageStrings


#%% Filename-cleaning functions

import unicodedata
import string

valid_filename_chars = "~-_.() %s%s" % (string.ascii_letters, string.digits)
valid_path_chars = valid_filename_chars + "\\/:"
separator_chars = ":/\\"
char_limit = 255

def clean_filename(filename, whitelist=valid_filename_chars):
    """
    Removes invalid characters (on any reasonable OS) in a filename, trims to a 
    maximum length, and removes unicode characters.
    
    Does not allow :\/ , use clean_path if you want to preserve those
    
    Adapted from: https://gist.github.com/wassname/1393c4a57cfcbf03641dbc31886123b8    
    """
    # keep only valid ascii chars
    cleaned_filename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore').decode()
    
    # keep only whitelisted chars
    cleaned_filename = ''.join([c for c in cleaned_filename if c in whitelist])
    return cleaned_filename[:char_limit]  


def clean_path(pathname, whitelist=valid_path_chars):
    """
    Removes invalid characters (on any reasonable OS) in a filename, trims to a 
    maximum length, and removes unicode characters.
    """
    return clean_filename(pathname,whitelist=whitelist)


def flatten_path(pathname):
    """
    Removes invalid characters (on any reasonable OS) in a filename, trims to a 
    maximum length, and removes unicode characters, then replaces all valid separators
    with '~'.
    """
    s = clean_path(pathname)
    for c in separator_chars:
        s = s.replace(c,'~')
    return s

