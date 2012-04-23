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
from gi.repository import GObject, Gio, Gtk, Peas, RB

import rb
import LastFMExtensionKeys as Keys
import LastFMExtensionUtils
from LastFMExtensionUtils import asynchronous_call as async, notify
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

class LastFMExtensionPlugin (GObject.Object, Peas.Activatable):
    __gtype_name = 'LastFMExtensionPlugin'
    object = GObject.property(type=GObject.Object)

    def __init__(self):
        GObject.Object.__init__(self)
        self.settings = Gio.Settings.new(Keys.PATH)

    def do_activate(self):
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
        action_love = Gtk.Action( 'LoveTrack', _('_Love Track'),
                                _("Love this track."),
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
        action_ban = Gtk.Action('BanTrack', _('_Ban Track'),
                                _("Ban this track."),
                                None)

        #creamos y asignamos el icono al action love
        icon = Gio.FileIcon.new( Gio.File.new_for_path( 
                                       rb.find_plugin_file( self, BAN_ICON ) ) )
        action_ban.set_gicon( icon )

        #conectamos la señal al método love_track
        self.ban_id = action_ban.connect( 'activate', self.ban_track)

        #agregamos el action al action group
        self.action_group.add_action( action_ban )

        #insertamos el action group y guardamos el ui_id
        manager.insert_action_group( self.action_group, -1 )
        self.ui_id = manager.add_ui_from_string( ui_str )

        #disableamos los botones
        self.enable_buttons( False )

        #updateamos la ui
        manager.ensure_update()        
        
        #guardamos la db como atributo
        self.db = shell.get_property('db')

        #guardamos el player en una variable para tenerla mas a mano
        self.player = player
        
        #conectamos la señal playing_changed para activar o desactivar
        #los botones de love/ban
        self.benable_id = player.connect( 'playing-changed', lambda sp, playing: 
              self.enable_buttons( playing and self.settings[Keys.CONNECTED] ) )
              
        #conectamos la señal para conectar o desconectar
        self.settings.connect( 'changed::connected', self.conection_changed )      
        
        #conectamos una señal con la setting de play count para
        #activar/desactivar la funcionalidad cuando sea necesario
        self.playcount_id = None
        self.settings.connect( 'changed::%s' % Keys.PLAY_COUNT,
                                self.connect_playcount )
                                              
        #conectamos una señal con la setting de loved para activar/desactivar
        #la funcionalidad cuando sea necesario
        self.loved_id = None
        self.settings.connect( 'changed::%s' % Keys.LOVED, self.connect_loved )        
        
        #inicializamos la network si estan los datos disponibles
        self.conection_changed( self.settings, Keys.CONNECTED )           
                           
        
    def do_deactivate(self):
        shell = self.object

        #destruimos la ui
        manager = shell.props.ui_manager
        manager.remove_ui(self.ui_id)
        manager.remove_action_group(self.action_group)
        manager.ensure_update()
        
        #desconectamos las señal de playcount y loved si estan conectado
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
        
        #borramos la network si existe
        if self.network:
            del self.network
            
    def get_track( self ):
        entry = self.player.get_playing_entry()
        
        if not entry or not self.settings[Keys.CONNECTED]:
        	return ( None, None )

        title = unicode( entry.get_string(RB.RhythmDBPropType.TITLE ), 'utf-8' )
        artist = unicode( entry.get_string(RB.RhythmDBPropType.ARTIST ), 'utf-8' )

        return ( entry, self.network.get_track( artist, title ) )


    def love_track( self, action ):
        entry, track = self.get_track()
        
        if not entry or not track:
        	return
                
        #armamos el titulo y mensaje de la notificacion
        titulo = 'Loved track'
        texto = 'You just marked the track %s - %s as loved' % \
              ( track.get_title(), track.get_artist() )

        async( track.love,
               lambda _, title, text: notify( title, text),
               titulo, texto )()
               
        #bonus: ponemos 5 estrellas al track
        self.db.entry_set(entry, RB.RhythmDBPropType.RATING, 5)        	

    def ban_track( self, action ):
        entry, track = self.get_track()
        
        if not entry or not track:
        	return

        #armamos el titulo y mensaje de la notificacion
        titulo = 'Banned track'
        texto = 'You just marked the track %s - %s as banned' % \
              ( track.get_title(), track.get_artist() )

        async( track.ban,
        	   lambda _, title, text: notify( title, text),
               titulo, texto )()
        
        #bonus: ponemos 0 estrellas al track
        self.db.entry_set(entry, RB.RhythmDBPropType.RATING, 0)       

    def enable_buttons( self, enable ):
        self.action_group.set_property( 'sensitive', enable )           	

    def connect_playcount( self, settings, key ):
        #si la opcion esta habilitada, conectamos la señal
        if settings[key] and self.settings[Keys.CONNECTED]:
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
                
        if playcount and type(playcount) is int and old_playcount < playcount:
            self.db.entry_set( entry, RB.RhythmDBPropType.PLAY_COUNT, playcount )  
            
    def connect_loved( self, settings, key ):
		#si la opcion esta habilitada, conectamos la señal
        if settings[key] and self.settings[Keys.CONNECTED]:
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
    	if loved:
    		self.db.entry_set(entry, RB.RhythmDBPropType.RATING, 5)   	      
            
    def conection_changed( self, settings, key ):
        if settings[key]:
            self.network = pylast.LastFMNetwork(
                api_key=Keys.API_KEY,
                api_secret=Keys.API_SECRET,
                session_key=self.settings[Keys.SESSION] )
        else:
            self.network = None
            
        self.connect_playcount( self.settings, Keys.PLAY_COUNT )
        self.connect_loved( self.settings, Keys.LOVED )

