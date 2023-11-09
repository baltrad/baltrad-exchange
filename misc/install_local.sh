#!/bin/sh

SCRIPTPATH="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
PROJECTFOLDER="$(dirname "$SCRIPTPATH")"

PREFIX=/opt/baltrad/exchange
NODENAME="$(hostname).node"
ODIM_SOURCE=
SERVER_SUBJECT=
USERNAME=baltrad
GROUPNAME=baltrad
ASKPROMPT=yes

exit_with_message() {
  echo "$*"
  exit 127
}

# Creates the install folders used for a local installation
#
create_install_folders() {
  if [ ! -d "$PREFIX" ]; then
    mkdir -p "$PREFIX" || exit_with_message "Could not create folder $PREFIX"
  fi
  if [ ! -d "$PREFIX/etc" ]; then
    mkdir -p "$PREFIX/etc" || exit_with_message "Could not create folder $PREFIX/etc"
  fi
  if [ ! -d "$PREFIX/etc/crypto-keys" ]; then
    mkdir -p "$PREFIX/etc/crypto-keys" || exit_with_message "Could not create folder $PREFIX/etc/crypto-keys"
  fi
  if [ ! -d "$PREFIX/config" ]; then
    mkdir -p "$PREFIX/config" || exit_with_message "Could not create folder $PREFIX/config"
  fi
  if [ ! -d "$PREFIX/var" ]; then
    mkdir -p "$PREFIX/var" || exit_with_message "Could not create folder $PREFIX/var"
  fi
}

# Dependencies that are not available on pip. Rest of dependencies should be found in the setup.py files.
#
install_dependencies()  {
  python3 -m pip install 'git+https://github.com/baltrad/baltrad-utils.git' || exit_with_message "Could not install baltrad-utils"

  python3 -m pip install 'git+https://github.com/baltrad/baltrad-crypto.git' || exit_with_message "Could not install baltrad-crypto"

  python3 -m pip install 'git+https://github.com/baltrad/baltrad-db.git/#egg=baltrad-bdbcommon&subdirectory=common' || exit_with_message "Could not install bdbcommon"

  python3 -m pip install 'git+https://github.com/baltrad/baltrad-db.git/#egg=baltrad-bdbclient&subdirectory=client/python' || exit_with_message "Could not install bdbclient"
}

# (Creates and) activates the virtual environment for the local installation. Note, no system site packages
# are used to avoid getting conflicts.
#
activate() {
  if [ ! -f "$PREFIX/local-env/bin/activate" ]; then
    python3 -m venv "$PREFIX/local-env" || exit_with_message "Could not create environment $PREFIX/local-env"
  fi
  . "$PREFIX/local-env/bin/activate" || exit_with_message "Could not activate environment"
}

# Updates the property file with some default settings and creates the server cert/key files.
#
create_initial_configuration()
{
  cp "$PROJECTFOLDER/etc/baltrad-exchange.properties" "$PREFIX/etc/"
  sed -i "$PREFIX/etc/baltrad-exchange.properties" -e "s/baltrad.exchange.log.type=\(.*\)/baltrad.exchange.log.type=syslog/g"
  sed -i "$PREFIX/etc/baltrad-exchange.properties" -e "s/baltrad.exchange.node.name\s*=\s*\(.*\)/baltrad.exchange.node.name = $NODENAME/g"
  
  if [ ! -f "$PREFIX/etc/crypto-keys/$NODENAME.private" ]; then
    baltrad-crypto-config create_keys --destination="$PREFIX/etc/crypto-keys" --nodename="$NODENAME" || exit_with_message "Could not create crypto key for $NODENAME"
  fi
  
  sed -i "$PREFIX/etc/baltrad-exchange.properties" -e "s#baltrad.exchange.auth.crypto.root\s*=\s*\(.*\)#baltrad.exchange.auth.crypto.root = $PREFIX/etc/crypto-keys#g"
  sed -i "$PREFIX/etc/baltrad-exchange.properties" -e "s#baltrad.exchange.auth.crypto.private.key\s*=\s*\(.*\)#baltrad.exchange.auth.crypto.private.key = $PREFIX/etc/crypto-keys/$NODENAME.private#g"
  sed -i "$PREFIX/etc/baltrad-exchange.properties" -e "s#baltrad.exchange.server.config.dirs\s*=\s*\(.*\)#baltrad.exchange.server.config.dirs = $PREFIX/config#g"
  
  if [ "$ODIM_SOURCE" = "" ]; then
    echo "Fetching latest odim sources"
    wget https://raw.githubusercontent.com/baltrad/rave/master/config/odim_source.xml -O "$PREFIX/etc/odim_source.xml" || exit_with_message "Could not fetch odim_source"
  else
    if [ -f "$ODIM_SOURCE" ]; then
      cp "$ODIM_SOURCE" "$PREFIX/etc/odim_source.xml" || exit_with_message "Could not copy odim_source"
    else
      exit_with_message "Must provide a valid odim_source"
    fi
  fi
  
  sed -i "$PREFIX/etc/baltrad-exchange.properties" -e "s#baltrad.exchange.server.odim_source\s*=\s*\(.*\)#baltrad.exchange.server.odim_source = $PREFIX/etc/odim_source.xml#g"
  sed -i "$PREFIX/etc/baltrad-exchange.properties" -e "s#baltrad.exchange.server.source_db_uri\s*=\s*\(.*\)#baltrad.exchange.server.source_db_uri = sqlite://$PREFIX/var/source.db#g"
  sed -i "$PREFIX/etc/baltrad-exchange.properties" -e "s#baltrad.exchange.server.db_uri\s*=\s*\(.*\)#baltrad.exchange.server.db_uri = sqlite://$PREFIX/var/baltrad-exchange.db#g"
  
  if [ ! -f "$PREFIX/etc/server.cert" ]; then
    if [ "$SERVER_SUBJECT" = "" ]; then
      SERVER_SUBJECT="/C=SE/ST=State/L=City/O=This/CN=$NODENAME"
    fi
    openssl req  -nodes -new -x509  -keyout "$PREFIX/etc/server.key" -out "$PREFIX/etc/server.cert" -subj="$SERVER_SUBJECT" > /dev/null 2>&1 || exit_with_message "Could not create server key"
  fi
  sed -i "$PREFIX/etc/baltrad-exchange.properties" -e "s#baltrad.exchange.server.certificate\s*=\s*\(.*\)#baltrad.exchange.server.certificate = $PREFIX/etc/server.cert#g"
  sed -i "$PREFIX/etc/baltrad-exchange.properties" -e "s#baltrad.exchange.server.key\s*=\s*\(.*\)#baltrad.exchange.server.key = $PREFIX/etc/server.key#g"
}

