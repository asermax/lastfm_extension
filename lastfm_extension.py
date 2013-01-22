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

import pylast
from abc import abstractproperty
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Peas
from gi.repository import RB

from glob import iglob
import os
import imp
import rb

import LastFMExtensionKeys as Keys
import LastFMExtensionUtils
from LastFMExtensionGui import ConfigDialog

import gettext

gettext.install('rhythmbox', RB.locale_dir(), unicode=True)

LASTFM_ICON = 'img/as.png'


class LastFMExtension(GObject.Object):
    '''
    Base class for all the extensions managed by this plugin.
    '''

    def __init__(self, plugin, settings):
        '''
        By default, all extension are initialized allocating a 'settings'
        attribute that points to a Gio.Settings object binded to the global
        settings of the plugin. Each extension can make use of it to check or
        modify it's settings.
        '''
        super(LastFMExtension, self).__init__()

        self.order = 0
        self.settings = settings.get_section(self.extension_name)
        self.initialised = False

        # connect signals
        settings.connect(Keys.CONNECTION_SECTION, Keys.CONNECTED,
            self.connection_changed, plugin)
        self.settings.connect('enabled', self.on_enabled_notify, plugin)

        # try to enable
        self.on_enabled_notify(self.enabled, plugin)

    def destroy(self, plugin):
        '''
        This method should be called ALWAYS before the deletion of the object or
        the deactivation of the plugin. It makes sure that all the resources
        this extensions has taken up are freed.
        '''
        if self.initialised:
            self.dismantle(plugin)

        del self.settings

    @abstractproperty
    def extension_name(self):
        '''
        Returns the extension name. Read only property.
        '''
        pass

    @abstractproperty
    def extension_desc(self):
        '''
        Returns a description for the extensions. Read only property.
        '''
        pass

    @property
    def ui_str(self):
        '''
        Returns the ui_str that defines this plugins ui elements to be added to
        Rhythmbox application window. Read only property.
        '''
        pass

    @property
    def enabled(self):
        ''' Indicates if the extension is enabled. '''
        if not self.settings.has_option(Keys.ENABLED):
            self.enabled = False

        return self.settings.getboolean(Keys.ENABLED)

    @enabled.setter
    def enabled(self, enable):
        ''' Allows to enabled/disable the extension. '''
        self.settings.set(Keys.ENABLED, enable)

    def connection_changed(self, connected, plugin):
        '''
        Callback for changes in the connection of the plugin. It ensures that
        the extension is reenabled (if enabled in the first place) when a
        connection is made and to dismantle the plugin (if initialized) when
        the connection is closed.
        '''
        if not connected:
            if self.initialised:
                self.dismantle(plugin)

        elif self.enabled:
            self.initialise(plugin)

    def initialise(self, plugin):
        '''
        Initialises the extension. This initialiser should ALWAYS be called by
        the class' subclasses that overrides it, since it haves an initialising
        sequence all extensions should follow.

        Parameters:
            plugin -- the current instance of the plugin managed by Rhythmbox.
        '''
        self.create_actions(plugin)
        self.create_ui(plugin)
        self.connect_signals(plugin)

        self.network = plugin.network
        self.initialised = True

    def dismantle(self, plugin):
        '''
        Dismantles the extension when it's disabled. This destroy any ui, signa-
        handlers and actions the extension may have created during it's
        initialization.

        Parameters:
            plugin -- the current instance of the plugin managed by Rhythmbox.
        '''
        self.disconnect_signals(plugin)
        self.destroy_ui(plugin)
        self.destroy_actions(plugin)

        self.initialised = False

    def create_actions(self, plugin):
        '''
        Creates all the extension's related actions and inserts them into the
        application.
        This method is always called when the extension is initialised.
        '''
        pass

    def create_ui(self, plugin):
        '''
        Creates the plugin ui within the Rhythmbox application.
        This method is always called when the extension is initialized
        '''
        if self.ui_str:
            self.ui_id = plugin.uim.add_ui_from_string(self.ui_str)

    def connect_signals(self, plugin):
        '''
        Connects all the extension's needed signals for it to function
        correctly.
        This method is always called when the extension is initialized.
        '''
        pass

    def disconnect_signals(self, plugin):
        '''
        Disconnects all the signals connected by the extension.
        This method is always called when the extension is dismantled.
        '''
        pass

    def destroy_ui(self, plugin):
        '''
        Destroys the extension's ui whithin the Rhythmbox application.
        This method is always called when the extension is dismantled.
        '''
        if self.ui_str:
            plugin.uim.remove_ui(self.ui_id)
            del self.ui_id

    def destroy_actions(self, plugin):
        '''
        Dismantles all the actions created by this extension and dissasociates
        them from the Rhythmbox application.
        This method is always called when the extension is dismantled.
        '''
        pass

    def get_configuration_widget(self):
        '''
        Returns a GTK widget to be used as a configuration interface for the
        extension on the plugin's preferences dialog. Every extension is
        responsible of connecting the correspondent signals and managing them
        to configure itself. By default, this methods returns a checkbox that
        allows the user to enable/disable the extension.
        '''
        def toggled_callback(checkbox):
            self.enabled = checkbox.get_active()

        widget = Gtk.CheckButton(_("Activate %s ") % self)
        widget.set_active(self.enabled)
        widget.connect('toggled', toggled_callback)
        widget.set_tooltip_text(self.extension_desc)

        return _('General'), widget

    def on_enabled_notify(self, enabled, plugin):
        '''
        Callback for when a setting is changed. The default implementation makes
        sure to initialise or dismantle the extension acordingly.
        '''
        if enabled:
            if not self.initialised and plugin.connected:
                self.initialise(plugin)

        elif self.initialised:
            self.dismantle(plugin)

    def __str__(self, *args, **kwargs):
        return self.extension_name

