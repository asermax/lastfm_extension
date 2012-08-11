lastfm_extension - Rhythmbox&#39;s LastFM Extension Plugin
==========================================================

This plugin adds the love and ban buttons to your Rhythmbox toolbar again!

Whenever you love a track, it will also be marked with 5 stars on the player, and whenever you ban a track, it's ranking will be reseted to 0. I can't assure what will happen if you ban an already loved track (or viceversa), since for some reason LastFM allows you to love and ban a track at the same time.

It currently doesn't support Unloving or Unbaning tracks (the LastFM API haven't implemented this feature yet).

Also, you have the option to activate:
- Playcount synchronization. (It can only retrieve the playcount from LastFM, not change it)
- Loved track synchronization. (It will add 5 stars to the current track if it's currently marked as loved on your account)

Installation
-----------

To install, just execute the install.sh script (this will install the plugin locally, it will only be available for the current user).
The installation script will ask for admin password to install the glib-schema used to save the plugin settings.

TODO: enable global installation (for all users).

Use
---

This plugin uses pylast (http://code.google.com/p/pylast/) as interface with LastFM and it doesn't depends on the default Rhythmbox's LastFM plugin. Thus, you have to login separately, going to the plugin's Preferences dialog, where you can also specify if you want to sync playcount and loved tracks with your account.

Contact
------
You can let me know of any bugs or new features you want to see implemented through this repository's issue tracker.
Also, feel free to contact me at my personal email account: asermax at gmail dot com.

And if you feel really friendly, at me on LastFM! My user over there is also asermax :]


