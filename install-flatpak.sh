#!/usr/bin/env bash
if [ $(flatpak list | grep -c "org.scarlatti.Scarlatti") == 1 ]; then
   echo "Removing existing Scarlatti installation..."
   flatpak remove org.scarlatti.Scarlatti
fi

flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo

echo "Downloading scarlatti.flatpak..."
curl -L -o /tmp/scarlatti.flatpak https://github.com/krischerven/scarlatti/raw/master/scarlatti.flatpak

echo "Installing Scarlatti"
flatpak install /tmp/scarlatti.flatpak