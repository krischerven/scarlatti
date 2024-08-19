#!/usr/bin/env bash
flatpak-builder --force-clean "$PWD"/flatpak "$PWD"/org.scarlatti.Scarlatti.json
sudo flatpak build-export repo flatpak
flatpak build-bundle repo scarlatti.flatpak org.scarlatti.Scarlatti
# flatpak-builder --run flatpak org.scarlatti.Scarlatti.json scarlatti