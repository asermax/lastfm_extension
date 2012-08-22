# -*- Mode: python; coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
#
# Copyright (C) 2012 - Carrasco Agustin
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

from gi.repository import Gio, RB, Gtk
from urlparse import urlparse
from urllib import unquote
from subprocess import check_output, CalledProcessError
import math
import rb

import LastFMExtensionKeys as Keys
from LastFMExtensionUtils import asynchronous_call as async, idle_add

#try to import lastfp
class LastFMFingerprinterException( Exception ):
    def __init__( self, message ):
        super( LastFMFingerprinterException, self).__init__( message )

try:
    import lastfp
    del lastfp
except:
    raise LastFMFingerprinterException( 'LastFM fingerprint library not found.' )

#constants
DIALOG_BUILDER_FILE = 'lastfmExtensionFingerprintDialog.glade'
MATCHER = 'matcher.py'
DIALOG_NAME = 'song-selection-dialog'
BOX = 'songe-selection-dialog-vbox'
STATUS_BOX = 'statusBox'
ACTION_SAVE = 'actionSave'

ui_context_menu = """
<ui>
  <popup name="BrowserSourceViewPopup">
	 <placeholder name="PluginPlaceholder">
         <menuitem name="FingerprintSong" action="FingerprintSong"/>
     </placeholder>
  </popup>
  <popup name="PlaylistViewPopup">
	 <placeholder name="PluginPlaceholder">
         <menuitem name="FingerprintSong" action="FingerprintSong"/>
     </placeholder>
  </popup>
  <popup name="QueuePlaylistViewPopup">
     <placeholder name="PluginPlaceholder">
	     <menuitem name="FingerprintSong" action="FingerprintSong"/>
     </placeholder>
  </popup>
  <popup name="PodcastViewPopup">
     <placeholder name="PluginPlaceholder">
	     <menuitem name="FingerprintSong" action="FingerprintSong"/>
     </placeholder>
  </popup>
</ui>
"""
        
