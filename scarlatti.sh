#!/usr/bin/env bash
meson setup builddir --prefix=/usr/local
sudo ninja -C builddir install
scarlatti