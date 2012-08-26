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
from abc import ABCMeta, abstractmethod, abstractproperty
from gi.repository import GObject, Gio, Gtk, Peas, RB

import rb

try:
    import LastFMExtensionFingerprinter
    from LastFMExtensionFingerprinter import LastFMFingerprinter as Fingerprinter
except Exception as e:
    Fingerprinter = e

import LastFMExtensionKeys as Keys
import LastFMExtensionUtils
import LastFMExtensionGui as GUI
from LastFMExtensionUtils import asynchronous_call as async, notify
from LastFMExtensionGui import ConfigDialog

import gettext
gettext.install( 'rhythmbox', RB.locale_dir(), unicode=True )

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

'''
Base class for all the extensions managed by this plugin.
'''
class LastFMExtension( object ):
    __metaclass__ = ABCMeta

    def __init__( self, plugin ):
        self.settings = plugin.settings
         
    '''
    Initialises the extension. This initialiser should ALWAYS be called by the
    class' subclasses that overrides it, since it haves an initialising sequence
    all extensions should follow.

    Parameters:
        plugin -- the current instance of the plugin managed by Rhythmbox.
    '''
    def initialise( self, plugin ):
        self.create_actions( plugin )
        self.create_ui( plugin )
        self.connect_signals( plugin )
       
    @property
    def enabled( self ):
        def fget( self ):
            return self.settings[self.settings_key]

        def fset( self, enable ):
            self.settings[self.settings_key] = enable

        return locals()

    @abstractproperty
    def extension_name( self ):
        pass

    @abstractproperty
    def settings_key( self ):
        pass

    @abstractproperty
    def ui_str( self ):
        pass

    def dismantle( self, plugin ):
        self.disconnect_signals( plugin )
        self.destroy_ui( plugin )
        self.destroy_actions( plugin )

    @abstractmethod
    def create_actions( self, plugin ):
        self.action_group = Gtk.ActionGroup( self.extension_name )
        plugin.uim.insert_action_group( self.action_group )

    def create_ui( self, plugin ):
        self.ui_id = plugin.uim.add_ui_from_string( self.ui_str )

    @abstractmethod
    def connect_signals( self, plugin ):
        pass

    @abstractmethod
    def disconnect_signals( self, plugin ):
        pass

    def destroy_ui( self, plugin ):
        plugin.uim.remove_ui( self.ui_id )
        del self.action_group

    @abstractmethod
    def destroy_actions( self, plugin ):
        self.action_group = Gtk.ActionGroup( self.extension_name )
        plugin.uim.insert_action_group( self.action_group )

    def get_configuration_widget( self ):
        return Gtk.CheckButton( "Activate %s " % self )

    def __str__( self, *args, **kwargs ):
        return self.extension_name

'''
This class serves as intermediary between the Plugin and it's Configurable, so
both can access the loaded extensions.
'''    
class LastFMExtensionBag( object ):
    instance = None
    
    def __init__(self):
        self.extensions = {}   
            
    @classmethod
    def get_instance( cls ):
        if not cls.instance:
            cls.instance = LastFMExtensionBag()
            
        return cls.instance