'''
This extension is responsible of fingerprinting songs and showing the UI to
let the user decide if he wants to save the result and which match to use.
'''
class LastFMFingerprinter:
    
    '''
    Initialises the extension, using the base plugin to populate some of the 
    internal properties used on the fingerprinting process.
    '''
    def __init__( self, plugin ):
        self.settings = Gio.Settings.new( Keys.PATH )
        
        #get the builder file path
        self.builder_file = rb.find_plugin_file( plugin, DIALOG_BUILDER_FILE )
        
        #save the matcher path
        self.matcher_path = rb.find_plugin_file( plugin, MATCHER )
        
        #rhythmbox database
        self.db = plugin.db
        
        #lastfm network
        self.network = plugin.network
        
        #queue for requests
        self.queue = []
    
    '''
    This is this extension principal interface. This method should be called
    whenever it's needed to fingerprint a song. 
    It uses the extension queue system, to avoid multiple request to happen at 
    the same time.
    '''
    def request_fingerprint( self, entry ):
        if len( self.queue ) == 0:
            self._fingerprint( entry )
        
        self.queue.append( entry )
    
    '''
    This is the actual function that starts the fingerprinting.
    It shows a Dialog to indicate the user to wait, and executes the 
    fingerprinting proccess asynchronously.
    '''    
    def _fingerprint( self, entry ):
        #show the fingerprinter dialog
        ui = self._show_dialog( entry )
        
        #fingerprint and match the entry asynchronously
        async( self._match, self._append_options, entry, *ui )( entry, 
                                                              self.network )       
    
    '''
    Shows a wait dialog with the entry title and artist in the title.
    This dialog is used to show the matching options after they are fetched.
    '''    
    def _show_dialog( self, entry ):
        #create a new builder over the builder_file
        builder = Gtk.Builder()
        builder.add_from_file( self.builder_file )
		
		#connect signals
		builder.connect_signals( self )
		
		#show the dialog
		dialog = builder.get_object( DIALOG_NAME )
		dialog.set_title( 'Matches for %s - %s' % 
		                    ( entry.get_string( RB.RhythmDBPropType.ARTIST ),
		                      entry.get_string( RB.RhythmDBPropType.TITLE ) ) )
		dialog.present()
		
		#get the status box and the box
		main_box = builder.get_object( BOX )
		status_box = builder.get_object( STATUS_BOX )
		action_save = builder.get_object( ACTION_SAVE )
		
		return main_box, status_box, action_save
    
    '''
    This method encapsulates the fingerprinting and matching process.
    It takes info from the entry to realize the fingerprinting and uses pylast
    to retrieve the tracks info, which is finally returned as a list of Track
    instances. 
    '''
    def _match( self, entry, network ):
        #get artist, album, track and path    
        path = unquote( urlparse( entry.get_playback_uri() ).path )
        artist = entry.get_string(RB.RhythmDBPropType.ARTIST )
        album = entry.get_string(RB.RhythmDBPropType.ALBUM )
        title = entry.get_string(RB.RhythmDBPropType.TITLE )
        
        #match the song    
        try:    
            fpid = check_output( 
                        [self.matcher_path, "%s" % path, artist, album, title] )
                
            result = network.get_tracks_by_fpid( fpid )
                        
        except CalledProcessError as error:
            #in the case the fingerprinter fails, raise an exception 
            raise Exception( error.output )
        
        return result          
    
    '''
    This method appends toggles buttons to the dialog, with the info of the 
    matched tracks and connects the signal to save the selected option.
    '''
    def _append_options( self, result, entry, main_box, status_box, action_save ):        
        #box which will contain the toggles   
        vbox = Gtk.VBox()
        
        #if there where actual results
        if type( result ) is list and len( result ) > 0:
            #options list
            options = []
            
            #for each option
            for track in result:
                #append the option and make sure they are all in the same group
                label = '%d%%: %s' % (math.ceil( track.rank * 100 ), str( track ))
            
                if not options:
                    toggle = Gtk.RadioButton( label=label )   
                    options.append( toggle )
                else:
                    toggle = Gtk.RadioButton( label=label )
                    toggle.join_group( options[0] )         
                
                toggle.set_mode( False )    
                
                vbox.pack_start( toggle, True, True, 0 )  
             
            #also, add a checkbox to ask if fetch extra info
            check_extra = Gtk.CheckButton( 'Fetch extra info?')
            check_extra.set_tooltip_text( 'Fetch album name, track number, '
                                          +'relase year, playcount and rating')
             
            vbox.pack_end( check_extra, True, True, 0 )  
             
            #connect and activate the save action
            action_save.connect( 'activate', self._save_selected, entry, result, 
                                 main_box.get_parent(), options, check_extra )
            idle_add( action_save.set_sensitive, True )          
            
        #if there weren't valid results
        else:
            #if we catched and exception show the error, otherwise, indicate 
            #that there weren't matches
            if type( result ) is Exception:
                label = Gtk.Label( result.message )
            else:
                label = Gtk.Label( 'No matches found.' )
                            
            vbox.pack_start( label, True, True, 0 )
        
        #show the box   
        vbox.show_all()  
         
        #delete the old box and append the new
        idle_add( status_box.destroy )
        idle_add( main_box.pack_start, vbox, True, True, 0 )
    
    '''
    Callback for closing the dialog.
    '''  
    def _close_fingerprinter_window( self, dialog ):
        dialog.destroy()
        
        self.queue.pop( 0 )
        
        if len( self.queue ) > 0:
            self._fingerprint( self.queue[0] )
    
    '''
    Callback for saving the selected option.
    '''                   
    def _save_selected( self, _, entry, tracks, dialog, options, extra ):        
        for option in options:
            if option.get_active():
                track = tracks[options.index( option )]
                
                self.db.entry_set( entry, RB.RhythmDBPropType.ARTIST, 
                                          str(track.get_artist()) ) 
                self.db.entry_set( entry, RB.RhythmDBPropType.TITLE, 
                                          str(track.get_title()) ) 
                self.db.commit()
                
                #asynchronously retrieve extra data
                if extra.get_active():
                    async( self._fetch_extra_info, 
                           self._delayed_properties_save, entry )( track )
                
                break     
                
        self._close_fingerprinter_window( dialog ) 
    
    '''
    Fetch extra info from Last.fm.
    For now, it fetchs:
    - Playcount
    - Album data (if available)
        - Rating (if is loved, 5 stars)
        - Album Name
        - Release Year (if available)
        - Album Artist
        - Track Number
    - TODO: Genre
    '''    
    def _fetch_extra_info( self, track ):
        #list for extra info with it's db keys
        info = []
        
        #play count
        info.append( (RB.RhythmDBPropType.PLAY_COUNT, 
                      track.get_playcount( True )) )
                   
        #loved track (rating 5 stars)           
        if track.is_loved():
            info.append( (RB.RhythmDBPropType.RATING, 5) )
        
        #album data
        album = track.get_album()
        
        if album:
            #album name
            info.append( (RB.RhythmDBPropType.ALBUM, str( album.get_name() )) )
            
            #release date (year)
            date = album.get_release_date()
            
            if date.strip() != '':
                info.append( (RB.RhythmDBPropType.DATE, 
                              int( date.split()[2][:-1] )) )
            
            #album artist
            info.append( (RB.RhythmDBPropType.ALBUM_ARTIST, 
                          str( album.get_artist().get_name() )) )
                          
            #track number
            tracks = album.get_tracks()
            
            for track_number in range( 0, len( tracks ) ):
                if track == tracks[track_number]:
                    break
            
            info.append( (RB.RhythmDBPropType.TRACK_NUMBER, track_number + 1) )
        
        return info
    
    '''
    Callback used after extra info is fetched, to save it to the properties of 
    the entry.
    '''
    def _delayed_properties_save( self, info, entry ):    
        print info
    
        for prop in info:
            idle_add( self.db.entry_set, entry,*prop )
            
        idle_add( self.db.commit )
    
