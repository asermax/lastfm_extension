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

from gi.repository import RB, Gtk, Gio
from urlparse import urlparse
from urllib import unquote
from subprocess import check_output, CalledProcessError
import math
import rb

import LastFMExtensionGui as GUI
from lastfm_extension import LastFMExtension
from LastFMExtensionGenreGuesser import LastFMGenreGuesser
from LastFMExtensionUtils import asynchronous_call as async, idle_add
import lastfm_extension

#try to import lastfp
class LastFMFingerprinterException( Exception ):
    def __init__( self, message ):
        super( LastFMFingerprinterException, self ).__init__( message )

try:
    import lastfp
except:
    lastfp = LastFMFingerprinterException( 
                                    'LastFM fingerprint library not found.' )

#constants
DIALOG_BUILDER_FILE = 'lastfmExtensionFingerprintDialog.glade'
MATCHER = 'matcher.py'
DIALOG_NAME = 'song-selection-dialog'
BOX = 'songe-selection-dialog-vbox'
STATUS_BOX = 'statusBox'
ACTION_SAVE = 'actionSave'

#rhythmbox magic number for days in a year(??????)
DAYS = 365.2

#name and description
NAME = "LastFMFingerprinter"
DESCRIPTION = "Fingerprint your songs and match them against Last.FM."

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