class LastFMExtensionPlugin ( GObject.Object, Peas.Activatable ):
    __gtype_name = 'LastFMExtensionPlugin'
    object = GObject.property( type=GObject.Object )

    def __init__( self ):
        GObject.Object.__init__( self )
        self.settings = Gio.Settings.new( Keys.PATH )

    def do_activate( self ):

        #=======================================================================
        # TODO: Before going to the extensions, the plugin should
        #       - Connect the settings
        #       - Create a network if it's connected, and from there 
        #
        #       The enabling proccess goes like this:
        #       - Iterate over all the extensions names
        #         - Create an instance of the extension
        #         - Initialise the extensions that ARE ENABLED
        #         - Connect a signal to it's settings key to a generic function
        #           that calls 'dismantle' when disabled or 'initialise' when
        #           enabled
        #       The disabling process goes like this:
        #       - Iterate over all the extensions names
        #         - Call dismantle on all enabled extensions
        #         - Disconnect the signals to enable/disable the plugin
        #         - Delete the instance of the extension
        #=======================================================================

        #obtenemos el shell y el player
        shell = self.object
        player = shell.props.shell_player

        #inicializamos el modulo de notificacion
        LastFMExtensionUtils.init( rb.find_plugin_file( self, LASTFM_ICON ) )

        #obtenemos el ui manager
        manager = shell.props.ui_manager

        #creamos el action group
        self.action_group = Gtk.ActionGroup( 'LastFMExtensionActions' )

        #creamos el action love
        action_love = Gtk.Action( 'LoveTrack', _( '_Love Track' ),
                                _( "Love this track." ),
                                None )

        #creamos y asignamos el icono al action love
        icon = Gio.FileIcon.new( Gio.File.new_for_path( 
                                      rb.find_plugin_file( self, LOVE_ICON ) ) )
        action_love.set_gicon( icon )

        #conectamos la señal al método love_track
        self.love_id = action_love.connect( 'activate', self.love_track )

        #agregamos el action al action group
        self.action_group.add_action( action_love )

        #creamos el action ban
        action_ban = Gtk.Action( 'BanTrack', _( '_Ban Track' ),
                                _( "Ban this track." ),
                                None )

        #creamos y asignamos el icono al action love
        icon = Gio.FileIcon.new( Gio.File.new_for_path( 
                                       rb.find_plugin_file( self, BAN_ICON ) ) )
        action_ban.set_gicon( icon )

        #conectamos la señal al método love_track
        self.ban_id = action_ban.connect( 'activate', self.ban_track )

        #agregamos el action al action group
        self.action_group.add_action( action_ban )

        #insertamos el action group y guardamos el ui_id
        manager.insert_action_group( self.action_group, -1 )
        self.ui_id = manager.add_ui_from_string( ui_str )

        #disableamos los botones
        self.enable_buttons( player.get_playing_entry(), self.settings )

        #updateamos la ui
        manager.ensure_update()

        #guardamos la db como atributo
        self.db = shell.get_property( 'db' )

        #guardamos el player en una variable para tenerla mas a mano
        self.player = player

        #conectamos la señal playing_changed para activar o desactivar
        #los botones de love/ban
        self.benable_id = player.connect( 'playing-changed', lambda sp, playing:
              self.enable_buttons( self.player.get_playing_entry(),
                                   self.settings ) )

        #conectamos la señal para conectar o desconectar
        self.settings.connect( 'changed::%s' % Keys.CONNECTED,
                                self.conection_changed, manager )

        #conectamos una señal con la setting de play count para
        #activar/desactivar la funcionalidad cuando sea necesario
        self.settings.connect( 'changed::%s' % Keys.PLAY_COUNT,
                                self.connect_playcount )

        #conectamos una señal con la setting de loved para activar/desactivar
        #la funcionalidad cuando sea necesario
        self.settings.connect( 'changed::%s' % Keys.LOVED, self.connect_loved )

        #conectamos la señal del fingerprinter para activarlo/desactivarlo
        self.settings.connect( 'changed::%s' % Keys.FINGERPRINTER,
                                        self.activate_fingerprinter, manager )

        #inicializamos la network si estan los datos disponibles
        self.conection_changed( self.settings, Keys.CONNECTED, manager )

    def do_deactivate( self ):
        shell = self.object

        #variables que pueden no estar inicializadas
        try:
            self.ui_cm
        except:
            self.ui_cm = None

        try:
            self.fingerprinter
        except:
            self.fingerprinter = None

        #destruimos la ui
        manager = shell.props.ui_manager
        manager.remove_ui( self.ui_id )
        manager.remove_action_group( self.action_group )

        if self.ui_cm:
            manager.remove_action_group( self.finger_action_group )
            manager.remove_ui( self.ui_cm )

        manager.ensure_update()

        #desconectamos las señales
        if self.playcount_id:
            self.player.disconnect( self.playcount_id )

        if self.loved_id:
            self.player.disconnect( self.loved_id )

        #desconectamos las señales de botones
        self.player.disconnect( self.benable_id )
        self.player.disconnect( self.love_id )
        self.player.disconnect( self.ban_id )

        #desasignamos variables
        del self.db
        del self.player
        del self.action_group
        del self.settings

        #borramos el fingerprinter si existe
        if self.fingerprinter:
            del self.finger_action_group
            del self.fingerprinter

        #borramos la network si existe
        if self.network:
            del self.network

    def get_track( self ):
        entry = self.player.get_playing_entry()

        if not entry or not self.settings[Keys.CONNECTED]:
            return ( None, None )

        title = unicode( entry.get_string( RB.RhythmDBPropType.TITLE ), 'utf-8' )
        artist = unicode( entry.get_string( RB.RhythmDBPropType.ARTIST ), 'utf-8' )

        return ( entry, self.network.get_track( artist, title ) )


    def love_track( self, action ):
        entry, track = self.get_track()

        if not entry or not track:
            return

        async( track.love, self.track_loved, track, entry )()

    def track_loved( self, result, track, entry ):
        #mostramos un mensaje diferente segun el resultado
        if isinstance( result, Exception ):
            titulo = 'Failed to love track'
            texto = 'There was an error in the connection while ' + \
                    'trying to mark the track as loved.'
        else:
            titulo = 'Loved track'
            texto = 'You just marked the track %s - %s as loved' % \
              ( track.get_title().encode( 'utf-8' ), track.get_artist() )

        notify( titulo, texto )

        #bonus: ponemos 5 estrellas al track
        self.db.entry_set( entry, RB.RhythmDBPropType.RATING, 5 )
        self.db.commit()

    def ban_track( self, action ):
        entry, track = self.get_track()

        if not entry or not track:
            return

        async( track.ban, self.track_banned, track, entry )()

    def track_banned( self, result, track, entry ):
        #mostramos un mensaje diferente segun el resultado
        if isinstance( result, Exception ):
            titulo = 'Failed to ban track'
            texto = 'There was an error in the connection while ' + \
                    'trying to mark the track as banned.'
        else:
            titulo = 'Banned track'
            texto = 'You just marked the track %s - %s as banned' % \
              ( track.get_title().encode( 'utf-8' ), track.get_artist() )

        notify( titulo, texto )

        #bonus: ponemos 0 estrellas al track
        self.db.entry_set( entry, RB.RhythmDBPropType.RATING, 0 )
        self.db.commit()

    def enable_buttons( self, entry, settings ):
        enable = settings[Keys.CONNECTED] and entry is not None

        self.action_group.set_property( 'sensitive', enable )

    def connect_playcount( self, settings, key ):
        try:
            self.playcount_id
        except:
            self.playcount_id = None

        #si la opcion esta habilitada, conectamos la señal
        if settings[key] and settings[Keys.CONNECTED]:
            self.playcount_id = self.player.connect( 'playing-changed',
                                                     self.playcount_updater )
        #sino, quitamos la señal
        elif self.playcount_id:
            self.player.disconnect( self.playcount_id )

    def playcount_updater ( self, sp, playing ):
        if not playing:
            return

        entry, track = self.get_track()

        if not entry or not track:
            return

        #obtenemos la playcount de lastfm asincronamente
        async( track.get_playcount, self.update_playcount, entry )( True )

    def update_playcount( self, playcount, entry ):
        #get current playcount               
        old_playcount = entry.get_ulong( RB.RhythmDBPropType.PLAY_COUNT )

        if playcount and type( playcount ) is int and old_playcount < playcount:
            self.db.entry_set( entry, RB.RhythmDBPropType.PLAY_COUNT, playcount )
            self.db.commit()

    def connect_loved( self, settings, key ):
        try:
            self.loved_id
        except:
            self.loved_id = None

        #si la opcion esta habilitada, conectamos la señal
        if settings[key] and settings[Keys.CONNECTED]:
            self.loved_id = self.player.connect( 'playing-changed',
                                                 self.loved_updater )
        #sino, quitamos la señal
        elif self.loved_id:
            self.player.disconnect( self.loved_id )

    def loved_updater ( self, sp, playing ):
        if not playing:
            return

        entry, track = self.get_track()

        if not entry or not track:
            return

        #obtenemos el loved asincronamente
        async( track.is_loved, self.update_loved, entry )()

    def update_loved( self, loved, entry ):
        if type( loved ) is bool and loved:
            self.db.entry_set( entry, RB.RhythmDBPropType.RATING, 5 )
            self.db.commit()

    def activate_fingerprinter( self, settings, key, manager ):
        try:
            self.fingerprinter
        except:
            self.fingerprinter = None

        #show error if the module couldn't be loaded
        if settings[key] and isinstance( Fingerprinter, Exception ):
            #this means the lastfp module isn't present
            settings[key] = False
            GUI.show_error_message( Fingerprinter.message )

        #if there's already a fingerprinter, deactivate it
        elif self.fingerprinter:
            manager.remove_action_group( self.finger_action_group )
            manager.remove_ui( self.ui_cm )

            del self.finger_action_group
            del self.ui_cm
            del self.fingerprinter

        #if there isn't a fingerprinter and it's supposed to be, create it
        elif settings[key] and settings[Keys.CONNECTED]:
            #creamos el fingerprinter
            self.fingerprinter = Fingerprinter( self )

            #agregamos la action para el fingerprinter
            self.finger_action_group = Gtk.ActionGroup( 
                                            'LastFMExtensionFingerprinter' )
            action_fingerprint = Gtk.Action( 'FingerprintSong',
                                            _( '_Fingerprint Song' ),
                                            _( "Get this song fingerprinted." ),
                                            None )
            icon = Gio.FileIcon.new( Gio.File.new_for_path( 
                                rb.find_plugin_file( self, LASTFM_ICON ) ) )
            action_fingerprint.set_gicon( icon )

            action_fingerprint.connect( 'activate', self.fingerprint_song )

            self.finger_action_group.add_action( action_fingerprint )
            manager.insert_action_group( self.finger_action_group, -1 )

            #agregamos los menues contextuales
            self.ui_cm = manager.add_ui_from_string( 
                                  LastFMExtensionFingerprinter.ui_context_menu )
        manager.ensure_update()

    def get_selected_songs( self ):
        shell = self.object

        page = shell.props.selected_page
        selected = page.get_entry_view().get_selected_entries()

        return selected

    def fingerprint_song( self, _ ):
        for entry in self.get_selected_songs():
            self.fingerprinter.request_fingerprint( entry )

    def conection_changed( self, settings, key, manager ):
        if settings[key]:
            self.network = pylast.LastFMNetwork( 
                api_key=Keys.API_KEY,
                api_secret=Keys.API_SECRET,
                session_key=settings[Keys.SESSION] )
        else:
            self.network = None

        self.connect_playcount( settings, Keys.PLAY_COUNT )
        self.connect_loved( settings, Keys.LOVED )
        self.activate_fingerprinter( settings, Keys.FINGERPRINTER, manager )

