#!/usr/bin/env bash
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
curl -L -o /tmp/scarlatti.flatpak https://github.com/krischerven/scarlatti/raw/master/scarlatti.flatpak
flatpak install /tmp/scarlatti.flatpak