class Extension( LastFMExtension ):
    '''
    This extension is responsible of fingerprinting songs and showing the UI to
    let the user decide if he wants to save the result and which match to use.
    '''

    def __init__( self, plugin ):
        '''
        Initialises the extension, using the base plugin to populate some of the
        internal properties used on the fingerprinting process.
        '''
        super( Extension, self ).__init__( plugin )

        #rhythmbox database
        self.db = plugin.shell.props.db

        #rhythmbox shell
        self.shell = plugin.shell

        #lastfm genre guesser
        self.genre_guesser = LastFMGenreGuesser( plugin )

        #save the matcher path
        self.matcher_path = rb.find_plugin_file( plugin, MATCHER )

        #get the builder file path
        self.builder_file = rb.find_plugin_file( plugin, DIALOG_BUILDER_FILE )

        #queue for requests
        self.queue = []

    def destroy( self, plugin ):
        '''
        Free all the resources that were allocated on the extension creation.
        '''
        super( Extension, self ).destroy( plugin )

        del self.db
        del self.shell
        del self.genre_guesser
        del self.matcher_path
        del self.builder_file
        del self.queue

    @property
    def extension_name( self ):
        '''
        Returns the extension name. Read only property.
        '''
        return NAME

    @property
    def extension_desc( self ):
        '''
        Returns a description for the extensions. Read only property.
        '''
        return DESCRIPTION

    @property
    def ui_str( self ):
        '''
        Returns the ui_str that defines this plugins ui elements to be added to
        Rhythmbox application window. Read only property.
        '''
        return ui_context_menu

    def initialise( self, plugin ):
        '''
        Initialises the extension. Checks if the last_fp module is avaible and
        shows an error if it's not.

        Parameters:
            plugin -- the current instance of the plugin managed by Rhythmbox.
        '''        
        if isinstance( lastfp, Exception ):
            GUI.show_error_message( lastfp.message )
            self.enabled = False
        else:            
            super( Extension, self ).initialise( plugin )

    def create_actions( self, plugin ):
        '''
        Creates fingerprint action for the different context menues.
        '''
        super( Extension, self ).create_actions( plugin )
        self.finger_action_group = Gtk.ActionGroup( 
                                        'LastFMExtensionFingerprinter' )
        self.action_fingerprint = Gtk.Action( 'FingerprintSong',
                                        _( '_Fingerprint Song' ),
                                        _( "Get this song fingerprinted." ),
                                        None )
        icon = Gio.FileIcon.new( 
           Gio.File.new_for_path( 
           rb.find_plugin_file( plugin, lastfm_extension.LASTFM_ICON ) ) )
        self.action_fingerprint.set_gicon( icon )

        self.finger_action_group.add_action( self.action_fingerprint )
        plugin.uim.insert_action_group( self.finger_action_group, -1 )

    def connect_signals( self, plugin ):
        '''
        Connects all the extension's needed signals for it to function
        correctly.
        This method is always called when the extension is initialized.
        '''
        super( Extension, self ).connect_signals( plugin )
        self.fp_id = self.action_fingerprint.connect( 'activate',
                                                      self.fingerprint_song )

    def disconnect_signals( self, plugin ):
        '''
        Disconnects all the signals connected by the extension.
        This method is always called when the extension is dismantled.
        '''
        super( Extension, self ).disconnect_signals( plugin )

        #disconnect signal
        self.action_fingerprint.disconnect( self.fp_id )

        #delete variables
        del self.fp_id

    def destroy_actions( self, plugin ):
        '''
        Dismantles all the actions created by this extension and dissasociates
        them from the Rhythmbox application.
        This method is always called when the extension is dismantled.
        '''
        super( Extension, self ).destroy_actions( plugin )

        #remove and destroy the action group
        plugin.uim.remove_action_group( self.finger_action_group )
        del self.finger_action_group

        #delete action
        del self.action_fingerprint

    def fingerprint_song( self, _ ):
        '''
        Callback for the action of the different cm items.
        '''
        for entry in self.get_selected_songs():
            self.request_fingerprint( entry )
    
    def get_selected_songs( self ):
        '''
        Returns a list of the selected songs in the current view.
        '''
        page = self.shell.props.selected_page
        selected = page.get_entry_view().get_selected_entries()

        return selected    

    def request_fingerprint( self, entry ):
        '''
        This is this extension principal interface. This method should be called
        whenever it's needed to fingerprint a song.
        It uses the extension queue system, to avoid multiple request to happen 
        at the same time.
        '''
        if len( self.queue ) == 0:
            self._fingerprint( entry )

        self.queue.append( entry )

    def _fingerprint( self, entry ):
        '''
        This is the actual function that starts the fingerprinting.
        It shows a Dialog to indicate the user to wait, and executes the
        fingerprinting proccess asynchronously.
        '''
        #show the fingerprinter dialog
        ui = self._show_dialog( entry )

        #fingerprint and match the entry asynchronously
        async( self._match, self._append_options, entry, *ui )( entry,
                                                              self.network )

    def _show_dialog( self, entry ):
        '''
        Shows a wait dialog with the entry title and artist in the title.
        This dialog is used to show the matching options after they are fetched.
        '''
        #create a new builder over the builder_file
        builder = Gtk.Builder()
        builder.add_from_file( self.builder_file )

        #connect signals
        builder.connect_signals( self )

        #show the dialog
        dialog = builder.get_object( DIALOG_NAME )
        dialog.set_title( 'Matches for %s - %s' %
		                    ( entry.get_string( RB.RhythmDBPropType.ARTIST ),
		                      entry.get_string( RB.RhythmDBPropType.TITLE ) ) )
        dialog.present()

        #get the status box and the box
        main_box = builder.get_object( BOX )
        status_box = builder.get_object( STATUS_BOX )
        action_save = builder.get_object( ACTION_SAVE )

        return main_box, status_box, action_save

    def _match( self, entry, network ):
        '''
        This method encapsulates the fingerprinting and matching process.
        It takes info from the entry to realize the fingerprinting and uses pylast
        to retrieve the tracks info, which is finally returned as a list of Track
        instances.
        '''
        #get artist, album, track and path    
        path = unquote( urlparse( entry.get_playback_uri() ).path )
        artist = entry.get_string( RB.RhythmDBPropType.ARTIST )
        album = entry.get_string( RB.RhythmDBPropType.ALBUM )
        title = entry.get_string( RB.RhythmDBPropType.TITLE )

        #match the song    
        try:
            fpid = check_output( 
                        [self.matcher_path, path, artist, album, title] )

            result = network.get_tracks_by_fpid( fpid )

        except CalledProcessError as error:
            #in the case the fingerprinter fails, raise an exception 
            raise Exception( error.output )

        return result

    def _append_options( self, result, entry, main_box, status_box,
                         action_save ):
        '''
        This method appends toggles buttons to the dialog, with the info of the
        matched tracks and connects the signal to save the selected option.
        '''
        #box which will contain the toggles   
        vbox = Gtk.VBox()

        #if there where actual results
        if type( result ) is list and len( result ) > 0:
            #options list
            options = []

            #for each option
            for track in result:
                #append the option and make sure they are all in the same group
                label = '%d%%: %s' % ( math.ceil( track.rank * 100 ), str( track ) )

                if not options:
                    toggle = Gtk.RadioButton( label=label )
                else:
                    toggle = Gtk.RadioButton( label=label )
                    toggle.join_group( options[0] )

                options.append( toggle )

                toggle.set_mode( False )
                vbox.pack_start( toggle, True, True, 0 )

            #also, add a checkbox to ask if fetch extra info
            check_extra = Gtk.CheckButton( 'Fetch extra info?' )
            check_extra.set_tooltip_text( 'Fetch track playcount, rating, '
                                          + 'genre, album name, track number '
                                          + 'and release year' )

            vbox.pack_end( check_extra, True, True, 0 )

            #connect and activate the save action
            action_save.connect( 'activate', self._save_selected, entry, result,
                                 main_box.get_parent(), options, check_extra )
            idle_add( action_save.set_sensitive, True )

        #if there weren't valid results
        else:
            #if we catched and exception show the error, otherwise, indicate 
            #that there weren't matches
            if type( result ) is Exception:
                label = Gtk.Label( result.message )
            else:
                label = Gtk.Label( 'No matches found.' )

            vbox.pack_start( label, True, True, 0 )

        #show the box   
        vbox.show_all()

        #delete the old box and append the new
        idle_add( status_box.destroy )
        idle_add( main_box.pack_start, vbox, True, True, 0 )

    def _close_fingerprinter_window( self, dialog ):
        '''
        Callback for closing the dialog.
        '''
        dialog.destroy()

        self.queue.pop( 0 )

        if len( self.queue ) > 0:
            self._fingerprint( self.queue[0] )

    def _save_selected( self, _, entry, tracks, dialog, options, extra ):
        '''
        Callback for closing the dialog.
        '''
        for option in options:
            if option.get_active():
                track = tracks[options.index( option )]

                self.db.entry_set( entry, RB.RhythmDBPropType.ARTIST,
                                          track.get_artist().get_name().encode( 
                                                                      'utf8' ) )
                self.db.entry_set( entry, RB.RhythmDBPropType.TITLE,
                                          track.get_title().encode( 'utf8' ) )
                self.db.commit()

                #asynchronously retrieve extra data
                if extra.get_active():
                    async( self._fetch_extra_info,
                           self._delayed_properties_save, entry )( track )

                break

        self._close_fingerprinter_window( dialog )

    def _fetch_extra_info( self, track ):
        '''
        Fetch extra info from Last.fm.
        For now, it fetchs:
        - Playcount
        - Album data (if available)
            - Rating (if is loved, 5 stars)
            - Album Name
            - Release Year (if available)
            - Album Artist
            - Track Number
            - Track Genre
        '''
        #list for extra info with it's db keys
        info = []

        #play count
        info.append( ( RB.RhythmDBPropType.PLAY_COUNT,
                      track.get_playcount( True ) ) )

        #genre
        genre = self.genre_guesser.guess( track )

        if genre:
            info.append( ( RB.RhythmDBPropType.GENRE, genre.encode( 'utf-8' ) ) )

        #loved track (rating 5 stars)           
        if track.is_loved():
            info.append( ( RB.RhythmDBPropType.RATING, 5 ) )

        #album data
        album = track.get_album()

        if album:
            #album name
            info.append( ( RB.RhythmDBPropType.ALBUM,
                          album.get_name().encode( 'utf-8' ) ) )

            #release date (year)
            date = album.get_release_date()

            if date.strip() != '':
                info.append( ( RB.RhythmDBPropType.DATE,
                              int( date.split()[2][:-1] ) * DAYS ) )

            #album artist
            info.append( ( RB.RhythmDBPropType.ALBUM_ARTIST,
                          album.get_artist().get_name().encode( 'utf-8' ) ) )

            #track number
            tracks = album.get_tracks()

            for track_number in range( 0, len( tracks ) ):
                if track == tracks[track_number]:
                    break

            info.append( ( RB.RhythmDBPropType.TRACK_NUMBER, track_number + 1 ) )

        return info

    def _delayed_properties_save( self, info, entry ):
        '''
        Callback used after extra info is fetched, to save it to the properties of
        the entry.
        '''
        for prop in info:
            idle_add( self.db.entry_set, entry, *prop )

        idle_add( self.db.commit )
