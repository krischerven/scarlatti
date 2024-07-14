#!/usr/bin/env bash
flatpak-builder --force-clean "$PWD"/flatpak "$PWD"/org.gnome.Lollypop.json
sudo flatpak build-export repo flatpak
flatpak build-bundle repo lollypop.flatpak org.gnome.Lollypop
# flatpak-builder --run flatpak org.gnome.Lollypop.json lollypop