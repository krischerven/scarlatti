# Lollypop-plus music player

![Lollypop logo](https://gitlab.gnome.org/World/lollypop/raw/master/data/icons/hicolor/256x256/apps/org.gnome.Lollypop.png)

Support upstream development: https://www.patreon.com/gnumdk

This project is a fork of Lollypop, the GNOME music playing application.
The aim of Lollypop-plus is to add new features - particularly advanced search features - missing from Lollypop.

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

## Depends on

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

## Building from Git

```bash
$ git clone https://github.com/krischerven/lollypop-plus
$ cd lollypop-plus
$ meson builddir --prefix=/usr/local
# sudo ninja -C builddir install
```

### On Debian/Ubuntu

```bash
$ git clone https://github.com/krischerven/lollypop-plus
$ cd lollypop-plus
# apt-get install meson libglib2.0-dev yelp-tools libgirepository1.0-dev libgtk-3-dev gir1.2-totemplparser-1.0 python-gi-dev
$ meson builddir --prefix=/usr/local
# sudo ninja -C builddir install
```

### On Fedora

```bash
$ git clone https://github.com/krischerven/lollypop-plus
$ cd lollypop-plus
# sudo dnf install meson glib2-devel yelp-tools gtk3-devel gobject-introspection-devel python3 pygobject3-devel libsoup-devel
$ meson builddir --prefix=/usr/local
# sudo ninja -C builddir install
```

<!-- [![Packaging status](https://repology.org/badge/vertical-allrepos/lollypop.svg)](https://repology.org/project/lollypop/versions) -->
    