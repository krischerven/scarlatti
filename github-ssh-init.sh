#!/bin/bash
eval "$(ssh-agent -s)"
# github-key should be a symlink to your github key
ssh-add ./github-key