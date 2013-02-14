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
from gi.repository import RB, Gtk, GObject

from LastFMExtensionUtils import asynchronous_call as async, idle_add, \
    bind_properties

# name and description
NAME = "LastFMPlaycountSync"
DESCRIPTION = "Sync your tracks playcount with Last.FM!"

class Extension(LastFMExtensionWithPlayer):
    '''
    This extensions allows the player to synchronize a track playcount with the
    one saved on LastFM servers.
    '''

    def __init__(self, plugin, settings):
        '''
        Initializes the extension.
        '''
        super(Extension, self).__init__(plugin, settings)

        self._full_sync_man = FullPlaycountSyncManager(self.db,
            plugin.shell.props.library_source.props.base_query_model)

        if plugin.network:
            self._full_sync_man.network = plugin.network

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

    def connection_changed(self, connected, plugin):
        super(Extension, self).connection_changed(connected, plugin)

        self._full_sync_man.network = plugin.network if connected else None

    def get_configuration_widget(self):
        '''
        Returns a GTK widget to be used as a configuration interface for the
        extension on the plugin's preferences dialog. Every extension is
        responsible of connecting the correspondent signals and managing them
        to configure itself. By default, this methods returns a checkbox that
        allows the user to enable/disable the extension.
        '''
        enable_widget = super(Extension, self).get_configuration_widget()[1]
        enable_widget.set_label(_('Enable per-play sync'))
        enable_widget.set_margin_left(25)

        # create the actual widget
        title = Gtk.Label(xalign=0)
        title.set_markup('<b>%s</b>' % _('Playcount Sync:'))

        widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        widget.pack_start(title, False, False, 0)
        widget.pack_start(enable_widget, False, False, 0)

        # add the full sync widtet
        self._full_sync_man.add_to_widget(widget)

        return _('Sync'), widget

    def playing_changed(self, shell_player, playing, plugin):
        '''
        Callback for the playing-changed signal. Initiates the process to
        retrieve the playcount from LastFM.
        '''
        # check if the player is playing a song
        if not playing:
            return

        # get the track
        entry, track = self.get_current_track()

        if not entry or not track:
            return

        # create a track sync and start the syncing
        track_sync = TrackPlaycountSync(self.db, entry, track)
        track_sync.start()


class TrackPlaycountSync(GObject.Object):
    # signals
    __gsignals__ = {
        'done': (GObject.SIGNAL_RUN_LAST, None, ())
        }

    def __init__(self, db, entry, track):
        super(TrackPlaycountSync, self).__init__()

        self._db = db
        self._entry = entry
        self._track = track

    def start(self):
        async(self._track.get_playcount, self._update_playcount,
            self._entry)(True)

    def _update_playcount(self, playcount, entry):
        '''
        Callback that actually sets the playcount, once retrieved.
        The playcount is updated ONLY if the one retreived from LastFM is
        HIGHER than the one stored locally.
        '''
        # get current playcount
        old_playcount = entry.get_ulong(RB.RhythmDBPropType.PLAY_COUNT)

        # update the playcount if it's valid and is higher than the local one
        if playcount and type(playcount) is int and old_playcount < playcount:
            def set_playcount(entry, playcount):
                self._db.entry_set(entry, RB.RhythmDBPropType.PLAY_COUNT,
                    playcount)
                self._db.commit()

            idle_add(set_playcount, entry, playcount)

        # emit the done signal
        idle_add(self.emit, 'done')


class FullPlaycountSync(GObject.Object):
    # signals
    __gsignals__ = {
        'done': (GObject.SIGNAL_RUN_LAST, None, ())
        }

    progress = GObject.property(type=float, default=1)

    def __init__(self, network, db, query_model):
        super(FullPlaycountSync, self).__init__()
        self._network = network
        self._db = db
        self._query_model = query_model
        self._cancel = False

    def _do_sync(self, iterator, total, synced):
        try:
            # get the entry
            entry = self._query_model[iterator.next().path][0]
        except StopIteration:
            self._cancel = True

        if self._cancel:
            # if canceled (either the iteration finished or user canceled)
            # emit the done signal
            self.emit('done')

        else:
            # if not, go ahead and poll the next playcount
            # update the progress
            synced += 1
            self.progress = synced / total

            # get the lastfm track
            title = unicode(entry.get_string(RB.RhythmDBPropType.TITLE),
                         'utf-8')
            artist = unicode(entry.get_string(RB.RhythmDBPropType.ARTIST),
                          'utf-8')

            track = self._network.get_track(artist, title)

            # create the track sync and connect to the done signal
            track_sync = TrackPlaycountSync(self._db, entry, track)
            track_sync.connect('done', lambda _, *data: self._do_sync(*data),
                iterator, total, synced)

            # start the track sync
            track_sync.start()

    def start(self):
        self.progress = 0.

        self._do_sync(iter(self._query_model), len(self._query_model), 0.)

    def cancel(self):
        self._cancel = True


class FullPlaycountSyncManager(object):
    def __init__(self, db, query_model):
        self._network = None
        self._db = db
        self._query_model = query_model
        self._full_sync = None
        self._start_widget = None
        self._stop_widget = None

    @property
    def network(self):
        return self._network

    @network.setter
    def network(self, network):
        self._network = network

        if self._start_widget:
            idle_add(self._start_widget.set_sensitive, network is not None)

    def _init_widgets(self, box):
        # start widget
        self._start_widget = Gtk.Button(label=_('Do a full sync'),
            margin_left=25)

        # stop widget
        self._stop_widget = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
            margin_left=25)

        progress_bar = Gtk.ProgressBar()
        self._stop_widget.pack_start(progress_bar, False, False, 0)

        stop_button = Gtk.Button(label=_('Stop'), margin_left=5)
        self._stop_widget.pack_start(stop_button, False, False, 0)

        # callbacks for widgets
        def do_full_sync(start_button):
            self._start_full_sync()
            self._wire_sync_progress(progress_bar)

            # hide this button and show the other
            box.remove(self._start_widget)
            box.pack_start(self._stop_widget, False, False, 0)
            box.show_all()

        self._start_widget.connect('clicked', do_full_sync)

        def cancel_full_sync(stop_button):
            # cancel the sync
            self._full_sync.cancel()

            # hide this widget and show the start button
            box.remove(self._stop_widget)
            box.pack_start(self._start_widget, False, False, 0)
            box.show_all()

        stop_button.connect('clicked', cancel_full_sync)

    def add_to_widget(self, box):
        # choose and add the correct widget
        self._init_widgets(box)

        if self._full_sync:
            box.pack_start(self._stop_widget, False, False, 0)
        else:
            box.pack_start(self._start_widget, False, False, 0)

            if not self.network:
                self._start_widget.set_sensitive(False)

    def _wire_sync_progress(self, progress_bar):
        # connect the progress bar progress
        bind_properties(self._full_sync, progress_bar, 'progress',
            'fraction')

    def _start_full_sync(self):
        # create and start the sync
        self._full_sync = FullPlaycountSync(self._network, self._db,
            self._query_model)
        self._full_sync.start()

        # connect to the done signal
        def full_sync_done(full_sync):
            self._full_sync = None

        self._full_sync.connect('done', full_sync_done)
