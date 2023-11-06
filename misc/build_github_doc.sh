#!/bin/sh

set -x

PROJECT_ROOT=$(dirname $(dirname $(readlink -f $0)))

# First setup environment
sudo apt-get update
sudo apt-get -y install git rsync python3-sphinx python3-pycryptodome python3-daemon
sudo apt-get -y install python3-sqlalchemy python3-paramiko python3-pyinotify python3-scp

git config --local user.email "baltrad@users.noreply.github.com"
git config --local user.name "Baltrad GitHub Action"

rm -fr /tmp/doc-env
python3 -m venv --system-site-packages /tmp/doc-env
source /tmp/doc-env/bin/activate

pip3 install git+https://github.com/baltrad/baltrad-crypto.git  || exit 127
pip3 install git+https://github.com/baltrad/baltrad-utils.git || exit 127
pip3 install "Werkzeug == 1.0.1"

cd "$PROJECT_ROOT/doc"

make clean

make github