# Updates the baltrad-exchange.service file with relevant information for running with a local installation
#
update_baltrad_exchange_service()
{
  cp "$PROJECTFOLDER/misc/baltrad-exchange.service" "$PREFIX/etc/"
  
  sed -i "$PREFIX/etc/baltrad-exchange.service" -e "s#^PIDFile\s*=\s*\(.*\)#PIDFile=/run/baltrad/baltrad-exchange-server.pid#g"

  sed -i "$PREFIX/etc/baltrad-exchange.service" -e "s#^User\s*=\s*\(.*\)#User=$USERNAME#g"
  sed -i "$PREFIX/etc/baltrad-exchange.service" -e "s#^Group\s*=\s*\(.*\)#Group=$GROUPNAME#g"

  EXECSTART="$PREFIX/local-env/bin/baltrad-exchange-server --pidfile=/run/baltrad/baltrad-exchange-server.pid --conf=$PREFIX/etc/baltrad-exchange.properties"

  sed -i "$PREFIX/etc/baltrad-exchange.service" -e "s#^ExecStart\s*=\s*\(.*\)#ExecStart=$EXECSTART#g"
}

# Performs the actual installation of baltrad-exchange
#
install_baltrad_exchange()
{
  cd "$PROJECTFOLDER" || exit_with_message "Could not change into $PROJECTFOLDER"
  python3 -m pip install . || exit_with_message "Could not install baltrad-exchange software"
  if [ ! -f "$PREFIX/etc/baltrad-exchange.properties" ]; then
    create_initial_configuration
  fi
  
  update_baltrad_exchange_service
}

# Handle arguments
for arg in $*; do
  case $arg in
    --prefix=*)
      PREFIX=`echo $arg | sed 's/--prefix=//'`
      ;;
    --nodename=*)
      NODENAME=`echo $arg | sed 's/--nodename=//'`
      ;;
    --odim_source=*)
      ODIM_SOURCE=`echo $arg | sed 's/--odim_source=//'`
      ;;
    --subject=*)
      SERVER_SUBJECT=`echo $arg | sed 's/--subject=//'`
      ;;
    --user=*)
      USERNAME=`echo $arg | sed 's/--user=//'`
      ;;
    --group=*)
      GROUPNAME=`echo $arg | sed 's/--group=//'`
      ;;
    --noprompt)
      ASKPROMPT=no
      ;;
    *)
      exit_with_message "Unknown option $arg"
  esac
done

echo "Installing software in $PREFIX"
echo "Nodename    : $NODENAME"
echo "Runas user  : $USERNAME"
echo "Runas group : $GROUPNAME"

if [ "$ASKPROMPT" = "yes" ]; then
  read -p "Is this correct (y/n) [y]: " yesno
  if [ "$yesno" = "" ]; then
    yesno="y"
  fi

  case $yesno in
    [Yy]* ) break;;
    [Nn]* ) 
      exit
      ;;
    *) 
      exit_with_message "Please answer yes or no."
      ;;
  esac
fi

# If we get here, run installation process.
#
create_install_folders

activate

install_dependencies

install_baltrad_exchange

# Print some relevant information about installation.
echo ""
echo "-----------------------------------------------------------------"
echo ""
echo "Local installation successful!"
echo ""
echo "A systemd service script can be found here: $PREFIX/etc/baltrad-exchange.service"
echo "To run the baltrad-exchange server as a systemd process, just copy the file to /usr/lib/systemd/system."
echo "Then run sudo systemctl reload-daemon"
echo ""
echo "Example configuration files can be found in: $PROJECTFOLDER/etc and should be added to $PREFIX/config/."
echo "You can found a userguide at: https://baltrad.github.io/baltrad-exchange/"
echo ""

