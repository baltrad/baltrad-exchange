#!/bin/bash

PROJECT_ROOT=$(dirname $(dirname $(readlink -f $0)))

create_and_init_venv() {
  echo "Creating virtual environment"
  envpath=$1
  python3 -m venv --system-site-packages "$envpath"
  source $envpath/bin/activate
  python3 setup.py develop
  $envpath/bin/pip3 install "nose2 >= 0.12" --trusted-host pypi.python.org
  $envpath/bin/pip3 install "mock >= 1.0" --trusted-host pypi.python.org
}

runtest() {
  echo "Running tests"
  package_dir=$1
  PYTHONPATH=src:test python3 -m nose2 --config misc/unittest.cfg --plugin nose2.plugins.junitxml --junit-xml
}


create_and_init_venv "$PROJECT_ROOT/test-env"
runtest "$PROJECT_ROOT"