class LastFMExtensionWithPlayer(LastFMExtension):
    '''
    Base class for the extensions that want to use the current track in their
    activity. It automatically connects the playing-changed signal and
    implements an utility method to get the current track data.
    '''

    def __init__(self, plugin, config):
        '''
        Initialises the plugin, saving the shell player on self.player
        '''
        self.player = plugin.shell.props.shell_player
        self.db = plugin.shell.props.db

        super(LastFMExtensionWithPlayer, self).__init__(plugin, config)

    def destroy(self, plugin):
        '''
        This method should be called ALWAYS before the deletion of the object
        or the deactivation of the plugin. It makes sure that all the resources
        this extension has taken up are freed.
        '''
        super(LastFMExtensionWithPlayer, self).destroy(plugin)

        del self.player
        del self.db

    def connect_signals(self, plugin):
        '''
        Connects the playing-changed signal to the callback playing_changed.
        '''
        super(LastFMExtensionWithPlayer, self).connect_signals(plugin)

        # connect to the playing change signal
        self.playing_changed_id = self.player.connect('playing-changed',
                                                 self.playing_changed, plugin)

    def disconnect_signals(self, plugin):
        '''
        Disconnects the playing-changed signal.
        '''
        super(LastFMExtensionWithPlayer, self).disconnect_signals(plugin)

        # disconnect signals
        self.player.disconnect(self.playing_changed_id)

        # delete variables
        del self.playing_changed_id

    def playing_changed(self, shell_player, playing, plugin):
        '''
        Callback for the playing-changed signal. Subclasses should probably
        override this method to do whatever they want with it.
        '''
        pass

    def get_current_track(self):
        '''
        Utility method that gaves easy access to the current playing track.
        It returns the current entry and a pylast Track instance pointing at
        the given track.
        '''
        entry = self.player.get_playing_entry()

        if not entry:
            return (None, None)

        title = unicode(entry.get_string(RB.RhythmDBPropType.TITLE),
                         'utf-8')
        artist = unicode(entry.get_string(RB.RhythmDBPropType.ARTIST),
                          'utf-8')

        return (entry, self.network.get_track(artist, title))

