#
# matlab_porting_tools.py
#
# Module containing a few ported Matlab functions that makes it easier
# for me to port other, larger Matlab functions.  Some of these are 
# built-in Matlab functions (e.g. fileparts()), some are 
# new utility functions my Matlab workflow depends on (e.g. 
# insert_before_extension()), and some are silly one-liners where it's
# easier for me to remember my Matlab-universe words than the Python-universe
# words, e.g. string_starts_with().
#
# Owner: Dan Morris (dan@microsoft.com)
#


#%% Constants and imports

import ntpath
import os
import datetime


#%% fileparts()

def fileparts(n):
    '''
    p,n,e = fileparts(filename)    
     
    fileparts(r'c:\blah\BLAH.jpg') returns ('c:\blah','BLAH','.jpg')
     
    Note that the '.' lives with the extension, and separators have been removed.
    '''
    
    p = ntpath.dirname(n)
    basename = ntpath.basename(n)
    n,e = ntpath.splitext(basename)
    return p,n,e
    

if False:

    #%% Test driver for fileparts()
    # from danUtil.matlab_porting_tools import fileparts
    
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
        

#%% insert_before_extension()
        
def insert_before_extension(filename,s=''):
    '''
    function filename = insert_before_extension(filename,s)
    
    Inserts the string [s] before the extension in [filename], separating with '.'.  
    
    If [s] is empty, generates a date/timestamp.
    
    If [filename] has no extension, appends [s].    
    '''
    
    assert len(filename) > 0
    
    if len(s) == 0:
        s = datetime.datetime.now().strftime('%Y.%m.%d.%H.%M.%S')

    p,n,e = fileparts(filename);
    
    fn = n + '.' + s + e
    filename = os.path.join(p,fn);
    
    return filename


if False:

    #%% Test driver for insert_before_extension
    
    # from danUtil.matlab_porting_tools import insert_before_extension
    
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


#%% sec2hms()
        
def sec2hms(tSeconds):
    '''
    function [str,h,m,s] = sec2hms(tSeconds,separator)
    
        Convert a time in seconds to a string of the form:
    
        1 hour, 2 minutes, 31.4 seconds
    
    I prefer using the humanfriendly package for this, but I use this when
    porting from Matlab.    
    '''

    # https://stackoverflow.com/questions/775049/python-time-seconds-to-hms    
    m, s = divmod(tSeconds, 60)
    h, m = divmod(m, 60)
    
    # colonString = '%d:%02d:%02d' % (h, m, s)
    # return (colonString,verboseString)
    
    hms = ''
    separator = ', '
    if (h > 0):
        pluralString = ''    
        if (h > 1):
            pluralString = 's'
        hms = hms + '%d hour%s%s' % (h,pluralString,separator)
    
    if (m > 0):
        pluralString = ''
        if (m > 1):
            pluralString = 's'
        hms = hms + '%d min%s%s' % (m,pluralString,separator)
    
    hms = hms + '%3.3fsec' % s
            
    return hms

if False:

    #%% Test driver for sec2hms()
    # from danUtil.matlab_porting_tools import sec2hms
    
    TEST_VALUES = [
            60033, 30.4, 245234523454.1
            ]
    
    for n in TEST_VALUES:
        s = sec2hms(n)
        print('{} - {}'.format(n,s))


#%% read_lines_from_file()

def read_lines_from_file(filename):
    
    with open(filename) as f:
        content = f.readlines()
    
    # Remove trailing newlines
    content = [x.rstrip() for x in content] 
    
    return content

#%% write_lines_to_file()
    
def write_lines_to_file(lines, filename):
    
    with open(filename,'w') as f:
        for line in lines:
            f.write(line+ '\n')
            

#%% string_ends_with()
            
def string_ends_with(s,query):    
    return s.endswith(query)

def string_starts_with(s,query):    
    return s.startswith(query)
