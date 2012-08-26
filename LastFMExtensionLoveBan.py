# -*- Mode: python; coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
#
# Copyright (C) 2012 - Carrasco Agustin
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301  USA.

from lastfm_extension import LastFMExtension
from gi.repository import Gtk, Gio, RB

import rb

from LastFMExtensionUtils import asynchronous_call as async, notify

#name and description
NAME = "LastFMLoveBan"
DESCRIPTION = "Add the Love and Ban buttons to your Toolbar!"

#constants
UI_STR = """
<ui>
  <toolbar name="ToolBar">
    <placeholder name="PluginPlaceholder">
      <toolitem name="Loves" action="LoveTrack"/>
      <toolitem name="Ban" action="BanTrack"/>
    </placeholder>
  </toolbar>
</ui>
"""

#icon paths
LOVE_ICON = 'img/love.png'
BAN_ICON = 'img/ban.png'

class Extension( LastFMExtension ):
    def __init__( self, plugin ):
        super( Extension, self ).__init__( plugin )
        
        self.network = plugin.network
        self.player = plugin.player

    @property
    def extension_name( self ):
        return NAME
    
    @property
    def extension_desc(self):
        return DESCRIPTION
    
    @property
    def ui_str(self):
        return UI_STR        
        
    def create_actions( self, plugin ):
        super( Extension, self ).create_actions( plugin )

        #create love action
        self.action_love = Gtk.Action( 'LoveTrack', _( '_Love Track' ),
                                       _( "Love this track." ), None )
        icon = Gio.FileIcon.new( Gio.File.new_for_path( 
                                      rb.find_plugin_file( self, LOVE_ICON ) ) )
        self.action_love.set_gicon( icon )
        self.action_group.add_action( self.action_love )

        #create ban action
        self.action_ban = Gtk.Action( 'BanTrack', _( '_Ban Track' ),
                                _( "Ban this track." ),
                                None )
        icon = Gio.FileIcon.new( Gio.File.new_for_path( 
                                       rb.find_plugin_file( self, BAN_ICON ) ) )
        self.action_ban.set_gicon( icon )        
        self.action_group.add_action( self.action_ban )       

    def connect_signals( self, plugin ):
        super( Extension, self ).connect_signals( self )
        
        #signal for loving a track
        self.love_id = self.action_love.connect( 'activate', self._love_track )
        
        #signal for baning a track
        self.ban_id = self.action_ban.connect( 'activate', self._ban_track )
        
        #signal to enable/disable the buttons when there's no current entry
        self.benable_id = self.player.connect( 'playing-changed',
                                                lambda sp, playing:
                      self.enable_buttons( self.player.get_playing_entry() ) )
        
    def disconnect_signals( self, plugin ):
        super( Extension, self ).disconnect_signals( self )
        
        #disconnect signals
        self.action_love.disconnect( self.love_id )
        self.action_ban.disconnect( self.ban_id )
        self.player.disconnect( self.benable_id )
        
        #delete variables
        del self.love_id
        del self.ban_id
        del self.benable_id
        
    def destroy_actions( self, plugin ):
        super( Extension, self ).destroy_actions( self )
        
        #delete actions
        del self.action_love
        del self.action_ban    
       
    def enable_buttons( self, entry ):
        enable = entry is not None

        self.action_group.set_property( 'sensitive', enable )
    
    def get_current_track( self ):
        entry = self.player.get_playing_entry()

        if not entry:
            return ( None, None )

        title = unicode( entry.get_string( RB.RhythmDBPropType.TITLE ),
                         'utf-8' )
        artist = unicode( entry.get_string( RB.RhythmDBPropType.ARTIST ), 
                          'utf-8' )

        return ( entry, self.network.get_track( artist, title ) )
             
    def _love_track(self):
        entry, track = self.get_current_track()

        if not entry or not track:
            return

        async( track.love, self._track_loved, track, entry )()

    def _track_loved( self, result, track, entry ):
        #show a different message for fail/success
        if isinstance( result, Exception ):
            titulo = 'Failed to love track'
            texto = 'There was an error in the connection while ' + \
                    'trying to mark the track as loved.'
        else:
            titulo = 'Loved track'
            texto = 'You just marked the track %s - %s as loved' % \
              ( track.get_title().encode( 'utf-8' ), track.get_artist() )

        notify( titulo, texto )

        #bonus: 5 stars to the loved track
        self.db.entry_set( entry, RB.RhythmDBPropType.RATING, 5 )
        self.db.commit()
    
    def _ban_track(self):
        entry, track = self.get_current_track()

        if not entry or not track:
            return

        async( track.ban, self._track_banned, track, entry )()

    def _track_banned( self, result, track, entry ):
        #show a different message for fail/success
        if isinstance( result, Exception ):
            titulo = 'Failed to ban track'
            texto = 'There was an error in the connection while ' + \
                    'trying to mark the track as banned.'
        else:
            titulo = 'Banned track'
            texto = 'You just marked the track %s - %s as banned' % \
              ( track.get_title().encode( 'utf-8' ), track.get_artist() )

        notify( titulo, texto )

        #bonus: 0 stars to the loved track
        self.db.entry_set( entry, RB.RhythmDBPropType.RATING, 0 )
        self.db.commit()
