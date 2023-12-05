#!/bin/bash

PROJECT_ROOT=$(dirname $(dirname $(readlink -f $0)))

exit_with_message() {
  echo "$*"
  exit 127
}

create_and_init_venv() {
  echo "Creating virtual environment"
  envpath=$1
  if [ -d "$envpath" ]; then
    \rm -fr "$envpath"
  fi
  python3 -m venv "$envpath"
  source $envpath/bin/activate
  pip3 install --upgrade pip setuptools==57.5.0 
  pip3 install "nose2 >= 0.12" --trusted-host pypi.python.org
  pip3 install "mock >= 1.0" --trusted-host pypi.python.org
  pip3 install "zmq" --trusted-host pypi.python.org
  pip3 install "cryptography == 3.3.1" --trusted-host pypi.python.org
  python3 -m pip install 'git+https://github.com/baltrad/baltrad-utils.git' || exit_with_message "Could not install baltrad-utils"
  python3 -m pip install 'git+https://github.com/baltrad/baltrad-crypto.git' || exit_with_message "Could not install baltrad-crypto"
  python3 -m pip install 'git+https://github.com/baltrad/baltrad-db.git/#egg=baltrad-bdbcommon&subdirectory=common' || exit_with_message "Could not install bdbcommon"
  python3 -m pip install 'git+https://github.com/baltrad/baltrad-db.git/#egg=baltrad-bdbclient&subdirectory=client/python' || exit_with_message "Could not install bdbclient"

  python3 setup.py develop
}

runtest() {
  echo "Running tests"
  package_dir=$1
  PYTHONPATH=src:test python3 -m nose2 --config misc/unittest.cfg --plugin nose2.plugins.junitxml --junit-xml
}


create_and_init_venv "$PROJECT_ROOT/test-env"
runtest "$PROJECT_ROOT"
