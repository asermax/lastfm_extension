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
#Utilidades para el plugin

import threading
from gi.repository import Gdk, GdkPixbuf, GLib, Notify

# icon used for notifications
icon = None

def init(icon_path):
    '''
    Initialize the module Notification system.
    '''
    # initialize icon
    global icon
    icon = GdkPixbuf.Pixbuf.new_from_file(icon_path)

    # initialize Notify
    if not Notify.is_initted():
        Notify.init("Rhythmbox")

def asynchronous_call(fun, callback=None, *cargs, **ckwargs):
    '''
    This function allows to make asynchronous calls, wrapping a function in
    another one, that is executed in a separated thread.
    Also, it allows to set a callback, together with it's arguments, that will
    be called once the main function processing finishes. The callback function
    MUST recieve as first argument the RESULT from the main function, which
    can be either the result of the execution or an Exception that could've
    been trhown during it's execution.
    '''
    # function that wraps the original function and calls the callback once
    # the processing is finished
    def worker(*args, **kwargs):
        try:
            result = fun(*args, **kwargs)
        except Exception as e:
            result = e

        if callback:
            callback(result, *cargs, **ckwargs)

    def fun2(*args, **kwargs):
        threading.Thread(target=worker, args=args, kwargs=kwargs).start()

    return fun2


def idle_add(fun, *args):
    '''
    Allows to add a function from any thread to be executed on Gtk main loop.
    This function MUST be used when trying to update something related with
    Gtk or GObject.
    '''
    def idle_call(data):
        fun(*data)

        return False

    Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT_IDLE, idle_call, args)

def notify(title, text):
    '''
    Shows a desktop notification.
    '''
    # create the notification
    notification = Notify.Notification.new(title, text, None)

    # add the icon if it's defined
    if icon:
        notification.set_icon_from_pixbuf(icon)

    # show the notification
    notification.show()

