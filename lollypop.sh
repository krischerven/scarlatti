#!/usr/bin/env bash
meson builddir --prefix=/usr/local
sudo ninja -C builddir install
lollypop