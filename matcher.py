#!/usr/bin/env python
"""A simple program for using pylastfp to fingerprint and look up
metadata for MP3 files. Usage:

    $ python matcher.py [-m] mysterious_music.mp3
    
By default, the script uses Gstreamer to decode audio. The -m flag
makes it use MAD instead (which, of course, only works on MPEG audio
such as MP3). To use the script, of course, you'll need to have
either Gstreamer (and its Python bindings) or pymad installed.
"""
import sys
import os

import LastFMExtensionKeys as Keys

# Just a little trickery to avoid importing the "lastfp" package that's
# in the source distribution, because it won't contain the built
# _fplib.so extension module. We need to import from the built verison,
# and this script is likely to be run from the distribution root.
for path in '', os.path.abspath(os.path.dirname(__file__)):
    if path in sys.path:
        sys.path.remove(path)
import lastfp

if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        print "usage: python lastmatch.py [-m] mysterious_music.mp3 [...]"
        sys.exit(1)
    if args[0] == '-m':
        match_func = lastfp.mad_match
        args.pop(0)
    else:
        match_func = lastfp.gst_match
        
    path = os.path.abspath(os.path.expanduser(args[0]))
    artist = args[1]
    album = args[2]    
    title = args[3]

    # Perform match.
    try:
        xml = match_func( Keys.API_KEY, path, metadata={ 'artist':artist,
                                                         'album':album,
                                                         'track':title } )
    except lastfp.ExtractionError:
        print 'fingerprinting failed!'
        sys.exit(1)
    except lastfp.QueryError:
        print 'could not match fingerprint!'
        sys.exit(1)

    # Show results.
    matches = lastfp.parse_metadata(xml)
    for track in matches:
        rank = track['rank']
        artist = track['artist'].encode('utf-8') 
        title = track['title'].encode('utf-8') 
        
        print '%.2f: %s - %s' % (rank, artist, title)
