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
from gi.repository import GObject, Gio, Gtk, Peas, RB

from ConfigParser import SafeConfigParser
from glob import iglob
import os
import imp
import rb

import LastFMExtensionKeys as Keys
import LastFMExtensionUtils
from LastFMExtensionGui import ConfigDialog

import gettext

gettext.install('rhythmbox', RB.locale_dir(), unicode=True)

ui_str = """
<ui>
  <toolbar name="ToolBar">
    <placeholder name="PluginPlaceholder">
      <toolitem name="Loves" action="LoveTrack"/>
      <toolitem name="Ban" action="BanTrack"/>
    </placeholder>
  </toolbar>
</ui>
"""

LASTFM_ICON = 'img/as.png'
LOVE_ICON = 'img/love.png'
BAN_ICON = 'img/ban.png'

# TODO: move all the configuration to the extensions configuration file

class LastFMExtension(GObject.Object):
    '''
    Base class for all the extensions managed by this plugin.
    '''

    # properties
    enabled = GObject.property(type=bool, default=False)

    def __init__(self, plugin, config):
        '''
        By default, all extension are initialized allocating a 'settings'
        attribute that points to a Gio.Settings object binded to the global
        settings of the plugin. Each extension can make use of it to check or
        modify it's settings.
        '''
        super(LastFMExtension, self).__init__()

        self.order = 0
        self.settings = plugin.settings
        self.initialised = False

        # connect signals
        self.conn_id = self.settings.connect('changed::%s' % Keys.CONNECTED,
            self.connection_changed, plugin)
        self.enab_id = self.connect('notify::enabled',
            self.on_enabled_notify, plugin)

        # load the extension configuration
        self.load_configuration(config)

    def destroy(self, plugin, config):
        '''
        This method should be called ALWAYS before the deletion of the object or
        the deactivation of the plugin. It makes sure that all the resources
        this extensions has taken up are freed.
        '''
        # save the plugin configuration
        self.save_configuration(config)

        if self.initialised:
            self.dismantle(plugin)

        self.settings.disconnect(self.conn_id)
        self.disconnect(self.enab_id)

        del self.settings
        del self.conn_id
        del self.enab_id

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

    def load_configuration(self, config):
        '''
        Loads the plugin configuration from a ConfigParser or sets the default
        configuration if the section for the plugin doesn't exist.
        '''
        if self.extension_name in config.sections():
            self.enabled = config.getboolean(self.extension_name, 'enabled')
        else:
            self.enabled = False

    def save_configuration(self, config):
        '''
        Saves the plugin configuration to a ConfigParser.
        '''
        if self.extension_name not in config.sections():
            config.add_section(self.extension_name)

        config.set(self.extension_name, 'enabled',
            'yes' if self.enabled else 'no')

    def connection_changed(self, settings, key, plugin):
        '''
        Callback for changes in the connection of the plugin. It ensures that
        the extension is reenabled (if enabled in the first place) when a
        connection is made and to dismantle the plugin (if initialized) when
        the connection is closed.
        '''
        if not plugin.connected:
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
        if self.ui_str != None:
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
        if self.ui_str != None:
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

        widget = Gtk.CheckButton("Activate %s " % self)
        widget.set_active(self.enabled)
        widget.connect('toggled', toggled_callback)
        widget.set_tooltip_text(self.extension_desc)

        return widget

    def on_enabled_notify(self, *args):
        '''
        Callback for when a setting is changed. The default implementation makes
        sure to initialise or dismantle the extension acordingly.
        '''
        plugin = args[-1]

        if self.enabled:
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

    def destroy(self, plugin, config):
        '''
        This method should be called ALWAYS before the deletion of the object
        or the deactivation of the plugin. It makes sure that all the resources
        this extension has taken up are freed.
        '''
        super(LastFMExtensionWithPlayer, self).destroy(plugin, config)

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
    # extensions configuration file
    EXT_CONFIG = 'extensions.conf'

    def __init__(self, plugin):
        '''
        Initialise the bag, dinamically generating all the plugins.
        '''
        self.extensions = {}
        extensions_class = self.discover_extensions(plugin)

        # generate config config_parser
        config_file = os.path.join(plugin.plugin_info.get_data_dir(),
             self.EXT_CONFIG)

        config_parser = SafeConfigParser()
        config_parser.read(config_file)

        # NOTE ABOUT THE CONFIG:
        # I should probably port all the configuration to this file.
        # It's way easier to manipulate the settings from here, and since now
        # each extension is responsible to return it's configuration widget,
        # there is no need to connect their activation or any other setting
        # modification through Gio (except maybe the connection, but I can
        # simulate that one someway else).

        # load all the extensions and configure them
        for extension_class in extensions_class:
            extension = extension_class(plugin, config_parser)

            self.extensions[extension.extension_name] = extension

    def destroy(self, plugin):
        '''
        Destroy this Bag. This method MUST be called (if you want a clean
        shutdown).
        '''
        config_parser = SafeConfigParser()

        # destroy all the extensions
        for extension in self.extensions.itervalues():
            extension.destroy(plugin, config_parser)

        with file(os.path.join(plugin.plugin_info.get_data_dir(),
            self.EXT_CONFIG), 'w') as config_file:
            config_parser.write(config_file)

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
    def initialise_instance(cls, plugin):
        '''
        Initializes the shared Bag.
        '''
        if not cls.instance:
            cls.instance = LastFMExtensionBag(plugin)

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
        self.settings = Gio.Settings.new(Keys.PATH)

    @property
    def connected(self):
        return self.settings['connected']

    @connected.setter
    def connected(self, connect):
        self.settings['connected'] = connect


    def do_activate(self):
        # inicializamos el modulo de notificacion
        LastFMExtensionUtils.init(rb.find_plugin_file(self, LASTFM_ICON))

        # conectamos la señal para conectar o desconectar
        self.settings.connect('changed::%s' % Keys.CONNECTED,
                                self.conection_changed)

        # asign variables and initialise the network and extensions
        self.conection_changed(self.settings, Keys.CONNECTED)

        self.shell = self.object
        self.uim = self.object.props.ui_manager
        LastFMExtensionBag.initialise_instance(self)

    def do_deactivate(self):
        # borramos la network si existe
        if self.network:
            del self.network

        # TESTING
        LastFMExtensionBag.destroy_instance(self)

        del self.shell
        del self.uim

    def conection_changed(self, settings, key):
        if settings[key]:
            self.network = pylast.LastFMNetwork(
                api_key=Keys.API_KEY,
                api_secret=Keys.API_SECRET,
                session_key=settings[Keys.SESSION])
        else:
            self.network = None
