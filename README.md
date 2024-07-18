# Lollypop-plus: A modern music player for Linux

![Lollypop logo](https://gitlab.gnome.org/World/lollypop/raw/master/data/icons/hicolor/256x256/apps/org.gnome.Lollypop.png)

This project is a mostly-backwards-compatible fork of Lollypop, the GNOME music playing application.
The aim of Lollypop-plus is to add new features - particularly advanced search features - missing
from Lollypop. You can support upstream development by going to https://www.patreon.com/gnumdk

(**WIP - THESE ARE UPSTREAM LINKS**)
- Users: https://wiki.gnome.org/Apps/Lollypop

- Translators: https://hosted.weblate.org/projects/gnumdk/

- Contributions: https://gitlab.gnome.org/World/lollypop/-/wikis/Contributions

It provides:

- MP3/4, Ogg and FLAC.
- Genre/cover browsing
- Genre/artist/cover browsing
- Search
- Main playlist (called queue in other apps)
- Party mode
- ReplayGain
- Cover art downloader
- Context artist view
- MTP sync
- Fullscreen view
- Last.fm support
- Auto install codecs
- HiDPI support
- TuneIn support
- **Regex search and word grouping**

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
bash -c "$(curl -L https://github.com/krischerven/lollypop-plus/raw/master/install-flatpak.sh)"
```

## Building from Git

```bash
git clone https://github.com/krischerven/lollypop-plus
cd lollypop-plus
meson builddir --prefix=/usr/local
# sudo ninja -C builddir install
```

### Building on Debian/Ubuntu

```bash
git clone https://github.com/krischerven/lollypop-plus
cd lollypop-plus
# sudo apt-get install --ignore-missing meson libglib2.0-dev yelp-tools libgirepository1.0-dev libgtk-3-dev gir1.2-totemplparser-1.0 python-gi-dev
meson builddir --prefix=/usr/local
# sudo ninja -C builddir install
```

### Building on Fedora

```bash
git clone https://github.com/krischerven/lollypop-plus
cd lollypop-plus
# sudo dnf install --skip-broken meson glib2-devel yelp-tools gtk3-devel gobject-introspection-devel python3 pygobject3-devel python3-gobject-devel libsoup3-devel totem-pl-parser libhandy python3-pillow
meson builddir --prefix=/usr/local
# sudo ninja -C builddir install
```

<!-- [![Packaging status](https://repology.org/badge/vertical-allrepos/lollypop.svg)](https://repology.org/project/lollypop/versions) -->
    