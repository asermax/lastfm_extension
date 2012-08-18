# -*- Mode: python; coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
#
# Copyright (C) 2012 - Carrasco Agustin
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


try:
    import lastfp
except:
    raise LastFMFingerprintException( 'LastFM fingerprint library not found.' )

from gi.repository import Gio

import LastFMExtensionKeys as Keys
from LastFMExtensionUtils import asynchronous_call as async

ui_context_menu = """
<ui>
  <popup name="BrowserSourceViewPopup">
	 <placeholder name="PluginPlaceholder">
         <menuitem name="FingerprintSong" action="FingerprintSong"/>
     </placeholder>
  </popup>
  <popup name="PlaylistViewPopup">
	 <placeholder name="PluginPlaceholder">
         <menuitem name="FingerprintSong" action="FingerprintSong"/>
     </placeholder>
  </popup>
  <popup name="QueuePlaylistViewPopup">
     <placeholder name="PluginPlaceholder">
	     <menuitem name="FingerprintSong" action="FingerprintSong"/>
     </placeholder>
  </popup>

  <popup name="PodcastViewPopup">
     <placeholder name="PluginPlaceholder">
	     <menuitem name="FingerprintSong" action="FingerprintSong"/>
     </placeholder>
  </popup>
</ui>

"""

class LastFMFingerprintException( Exception ):
    def __init__( self, message ):
        super( LastFMFingerprintException, self).__init__( message )
        
class LastFMFingerprinter:
    
    def __init__( self ):
        self.settings = Gio.Settings.new( Keys.PATH )

    
    
