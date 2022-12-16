#!/bin/sh

set -x

PROJECT_ROOT=$(dirname $(dirname $(readlink -f $0)))

# First setup environment
sudo apt-get update
sudo apt-get -y install git rsync python3-sphinx python3-pycryptodome

git config --local user.email "baltrad@users.noreply.github.com"
git config --local user.name "Baltrad GitHub Action"

pip3 install "jprops == 2.0.2"
pip3 install "Werkzeug == 1.0.1"

cd "$PROJECT_ROOT/doc"

make github
