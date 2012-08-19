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

try:
    import lastfp
except:
    raise LastFMFingerprintException( 'LastFM fingerprint library not found.' )
finally:
    del lastfp

from gi.repository import Gio, RB, Gtk
from urlparse import urlparse
from urllib import unquote
from subprocess import check_output
import re
import rb

import LastFMExtensionKeys as Keys
from LastFMExtensionUtils import asynchronous_call as async, idle_add

DIALOG_BUILDER_FILE = 'lastfmExtensionFingerprintDialog.glade'
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
class LastFMFingerprintException( Exception ):
    def __init__( self, message ):
        super( LastFMFingerprintException, self).__init__( message )
        
class LastFMFingerprinter:
    
    def __init__( self, plugin ):
        self.settings = Gio.Settings.new( Keys.PATH )
        
        #load the dialog builder file
        self.builder_file = rb.find_plugin_file( plugin, DIALOG_BUILDER_FILE )
        
        #rhythmbox database
        self.db = plugin.db
        
    def fingerprint( self, entry ):
        #show the fingerprinter dialog
        ui = self.show_dialog()
        
        #fingerprint and match the entry asynchronously
        async( self.match, self.append_options, entry, *ui )( entry )       
        
    def show_dialog( self ):
        #create a new builder over the builder_file
        builder = Gtk.Builder()
        builder.add_from_file( self.builder_file )
		
		#connect signals
		builder.connect_signals( self )
		
		#show the dialog
		builder.get_object( DIALOG_NAME ).present()
		
		#get the status box and the box
		main_box = builder.get_object( BOX )
		status_box = builder.get_object( STATUS_BOX )
		action_save = builder.get_object( ACTION_SAVE )
		
		return main_box, status_box, action_save
    
    def match( self, entry ):
        #get artist, album, track and path    
        path = unquote( urlparse( entry.get_playback_uri() ).path )
              
        #match the song        
        raw = check_output( './matcher.py "%s"' % path, shell=True )
        
        lines = re.split( '\n+', raw )
        matches = lines[:-1]
        
        return matches          
    
    def append_options( self, result, entry, main_box, status_box, action_save ):        
        vbox = Gtk.VBox()
        
        first = None
        for match in result:
            if not first:
                toggle = Gtk.RadioButton( label=match )   
                first = toggle
            else:
                toggle = Gtk.RadioButton( label=match )
                toggle.join_group( first )         
            
            toggle.set_mode( False )    
            toggle.show()
            
            vbox.pack_start( toggle, True, True, 0 )   
        
        vbox.show()
        
        action_save.connect( 'activate', self.save_selected, entry, main_box )
        
        idle_add( status_box.destroy )
        idle_add( main_box.pack_start, vbox, True, True, 0 )
        idle_add( action_save.set_sensitive, True )        
        
    def close_fingerprinter_window( self, dialog ):
        dialog.destroy()
            
    def save_selected( self, _, entry, box ):
        options = box.get_children()[0].get_children()
        
        for option in options:
            if option.get_active():
                metadata = re.match( r'.+?:\s(.+?)\s-\s(.+)$',option.get_label() ).groups()
                self.db.entry_set( entry, RB.RhythmDBPropType.ARTIST, metadata[0] ) 
                self.db.entry_set( entry, RB.RhythmDBPropType.TITLE, metadata[1] ) 
                break     
                
        self.close_fingerprinter_window( box.get_parent() )  
    
