#!/usr/bin/env python
"""A simple program for using pylastfp to fingerprint MP3 files. Usage:

    $ python matcher.py mysterious_music.mp3   
"""
import sys, os, lastfp 

import LastFMExtensionKeys as Keys

'''
Modified match function to return only the fpid
'''
def match(apikey, pcmiter, samplerate, duration, channels=2, metadata=None):
    fpdata = lastfp.extract(pcmiter, samplerate, channels)
    fpid = lastfp.fpid_query(duration, fpdata, metadata)
    return fpid

lastfp.match = match

if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        print "usage: matcher.py mysterious_music.mp3"
        sys.exit(1)
        
    path = os.path.abspath(os.path.expanduser(args[0]))
    artist = args[1]
    album = args[2]    
    title = args[3]

    # Perform match.
    try:
        fpid = lastfp.match_file( Keys.API_KEY, path, metadata={ 'artist':artist,
                                                         'album':album,
                                                         'track':title } )
    except lastfp.ExtractionError:
        print 'Fingerprinting failed! (Is the song too short?)'
        sys.exit(1)
    except lastfp.QueryError:
        print 'Could not match fingerprint!'
        sys.exit(1)

    # Show fpid
    print fpid
