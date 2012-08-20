# -*- Mode: python; coding: utf-8; tab-width: 4; indent-tabs-mode: s; -*-
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

from gi.repository import Gtk, Gio, GObject, PeasGtk
from LastFMExtensionUtils import asynchronous_call as async
import LastFMExtensionKeys as Keys
import rb
import pylast, webbrowser

DIALOG_FILE = 'lastfmExtensionConfigDialog.glade'
DIALOG = 'boxPrincipal'
LOGIN_LABEL = 'labelLogin'
LOGIN_BUTTON = 'buttonLogin'
PLAYCOUNT_CHECKBOX = 'checkbuttonPlayCount'
LOVED_CHECKBOX = 'checkbuttonLoved'
FINGERPRINTER_CHECKBOX = 'checkbuttonFingerprinter'

'''
Función auxiliar para mostrar mensajes de error con un dialog.
'''
def show_error_message( message ):
	dialog = Gtk.MessageDialog( None, 0, Gtk.MessageType.ERROR,
								Gtk.ButtonsType.CLOSE, message )
	
	dialog.run()
	dialog.destroy()

'''
Diálogo que permite obtener y persistir ciertas configuraciones,
utilizando Gio para persistir las mismas.
'''
class ConfigDialog( GObject.Object, PeasGtk.Configurable ):
    __gtype_name__ = 'LastFMExtensionConfigDialog'
    object = GObject.property(type=GObject.Object)

    def __init__(self):
        GObject.Object.__init__( self )
        self.settings = Gio.Settings( Keys.PATH )

    def do_create_configure_widget( self ):
        #creamos un builder y agregamos el archivo de gui
        builder = Gtk.Builder()
        builder.add_from_file( rb.find_plugin_file( self, DIALOG_FILE ) )
                
        if self.settings[Keys.CONNECTED]:
            label_text = 'Logged'
            button_label = 'Logout'
            button_callback = self._logout
            
        else:
            label_text = 'Not Logged'
            button_label = 'Login' 
            button_callback = self._login
            
        #obtenemos los componentes del dialog a modificar
        label = builder.get_object( LOGIN_LABEL )
        button = builder.get_object( LOGIN_BUTTON )
        playcount_checkbox = builder.get_object( PLAYCOUNT_CHECKBOX )
        loved_checkbox = builder.get_object( LOVED_CHECKBOX )
        fingerprint_checkbox = builder.get_object( FINGERPRINTER_CHECKBOX )
            
        #preparamos la gui   
        label.set_text( label_text )  
           
        button.set_label( button_label )
        self._b_id = button.connect( 'clicked', button_callback, label )
        
        playcount_checkbox.set_active( self.settings[Keys.PLAY_COUNT] )
        playcount_checkbox.connect( 'toggled', self._toggle, Keys.PLAY_COUNT )
        
        loved_checkbox.set_active( self.settings[Keys.LOVED] )    
        loved_checkbox.connect( 'toggled', self._toggle, Keys.LOVED )                           
                    
        fingerprint_checkbox.set_active( self.settings[Keys.FINGERPRINTER] )    
        fingerprint_checkbox.connect( 'toggled', 
        								  self._toggle, Keys.FINGERPRINTER ) 
                    
        return builder.get_object( DIALOG )
    
    def _toggle( self, checkbutton, key ):
        self.settings[key] = checkbutton.get_active()
        checkbutton.set_active( self.settings[key] )
       
    def _login( self, button, label ):               
        #mostramos la pagina para aceptar la conexion
        network = pylast.LastFMNetwork( Keys.API_KEY, Keys.API_SECRET )
        skey_generator = pylast.SessionKeyGenerator( network )
        url = skey_generator.get_web_auth_url()
        
        #desconectamos la señal anterior del boton
        button.disconnect( self._b_id )
        
        #cambiamos el label y conectamos la nueva señal
        button.set_label( 'Press again once allowed' )
        self._b_id = button.connect( 'clicked', self._connect, label, 
                                     skey_generator, url )
        
        #abrimos la pagina de confirmacion
        webbrowser.open_new( url )
    
    def _connect( self, button, label, skey_generator, url ):    
        #desconectamos la señal anterior
        button.disconnect( self._b_id )
        
        try:    
            #intentamos obtener la session key y conectamos
            self.settings[Keys.SESSION] = \
                                skey_generator.get_web_auth_session_key(url) 
            self.settings[Keys.CONNECTED] = True      
        
            #reconfiguramos la gui
            label.set_text( 'Logged' )
            button.set_label( 'Logout' )        
            
            #conectamos la nueva señal    
            self._b_id = button.connect( 'clicked', self._logout, label )
        
        except:
            #reconfiguramos la gui para indicar que fallo
            label.set_text( 'Connection failed' )
            button.set_label( 'Login' )  
            
            #conectamos la nueva señal         
            self._b_id = button.connect( 'clicked', self._login, label )             
            
    def _logout( self, button, label ):
        #cambiamos el estado
        self.settings[Keys.CONNECTED] = False
        
        #reconfiguramos la gui
        label.set_text( 'Not Logged' )
        button.set_label( 'Login' )          
        
        #desconectamos la señal anterior
        button.disconnect( self._b_id )
        
        #conectamos la nueva señal 
        self._b_id = button.connect( 'clicked', self._login, label ) 
