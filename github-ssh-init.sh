#!/bin/bash
echo "Running ./github-ssh-init.sh. This file must be sourced to have any effect!"
eval "$(ssh-agent -s)"
# github-key should be a symlink to your github key
ssh-add ./github-key