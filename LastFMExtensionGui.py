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

from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import PeasGtk
import LastFMExtensionKeys as Keys
import rb
import pylast, webbrowser

DIALOG_FILE = 'lastfmExtensionConfigDialog.glade'
DIALOG = 'config_notebook'
LOGIN_LABEL = 'login_label'
LOGIN_BUTTON = 'login_button'


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

    def do_create_configure_widget(self):
        from lastfm_extension import LastFMExtensionBag

        self.settings = LastFMExtensionBag.get_instance().settings.get_section(
            Keys.CONNECTION_SECTION)

        # create the ui with a builder
        builder = Gtk.Builder()
        builder.add_from_file(rb.find_plugin_file(self, DIALOG_FILE))

        dialog = builder.get_object(DIALOG)

        if self.settings.getboolean(Keys.CONNECTED):
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

        # get the ui ready
        label.set_text(label_text)

        button.set_label(button_label)
        self._b_id = button.connect('clicked', button_callback, label)

        # add each extension's widget
        extensions = LastFMExtensionBag.get_instance().extensions.values()

        for extension in sorted(extensions, key=lambda ext: ext.order,
                                reverse=True):
            self._add_extension_widget(dialog,
                *extension.get_configuration_widget())
            # extensions_box.pack_end(extension.get_configuration_widget(), False,
            #                       True, 0)

        return dialog

    def _add_extension_widget(self, dialog, section, widget):
        extension_box = None

        for page_num in range(0, dialog.get_n_pages()):
            page = dialog.get_nth_page(page_num)

            if dialog.get_tab_label_text(page) == section:
                extension_box = page

        if not extension_box:
            extension_box = Gtk.Box(visible=True, can_focus=False,
                border_width=10, orientation=Gtk.Orientation.VERTICAL,
                spacing=5)
            label = Gtk.Label(visible=True, label=section)

            dialog.append_page(extension_box, label)

        extension_box.pack_start(widget, False, True, 0)

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

        # abrimos la pagina de confirmacion
        webbrowser.open_new(url)

    def _connect(self, button, label, skey_generator, url):
        # disconnects old signal
        button.disconnect(self._b_id)

        try:
            # try to get the session key and get connected
            self.settings.set(Keys.SESSION,
                skey_generator.get_web_auth_session_key(url))
            self.settings.set(Keys.CONNECTED, True)

            # reconfigure the ui
            label.set_text('Logged')
            button.set_label('Logout')

            # connect the new signal
            self._b_id = button.connect('clicked', self._logout, label)

        except Exception as e:
            # reconfigure the ui to indicate the failure
            label.set_text('Connection failed:\n%s' % e.message)
            button.set_label('Login')

            # connect the new signal
            self._b_id = button.connect('clicked', self._login, label)

    def _logout(self, button, label):
        # change the state
        self.settings.set(Keys.CONNECTED, False)

        # reconfigure ui
        label.set_text('Not Logged')
        button.set_label('Login')

        # disconect old signal and connect new one
        button.disconnect(self._b_id)
        self._b_id = button.connect('clicked', self._login, label)
