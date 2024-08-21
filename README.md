# Scarlatti: A modern music player for Linux

<!-- ![Scarlatti logo](https://gitlab.gnome.org/World/lollypop/raw/master/data/icons/hicolor/256x256/apps/org.gnome.Lollypop.png) -->

This project is a mostly-backwards-compatible fork of Lollypop, the GNOME music playing application.
The aim of Scarlatti is to add new features - particularly advanced search features - missing
from Lollypop. You can support upstream development by going to https://www.patreon.com/gnumdk

(**WIP - THESE ARE UPSTREAM LINKS**)
- Users: https://wiki.gnome.org/Apps/Lollypop

- Translators: https://hosted.weblate.org/projects/gnumdk/

- Contributions: https://gitlab.gnome.org/World/lollypop/-/wikis/Contributions

It provides:

- MP3/4, Ogg and FLAC support
- Genre/artist/cover browsing
- Regex search with word-grouping
- Search synonyms/typos
- Queue
- Party mode
- ReplayGain
- Cover art downloader
- Context artist view
- MTP sync
- Fullscreen view
- Last.fm support
- Auto install of codecs
- HiDPI support
- TuneIn support

## Dependencies

- `gtk3 >= 3.20`
- `gobject-introspection`
- `appstream-glib`
- `gir1.2-gstreamer-1.0 (Debian)`
- `python3`
- `libhandy1`
- `meson >= 0.40`
- `ninja`
- `totem-plparser`
- `python-gst`
- `python-cairo`
- `python-gobject`
- `python-sqlite`
- `beautifulsoup4`

## Installation (Flatpak)
``` bash
bash -c "$(curl -L https://github.com/krischerven/scarlatti/raw/master/install-flatpak.sh)"
```

## Building from Git

```bash
git clone https://github.com/krischerven/scarlatti
cd scarlatti
meson builddir --prefix=/usr/local
# sudo ninja -C builddir install
```

### Building on Debian/Ubuntu

```bash
git clone https://github.com/krischerven/scarlatti
cd scarlatti
# sudo apt-get install --ignore-missing meson libglib2.0-dev yelp-tools libgirepository1.0-dev libgtk-3-dev gir1.2-totemplparser-1.0 python-gi-dev
meson builddir --prefix=/usr/local
# sudo ninja -C builddir install
```

### Building on Fedora

```bash
git clone https://github.com/krischerven/scarlatti
cd scarlatti
# sudo dnf install --skip-broken meson glib2-devel yelp-tools gtk3-devel gobject-introspection-devel python3 pygobject3-devel python3-gobject-devel libsoup3-devel totem-pl-parser libhandy python3-pillow
meson builddir --prefix=/usr/local
# sudo ninja -C builddir install
```

<!-- [![Packaging status](https://repology.org/badge/vertical-allrepos/lollypop.svg)](https://repology.org/project/lollypop/versions) -->
    