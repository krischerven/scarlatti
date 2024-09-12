# Scarlatti: A modern, powerful music player for Linux (and WSL)

![Scarlatti screenshot](./img/Screenshot_2024-08-24_01-57-42.png)

Scarlatti is a mostly-backwards-compatible fork of Lollypop, the GNOME music playing application.
Scarlatti was created because I needed a number of new features in my Lollypop workflow, and no
other music player met my needs.

Scarlatti is designed to be particularly good at searching through large collections of untagged
music with detailed filenames (which is a large part of my unusual workflow)

Generally speaking, I will accept any reasonable feature request so as to make Scarlatti useful for
the largest number of people. Not all features will be enabled by default, but Scarlatti's philosophy
is that a good music player should be powerful and extremely flexible while still having a modern
look and feel.

This project would not have been possible without the work of the original Lollypop developers,
particularly Cédric Bellegarde. Please consider supporting him and Lollypop by going to
https://www.patreon.com/gnumdk

Scarlatti provides, among other features:

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

For a full list of improvements to Lollypop, see [here](./scarlatti-vs-lollypop.md).

For a (heavy WIP) usage guide, see [here](./how-do-I.md).

For a list of build dependencies, see [here](./build-dependencies.md).

## Flatpak installation/update (recommended)
``` bash
bash -c "$(curl -L https://github.com/krischerven/scarlatti/raw/master/install-flatpak.sh)"
```

## Uninstallation
``` bash
flatpak remove org.scarlatti.Scarlatti
```

## Building from source

```bash
git clone https://github.com/krischerven/scarlatti
cd scarlatti
# Install dependencies using instructions in ./build-dependencies.md
meson builddir --prefix=/usr/local
# sudo ninja -C builddir install
```

<!-- [![Packaging status](https://repology.org/badge/vertical-allrepos/lollypop.svg)](https://repology.org/project/lollypop/versions) -->
    