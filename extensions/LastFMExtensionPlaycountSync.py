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

from LastFMExtensionUtils import asynchronous_call as async, idle_add

#name and description
NAME = "LastFMPlaycountSync"
DESCRIPTION = "Sync your tracks playcount with Last.FM!"

class Extension(LastFMExtensionWithPlayer):
    '''
    This extensions allows the player to synchronize a track playcount with the
    one saved on LastFM servers.
    '''

    def __init__(self, plugin, config):
        '''
        Initializes the extension.
        '''
        super(Extension, self).__init__(plugin, config)

        self.order = 2

    @property
    def extension_name(self):
        '''
        Returns the extension name. Read only property.
        '''
        return NAME

    @property
    def extension_desc(self):
        '''
        Returns a description for the extensions. Read only property.
        '''
        return DESCRIPTION

    def playing_changed(self, shell_player, playing, plugin):
        '''
        Callback for the playing-changed signal. Initiates the process to
        retrieve the playcount from LastFM.
        '''
        #check if the player is playing a song
        if not playing:
            return

        #get the track
        entry, track = self.get_current_track()

        if not entry or not track:
            return

        #obtenemos la playcount de lastfm asincronamente
        async(track.get_playcount, self._update_playcount, entry)(True)

    def _update_playcount(self, playcount, entry):
        '''
        Callback that actually sets the playcount, once retrieved.
        The playcount is updated ONLY if the one retreived from LastFM is
        HIGHER than the one stored locally.
        '''
        #get current playcount               
        old_playcount = entry.get_ulong(RB.RhythmDBPropType.PLAY_COUNT)

        #update the playcount if it's valid and is higher than the local one
        if playcount and type(playcount) is int and old_playcount < playcount:
            def set_playcount(entry, playcount):
                self.db.entry_set(entry, RB.RhythmDBPropType.PLAY_COUNT,
                    playcount)
                self.db.commit()

            idle_add(set_playcount, entry, playcount)



