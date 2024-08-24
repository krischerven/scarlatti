# Scarlatti: A modern, powerful music player for Linux

<!-- ![Scarlatti logo](https://gitlab.gnome.org/World/lollypop/raw/master/data/icons/hicolor/256x256/apps/org.gnome.Lollypop.png) -->
![Scarlatti screenshot](./img/Screenshot_2024-08-24_01-57-42.png)

This project is a mostly-backwards-compatible fork of Lollypop, the GNOME music playing application.
The aim of Scarlatti is to add new features - particularly advanced search features - missing
from Lollypop. You can support upstream development by going to https://www.patreon.com/gnumdk

It provides:

- MP3/4, Ogg and FLAC support
- Genre/artist/cover browsing
- Regex search with word-grouping
- Search synonym/typo-correction system
- Queue
- Party mode
- ReplayGain
- Cover art downloader
- Artist view
- MTP sync
- Fullscreen support
- Last.fm support
- HiDPI support
- TuneIn support
- Builtin codecs

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
    