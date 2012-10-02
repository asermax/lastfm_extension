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
NAME = "LastFMLovedSync"
DESCRIPTION = "Sync your tracks loved status with Last.FM!"

class Extension(LastFMExtensionWithPlayer):
    '''
    This extensions allows the player to synchronize a track loved status the
    rating saved locally.
    '''

    def __init__(self, plugin, config):
        '''
        Initializes the extension.
        '''
        super(Extension, self).__init__(plugin, config)

        self.order = 1

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
        retrieve the loved status from LastFM.
        '''
        #check if the player is playing a song
        if not playing:
            return

        #get the track
        entry, track = self.get_current_track()

        if not entry or not track:
            return

        #obtenemos la playcount de lastfm asincronamente
        async(track.is_loved, self._update_loved, entry)()

    def _update_loved(self, loved, entry):
        '''
        Callback that actually sets the rating on the track, once retrieved the
        loved status of it.
        '''
        if type(loved) is bool and loved:
            def set_rating(entry):
                self.db.entry_set(entry, RB.RhythmDBPropType.RATING, 5)
                self.db.commit()

            idle_add(set_rating, entry)



