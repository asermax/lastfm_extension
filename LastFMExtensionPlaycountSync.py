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

from lastfm_extension import LastFMExtensionWithPlayer
from gi.repository import RB

from LastFMExtensionUtils import asynchronous_call as async

#name and description
NAME = "LastFMPlaycountSync"
DESCRIPTION = "Sync your tracks playcount with Last.FM!"

class Extension( LastFMExtensionWithPlayer ):
    def __init__( self, plugin ):
        super( Extension, self ).__init__( plugin )

        self.db = plugin.shell.props.db

    @property
    def extension_name( self ):
        return NAME

    @property
    def extension_desc( self ):
        return DESCRIPTION

    def playing_changed( self, shell_player, playing, plugin ):        
        #check if the player is playing a song
        if not playing:
            return

        #get the track
        entry, track = self.get_current_track()

        if not entry or not track:
            return

        #obtenemos la playcount de lastfm asincronamente
        async( track.get_playcount, self._update_playcount, entry )( True )

    def _update_playcount( self, playcount, entry ):
        #get current playcount               
        old_playcount = entry.get_ulong( RB.RhythmDBPropType.PLAY_COUNT )

        #update the playcount if it's valid and is higher than the local one
        if playcount and type( playcount ) is int and old_playcount < playcount:
            self.db.entry_set( entry, RB.RhythmDBPropType.PLAY_COUNT, playcount )
            self.db.commit()



