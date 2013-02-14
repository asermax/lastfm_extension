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
from gi.repository import Gtk, Gio, RB

import rb

from LastFMExtensionUtils import asynchronous_call as async, notify, idle_add

# name and description
NAME = "LastFMLoveBan"
DESCRIPTION = "Add the Love and Ban buttons to your Toolbar!"

# constants
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

# icon paths
LOVE_ICON = 'img/love.png'
BAN_ICON = 'img/ban.png'

# settings keys
LOVE_VISIBLE = 'love_visible'
BAN_VISIBLE = 'ban_visible'

class Extension(LastFMExtensionWithPlayer):
    '''
    This extensions adds the posibility to love or ban the current playing track.
    '''
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

    @property
    def ui_str(self):
        '''
        Returns the ui_str that defines this plugins ui elements to be added to
        Rhythmbox application window. Read only property.
        '''
        return UI_STR

    @property
    def enabled(self):
        return True

    @enabled.setter
    def enabled(self, enabled):  # @DuplicatedSignature
        pass

    @property
    def love_visible(self):
        if not self.settings.has_option(LOVE_VISIBLE):
            self.love_visible = True

        return self.settings.getboolean(LOVE_VISIBLE)

    @love_visible.setter
    def love_visible(self, visible):
        self.settings.set(LOVE_VISIBLE, visible)

        try:
            self.action_love.set_visible(visible)
        except:
            pass

    @property
    def ban_visible(self):
        if not self.settings.has_option(BAN_VISIBLE):
            self.ban_visible = True

        return self.settings.getboolean(BAN_VISIBLE)

    @ban_visible.setter
    def ban_visible(self, visible):
        self.settings.set(BAN_VISIBLE, visible)

        try:
            self.action_ban.set_visible(visible)
        except:
            pass

    def create_actions(self, plugin):
        '''
        Creates all the extension's related actions and inserts them into the
        application.
        This method is always called when the extension is initialised.
        '''
        super(Extension, self).create_actions(plugin)

        # create the action group
        self.action_group = Gtk.ActionGroup(self.extension_name)

        # create love action
        self.action_love = Gtk.Action('LoveTrack', _('_Love'),
            _("Love this track."), None, visible=self.love_visible)

        icon = Gio.FileIcon.new(Gio.File.new_for_path(
            rb.find_plugin_file(plugin, LOVE_ICON)))

        self.action_love.set_gicon(icon)
        self.action_group.add_action(self.action_love)

        # create ban action
        self.action_ban = Gtk.Action('BanTrack', _('_Ban'),
            _("Ban this track."), None, visible=self.ban_visible)

        icon = Gio.FileIcon.new(Gio.File.new_for_path(
            rb.find_plugin_file(plugin, BAN_ICON)))

        self.action_ban.set_gicon(icon)
        self.action_group.add_action(self.action_ban)

        # enable the buttons depending if there's a song playing
        self.playing_changed()

        # insert the action group to the uim
        plugin.uim.insert_action_group(self.action_group)

    def connect_signals(self, plugin):
        '''
        Connects all the extension's needed signals for it to function
        correctly.
        This method is always called when the extension is initialized.
        '''
        super(Extension, self).connect_signals(plugin)

        # signal for loving a track
        self.love_id = self.action_love.connect('activate', self._love_track)

        # signal for baning a track
        self.ban_id = self.action_ban.connect('activate', self._ban_track)

    def disconnect_signals(self, plugin):
        '''
        Disconnects all the signals connected by the extension.
        This method is always called when the extension is dismantled.
        '''
        super(Extension, self).disconnect_signals(plugin)

        # disconnect signals
        self.action_love.disconnect(self.love_id)
        self.action_ban.disconnect(self.ban_id)

        # delete variables
        del self.love_id
        del self.ban_id

    def destroy_actions(self, plugin):
        '''
        Dismantles all the actions created by this extension and dissasociates
        them from the Rhythmbox application.
        This method is always called when the extension is dismantled.
        '''
        super(Extension, self).destroy_actions(plugin)

        # remove and destroy the action group
        plugin.uim.remove_action_group(self.action_group)
        del self.action_group

        # delete actions
        del self.action_love
        del self.action_ban

    def get_configuration_widget(self):
        '''
        Returns a GTK widget to be used as a configuration interface for the
        extension on the plugin's preferences dialog. Every extension is
        responsible of connecting the correspondent signals and managing them
        to configure itself. By default, this methods returns a checkbox that
        allows the user to enable/disable the extension.
        '''
        # love visible checkbox
        def love_visible_callback(checkbox):
            self.love_visible = checkbox.get_active()

        love_checkbox = Gtk.CheckButton(_('Love'), margin_left=25,
            active=self.love_visible, tooltip_text=_('Show Love button'))
        love_checkbox.connect('toggled', love_visible_callback)

        # ban visible checkobx
        def ban_visible_callback(checkbox):
            self.ban_visible = checkbox.get_active()

        ban_checkbox = Gtk.CheckButton(_('Ban'), active=self.ban_visible,
            tooltip_text=_('Show Ban button'))
        ban_checkbox.connect('toggled', ban_visible_callback)

        # build all the widget
        title = Gtk.Label(xalign=0)
        title.set_markup('<b>%s</b>' % _('Enable buttons:'))

        widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        widget.pack_start(title, False, False, 0)

        buttons_box = Gtk.Box(spacing=5)
        buttons_box.pack_start(love_checkbox, False, False, 0)
        buttons_box.pack_start(ban_checkbox, False, False, 0)

        widget.pack_start(buttons_box, False, False, 0)

        return _('General'), widget

    def playing_changed(self, *args):
        '''
        Callback for the playing-changed signal. Enables or disables the buttons
        for the extension.
        '''
        self._enable_buttons(self.player.get_playing_entry() is not None)

    def _enable_buttons(self, enable):
        '''
        Allows to enable or disable the extension's buttons.
        '''
        self.action_group.set_property('sensitive', enable)

    def _love_track(self, _):
        '''
        Callback for when the Love action is called. It initiates the process
        for loving a track.
        '''
        entry, track = self.get_current_track()

        if not entry or not track:
            return

        async(track.love, self._track_loved, track, entry)()

    def _track_loved(self, result, track, entry):
        '''
        Callback for when the track is finally marked as loved or when the
        action failed for some reason. It informs the user of the result of
        the action.
        '''
        # show a different message for fail/success
        if isinstance(result, Exception):
            titulo = 'Failed to love track'
            texto = 'There was an error in the connection while ' + \
                    'trying to mark the track as loved.'

            print result
        else:
            titulo = 'Loved track'
            texto = 'You just marked the track %s - %s as loved' % \
              (track.get_title().encode('utf-8'), track.get_artist())

            # bonus: 5 stars to the loved track
            idle_add(self._set_rating, entry, 5)

        notify(titulo, texto)

    def _ban_track(self, _):
        '''
        Callback for when the Ban action is called. It initiates the process
        for banning a track.
        '''
        entry, track = self.get_current_track()

        if not entry or not track:
            return

        async(track.ban, self._track_banned, track, entry)()

    def _track_banned(self, result, track, entry):
        '''
        Callback for when the track is finally marked as banned or when the
        action failed for some reason. It informs the user of the result of
        the action.
        '''
        # show a different message for fail/success
        if isinstance(result, Exception):
            titulo = 'Failed to ban track'
            texto = 'There was an error in the connection while ' + \
                    'trying to mark the track as banned.'

            print result
        else:
            titulo = 'Banned track'
            texto = 'You just marked the track %s - %s as banned' % \
              (track.get_title().encode('utf-8'), track.get_artist())

            # bonus: 0 stars to the loved track
            idle_add(self._set_rating, entry, 0)

        notify(titulo, texto)

    def _set_rating(self, entry, rating):
        self.db.entry_set(entry, RB.RhythmDBPropType.RATING, rating)
        self.db.commit()
