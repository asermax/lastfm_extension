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
import LastFMExtensionKeys as Keys
import rb
import pylast, webbrowser

DIALOG_FILE = 'lastfmExtensionConfigDialog.glade'
DIALOG = 'boxPrincipal'
LOGIN_LABEL = 'labelLogin'
LOGIN_BUTTON = 'buttonLogin'
EXTENSIONS_BOX = 'extensions_box'

'''
Función auxiliar para mostrar mensajes de error con un dialog.
'''
def show_error_message(message):
    dialog = Gtk.MessageDialog(None, 0, Gtk.MessageType.ERROR,
                                Gtk.ButtonsType.CLOSE, message)
    dialog.run()
    dialog.destroy()

'''
Diálogo que permite obtener y persistir ciertas configuraciones,
utilizando Gio para persistir las mismas.
'''
class ConfigDialog(GObject.Object, PeasGtk.Configurable):
    __gtype_name__ = 'LastFMExtensionConfigDialog'
    object = GObject.property(type=GObject.Object)

    def __init__(self):
        GObject.Object.__init__(self)
        self.settings = Gio.Settings(Keys.PATH)

    def do_create_configure_widget(self):
        from lastfm_extension import LastFMExtensionBag

        # create the ui with a builder
        builder = Gtk.Builder()
        builder.add_from_file(rb.find_plugin_file(self, DIALOG_FILE))

        if self.settings[Keys.CONNECTED]:
            label_text = 'Logged'
            button_label = 'Logout'
            button_callback = self._logout

        else:
            label_text = 'Not Logged'
            button_label = 'Login'
            button_callback = self._login

        # get the components to modify
        label = builder.get_object(LOGIN_LABEL)
        button = builder.get_object(LOGIN_BUTTON)
        extensions_box = builder.get_object(EXTENSIONS_BOX)

        # get the ui ready
        label.set_text(label_text)

        button.set_label(button_label)
        self._b_id = button.connect('clicked', button_callback, label)

        # add each extension's widget
        for extension in LastFMExtensionBag.get_instance().extensions.values():
            extensions_box.pack_end(extension.get_configuration_widget(), False,
                                   True, 0)

        return builder.get_object(DIALOG)

    def _toggle(self, checkbutton, key):
        self.settings[key] = checkbutton.get_active()
        checkbutton.set_active(self.settings[key])

    def _login(self, button, label):
        # show the page to login
        network = pylast.LastFMNetwork(Keys.API_KEY, Keys.API_SECRET)
        skey_generator = pylast.SessionKeyGenerator(network)
        url = skey_generator.get_web_auth_url()

        # disconnect the button signal
        button.disconnect(self._b_id)

        # change the label and connect new signal
        button.set_label('Press again once allowed')
        self._b_id = button.connect('clicked', self._connect, label,
                                     skey_generator, url)

        #abrimos la pagina de confirmacion
        webbrowser.open_new(url)

    def _connect(self, button, label, skey_generator, url):
        # disconnects old signal
        button.disconnect(self._b_id)

        try:
            # try to get the session key and get connected
            self.settings[Keys.SESSION] = \
                                skey_generator.get_web_auth_session_key(url)
            self.settings[Keys.CONNECTED] = True

            # reconfigure the ui
            label.set_text('Logged')
            button.set_label('Logout')

            # connect the new signal
            self._b_id = button.connect('clicked', self._logout, label)

        except:
            # reconfigure the ui to indicate the failure
            label.set_text('Connection failed')
            button.set_label('Login')

            # connect the new signal
            self._b_id = button.connect('clicked', self._login, label)

    def _logout(self, button, label):
        # change the state
        self.settings[Keys.CONNECTED] = False

        # reconfigure ui
        label.set_text('Not Logged')
        button.set_label('Login')

        # disconect old signal and connect new one
        button.disconnect(self._b_id)
        self._b_id = button.connect('clicked', self._login, label)
