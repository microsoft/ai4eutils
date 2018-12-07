#
# function write_html_image_list(filename,imageFilenames,titles, options)
#
# Given a list of image file names, writes an HTML file that
# shows all those images, with optional one-line headers above each.
#
# Each "filename" can also be a list array of filenames (they will share a title).
#
# Strips directory information away if options.makeRelative == 1.
#
# Tries to convert absolute to relative paths if options.makeRelative == 2.
#
# Owner: Dan Morris (dan@microsoft.com)
#


#%% Constants and imports

import math
import matlab_porting_tools as mpt


#%% write_html_image_list

def write_html_image_list(filename=None,imageFilenames=None,titles=(),options={}):

    # returns an options struct
    
    if 'fHtml' not in options:
        options['fHtml'] = -1
    
    if 'makeRelative' not in options:        
        options['makeRelative'] = 0
    
    if 'headerHtml' not in options:
        options['headerHtml'] = ''        
    
    if 'trailerHtml' not in options:
        options['trailerHtml'] = ''    

    if 'imageStyle' not in options:
        options['imageStyle'] = ''    
    
    # Possibly split the html output for figures into multiple files; Chrome gets sad with
    # thousands of images in a single tab.        
    if 'maxFiguresPerHtmlFile' not in options:
        options['maxFiguresPerHtmlFile'] = math.inf    
    
    if filename == None:
        return options
    
    # Remove leading directory information from filenames if requested
    if options['makeRelative'] == 1:
        for iImage in range(0,len(imageFilenames)):
            _,n,e = mpt.fileparts(imageFilenames[iImage])
            imageFilenames[iImage] = n + e
        
    elif options['makeRelative'] == 2:
        baseDir,_,_ = mpt.fileparts(filename)
        if len(baseDir) > 1 and baseDir[-1] != '\\':
            baseDir = baseDir + '\\'
        
        for iImage in range(0,len(imageFilenames)):
            fn = imageFilenames[iImage]
            fn = fn.replace(baseDir,'')
            imageFilenames[iImage] = fn        
    
    nImages = len(imageFilenames)
    if len(titles) != 0:
        assert len(titles) == nImages,'Title/image list mismatch'    
    
    # If we need to break this up into multiple files...
    if nImages > options['maxFiguresPerHtmlFile']:
    
        # You can't supply your own file handle in this case
        if options['fHtml'] != -1:
            raise ValueError(
                    'You can''t supply your own file handle if we have to page the image set')
        
        figureFileStartingIndices = list(range(0,nImages,options['maxFiguresPerHtmlFile']))

        assert len(figureFileStartingIndices) > 1
        
        # Open the meta-output file
        fMeta = open(filename,'w')
        
        # Write header stuff
        fMeta.write('<html><body>\n')    
        fMeta.write(options['headerHtml'])        
        fMeta.write('<table border = 0 cellpadding = 2>\n')
        
        for startingIndex in figureFileStartingIndices:
            iStart = startingIndex
            iEnd = startingIndex+options['maxFiguresPerHtmlFile']-1;
            if iEnd >= nImages:
                iEnd = nImages-1
            
            trailer = 'image_{:05d}_{:05d}'.format(iStart,iEnd)
            localFiguresHtmlFilename = mpt.insert_before_extension(filename,trailer)
            fMeta.write('<tr><td>\n')
            fMeta.write('<p style="padding-bottom:0px;margin-bottom:0px;text-align:left;font-family:''segoe ui'',calibri,arial;font-size:100%;text-decoration:none;font-weight:bold;">')
            fMeta.write('<a href="{}">Figures for images {} through {}</a></p></td></tr>\n'.format(
                localFiguresHtmlFilename,iStart,iEnd))
            
            localImageFilenames = imageFilenames[iStart:iEnd+1]
            
            if len(titles) == 0:
                localTitles = []
            else:
                localTitles = titles[iStart:iEnd+1]            
            
            localOptions = options.copy();
            localOptions['headerHtml'] = '';
            localOptions['trailerHtml'] = '';
            
            # Make a recursive call for this image set
            write_html_image_list(localFiguresHtmlFilename,localImageFilenames,localTitles,
                localOptions)
            
        # ...for each page of images
        
        fMeta.write('</table></body>\n')
        fMeta.write(options['trailerHtml'])
        fMeta.write('</html>\n')
        fMeta.close()
        
        return options
        
    # ...if we have to make multiple sub-pages
        
    bCleanupFile = False
    if options['fHtml'] == -1:
        bCleanupFile = True;
        fHtml = open(filename,'w')
    else:
        fHtml = options['fHtml']
        
    fHtml.write('<html><body>\n')
    
    fHtml.write(options['headerHtml'])
    
    # Write out images
    for iImage in range(0,len(imageFilenames)):
        
        if len(titles) > 0:
            s = titles[iImage];
            fHtml.write(
                    '<p style="font-family:calibri,verdana,arial;font-weight:bold;font-size:150%;text-align:left;">{}</p>\n'\
                    .format(s))            

        # If we have multiple images for this same title
        if (isinstance(imageFilenames[iImage],list)):
            files = imageFilenames[iImage];
            for iFile in range(0,len(files)):
                fHtml.write('<img src="{}" style="{}"><br/>\n'.format(files(iFile),options['imageStyle']))
                if iFile != len(files)-1:
                    fHtml.write('<br/>')                
            # ...for each file in this group
        else:
            fHtml.write('<img src="{}" style="{}"><br/>\n'.\
                        format(imageFilenames[iImage],options['imageStyle']))
        
    # ...for each image we need to write
    
    fHtml.write(options['trailerHtml'])
    
    fHtml.write('</body></html>\n')
    
    if bCleanupFile:
        fHtml.close()    

# ...function


