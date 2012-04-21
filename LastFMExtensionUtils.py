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
from gi.repository import GObject, GdkPixbuf, Notify

#icono utilizado para las notificaciones
icon = None

'''
Inicializa este modulo de manera que:
- Se puedan utilizar threads junto con gtk.
- Se muestre un ícono en las notificaciones.
'''
def init( icon_path ):
    #inicializa los threads de gobject
    GObject.threads_init()
        
    #inicializa el icono para notificaciones
    global icon
    icon = GdkPixbuf.Pixbuf.new_from_file( icon_path )
    
    #inicializamos libnotify
    if not Notify.is_initted():
        Notify.init( "Rhythmbox" )

'''
Permite realizar llamadas asincronas, envolviendo una función cualquiera
en otra función que cuando es ejecutada, lo hace en un thread separado.
Ademas, permite agregar una función de callback, junto con argumentos
posicionales y keywords que sera llamada una vez que se termine la 
ejecución de la función asincrona. Esta función DEBE estar preparada para
recibir como primer argumento el RESULTADO de la ejecución de la función
principal, el cual puede ser tanto un OBJETO común como una EXCEPCIÓN.
'''
def asynchronous_call( fun, callback=None, *cargs, **ckwargs ):
    #función que wrappea la función original y ejecuta el callback una
    #vez terminada la ejecución
    def worker( *args, **kwargs ):         
        try:      
            result = fun( *args, **kwargs )            
        except Exception as e:
            result = e
        
        if callback:    
            callback( result, *cargs, **ckwargs )
    
    #función que wrappea la ejecución asincrona en un thread aparte
    def fun2( *args, **kwargs ):
        threading.Thread( target=worker, args=args, kwargs=kwargs ).start()

    return fun2

'''
Permite realizar una llamada asincrona desde un thread cualquiera a un
componente de UI que corre sobre el main loop de gtk. Se DEBE utilizar
esta función para realizar este tipo de tareas, de otra forma gtk crashea.
'''
def idle_add( fun, *args ):
    GObject.idle_add( fun, *args )
    
'''
Muestra una notificación de escritorio utilizando la libreria de notificación
libnotify (a través de los bindings de pynotify)
''' 
def notify( title, text ):
    #crea la notificación
    notification = Notify.Notification.new( title, text, None )
    
    #le agrega el ícono si el mismo fué definido
    if icon:
        notification.set_icon_from_pixbuf( icon )
    
    #muestra la notificación
    notification.show()
    