class LastFMExtensionBag(object):
    '''
    This class serves as intermediary between the Plugin and it's Configurable,
    so both can access the loaded extensions.
    Also it works as a sort of factory, responsible of initialising and
    destroying all configured extensions.
    '''

    # unique instance of this Bag
    instance = None

    # extensions directory
    EXT_DIR = 'extensions'

    def __init__(self, plugin, settings):
        '''
        Initialise the bag, dinamically generating all the plugins.
        '''
        self.settings = settings
        self.extensions = {}
        extensions_class = self.discover_extensions(plugin)

        # load all the extensions and configure them
        for extension_class in extensions_class:
            extension = extension_class(plugin, settings)

            self.extensions[extension.extension_name] = extension

    def destroy(self, plugin):
        '''
        Destroy this Bag. This method MUST be called (if you want a clean
        shutdown).
        '''
        # destroy all the extensions
        for extension in self.extensions.itervalues():
            extension.destroy(plugin)

    def discover_extensions(self, plugin):
        extensions = []
        ext_dir = rb.find_plugin_file(plugin, self.EXT_DIR)

        # iterate through all py files on the extensions directory
        for py_file in iglob(os.path.join(ext_dir, '*.py')):
            module_name = os.path.basename(py_file).split(os.path.extsep)[0]

            fp, path, desc = imp.find_module(module_name, [ext_dir])

            try:
                module = imp.load_module(module_name, fp, path, desc)

                # if there is an extension class, this is an extension
                ext_class = getattr(module, 'Extension')

                if ext_class:
                    extensions.append(ext_class)

            except Exception as ex:
                print ex.message
            finally:
                if fp:
                    fp.close()

        return extensions

    @classmethod
    def initialise_instance(cls, plugin, settings):
        '''
        Initializes the shared Bag.
        '''
        if not cls.instance:
            cls.instance = LastFMExtensionBag(plugin, settings)

    @classmethod
    def destroy_instance(cls, plugin):
        '''
        Destroys the shared Bag.
        '''
        if cls.instance:
            cls.instance.destroy(plugin)

    @classmethod
    def get_instance(cls):
        '''
        Returns the shared Bag.
        '''
        return cls.instance

class LastFMExtensionPlugin (GObject.Object, Peas.Activatable):
    __gtype_name = 'LastFMExtensionPlugin'
    object = GObject.property(type=GObject.Object)

    def __init__(self):
        GObject.Object.__init__(self)

    @property
    def connected(self):
        if not self.settings.has_option(Keys.CONNECTED):
            self.settings.set(Keys.CONNECTED, False)

        return self.settings.getboolean(Keys.CONNECTED)

    def do_activate(self):
        # initialise the utils module
        LastFMExtensionUtils.init(rb.find_plugin_file(self, LASTFM_ICON))

        # create the settings for the plugin
        settings = LastFMExtensionUtils.Settings(self)

        # get the settings section for the connection
        self.settings = settings.get_section(Keys.CONNECTION_SECTION)

        # connect a signal to the connected property
        self.settings.connect(Keys.CONNECTED, self.conection_changed)

        # asign variables and initialise the network and extensions
        self.conection_changed(self.connected)

        # initialise the extensions bag
        self.shell = self.object
        self.uim = self.object.props.ui_manager
        LastFMExtensionBag.initialise_instance(self, settings)

    def do_deactivate(self):
        # borramos la network si existe
        if self.network:
            del self.network

        # TESTING
        LastFMExtensionBag.destroy_instance(self)

        del self.shell
        del self.uim

    def conection_changed(self, connected):
        if connected:
            self.network = pylast.LastFMNetwork(
                api_key=Keys.API_KEY,
                api_secret=Keys.API_SECRET,
                session_key=self.settings.get(Keys.SESSION))
        else:
            self.network = None
