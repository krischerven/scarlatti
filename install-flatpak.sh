#!/usr/bin/env bash

flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
curl -L -o /tmp/lollypop-plus.flatpak https://github.com/krischerven/lollypop-plus/raw/master/lollypop.flatpak
flatpak install /tmp/lollypop-plus.flatpak
