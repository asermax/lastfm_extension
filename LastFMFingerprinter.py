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
import re, math
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
        
class LastFMFingerprinter:
    
    def __init__( self, plugin ):
        self.settings = Gio.Settings.new( Keys.PATH )
        
        #load the dialog builder file
        self.builder_file = rb.find_plugin_file( plugin, DIALOG_BUILDER_FILE )
        
        #save the matcher path
        self.matcher_path = rb.find_plugin_file( plugin, MATCHER )
        
        #rhythmbox database
        self.db = plugin.db
        
        #lastfm network
        self.network = plugin.network
        
        #queue for requests
        self.queue = []
    
    def request_fingerprint( self, entry ):
        if len( self.queue ) == 0:
            self.fingerprint( entry )
        
        self.queue.append( entry )
        
    def fingerprint( self, entry ):
        #show the fingerprinter dialog
        ui = self.show_dialog( entry )
        
        #fingerprint and match the entry asynchronously
        async( self.match, self.append_options, entry, *ui )( entry, 
                                                              self.network )       
        
    def show_dialog( self, entry ):
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
    
    def match( self, entry, network ):
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
            result = error.output
        
        return result          
    
    def append_options( self, result, entry, main_box, status_box, action_save ):           
        vbox = Gtk.VBox()
        
        if type( result ) is list and len( result ) > 0:
            first = None
            for track in result:
                label = '%d%%: %s' % (math.ceil( track.rank * 100 ), str( track ))
            
                if not first:
                    toggle = Gtk.RadioButton( label=label )   
                    first = toggle
                else:
                    toggle = Gtk.RadioButton( label=label )
                    toggle.join_group( first )         
                
                toggle.set_mode( False )    
                toggle.show()
                
                vbox.pack_start( toggle, True, True, 0 )  
                
            action_save.connect( 'activate', self.save_selected, entry, result, 
                                                                      main_box )
            idle_add( action_save.set_sensitive, True ) 
        else:
            if type( result ) is str:
                label = Gtk.Label( result )
            else:
                label = Gtk.Label( 'No matches found.' )
                
            label.show()
            
            vbox.pack_start( label, True, True, 0 )
            
        vbox.show()  
                             
        idle_add( status_box.destroy )
        idle_add( main_box.pack_start, vbox, True, True, 0 )
        
    def close_fingerprinter_window( self, dialog ):
        dialog.destroy()
        
        self.queue.pop( 0 )
        
        if len( self.queue ) > 0:
            self.fingerprint( self.queue[0] )
                       
    def save_selected( self, _, entry, tracks, box ):
        options = box.get_children()[0].get_children()
        
        for option in options:
            if option.get_active():
                track = tracks[options.index( option )]
                
                self.db.entry_set( entry, RB.RhythmDBPropType.ARTIST, 
                                          str(track.get_artist()) ) 
                self.db.entry_set( entry, RB.RhythmDBPropType.TITLE, 
                                          str(track.get_title()) ) 
                self.db.commit()
                break     
                
        self.close_fingerprinter_window( box.get_parent() )  
    
