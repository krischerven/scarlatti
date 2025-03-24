#!/usr/bin/env bash


if [ -n "$(git log --branches --not --remotes)" ]; then
    read -p "WARNING: You have unpushed commits! Continue? (y/N) " choice
    [[ $choice =~ ^[Yy]$ ]] || exit 1
fi

flatpak-builder --force-clean "$PWD"/flatpak "$PWD"/org.scarlatti.Scarlatti.json
sudo flatpak build-export repo flatpak
flatpak build-bundle repo scarlatti.flatpak org.scarlatti.Scarlatti
# flatpak-builder --run flatpak org.scarlatti.Scarlatti.json scarlatti