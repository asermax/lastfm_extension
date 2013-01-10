lastfm_extension - Rhythmbox&#39;s LastFM Extension Plugin
==========================================================

This plugin adds the love and ban buttons to your Rhythmbox toolbar again!

Whenever you love a track, it will also be marked with 5 stars on the player, and whenever you ban a track, it's ranking will be reseted to 0. I can't assure what will happen if you ban an already loved track (or viceversa), since for some reason LastFM allows you to love and ban a track at the same time.

It currently doesn't support Unloving or Unbaning tracks (the LastFM API haven't implemented this feature yet).

Extras!
-----------
Besides the love and ban buttons, this plugins haves some extras, which you can activate from the plugin configuration dialog:
* Playcount synchronization. (It can only retrieve the playcount from LastFM, not change it)
* Loved track synchronization. (It will add 5 stars to the current track if it's currently marked as loved on your account)
* Add an option to fingerprint your songs and match them against the Last.fm database! Initialy, this extension can retrieve the title and artist name of your tracks, but you can also fetch extra info (as it's album name, track number, realese year, playcount, rating and genre) by checking the "Fetch extra info" checkbox (this will be done asynchronously in the background, once the info is fetched, your track will be updated). This handy feature requires [pylastfp](http://pypi.python.org/pypi/pylastfp/0.1) to work.

**Note:** you need to be logged into your LastFM account for this extras to work. Even if they are activated, they won't take effect until you log in.

Installation
-----------
To install, just execute the install.sh script; this will install the plugin locally by default. 
If you want to install the plugin globally (for all the users of the system) you need to use the '-g' option.

###About [pylastfp](http://pypi.python.org/pypi/pylastfp/0.1)
To enable the fingerprinting feature on this plugin, you need to install pylastfp.
On debian based distributions, you can let the installer script do it for you adding the '--fingerprint-support' flag, or you can do it manually by issuing the following commands on a terminal:
```
sudo apt-get install python-pip libfftw3-dev libsamplerate0-dev

sudo pip install pylastfp
```

In the case you already installed pylastfp and want to upgrade it:
```
sudo pip install pylastfp --upgrade
```

After installing it, you should be able to enable the fingerprinter on the plugins preferences.

Use
---
This plugin uses pylast (http://code.google.com/p/pylast/) as interface with LastFM and it doesn't depends on the default Rhythmbox's LastFM plugin. Thus, you have to login separately, going to the plugin's Preferences dialog, where you can also specify if you want to sync playcount and loved tracks with your account.

Credits
-------
This plugin makes use of the following libraries:
* [pylast](http://code.google.com/p/pylast/), a wonderful python library that allows you to painlessly interact with [Last.fm API](http://www.last.fm/api).
* [pylastfp](http://pypi.python.org/pypi/pylastfp/0.1), a library that binds the Last.fm's fingerprinting library and provides an easy access to it's functions.

Also, some of the ideas on this plugin came from [beets](https://github.com/sampsyo/beets), and extremely good media library management system; for instance, the genre guessing mechanism on the plugin fingerprinting feature is based on lastgenre's beets plugin.

Contact
------
You can let me know of any bugs or new features you want to see implemented through this repository's issue tracker.
Also, feel free to contact me at my personal email account: asermax at gmail dot com.

And if you feel really friendly, add me on LastFM! My user over there is also asermax :]


