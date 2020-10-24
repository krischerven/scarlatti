#!/bin/sh
git fetch --tags
git describe --tags | sed 's/\([^-]*-g\)/r\1/;s/-/./g'
