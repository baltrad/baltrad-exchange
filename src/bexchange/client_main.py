# Copyright (C) 2021- Swedish Meteorological and Hydrological Institute (SMHI)
#
# This file is part of baltrad-exchange.
#
# baltrad-exchange is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# baltrad-exchange is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with baltrad-exchange.  If not, see <http://www.gnu.org/licenses/>.
###############################################################################

## Main functions for the baltrad-exchange-client

## @file
## @author Anders Henja, SMHI
## @date 2021-08-18
from __future__ import print_function

import logging
import os
import sys

from bexchange import config,exchange_optparse
from bexchange.client import cmd,rest

# Default configuration file.
DEFAULT_CONFIG = "/etc/baltrad/exchange/etc/baltrad-exchange.properties"

def extract_command(args):
    command = None
    result_args = []
    for arg in args:
        if not command and not arg.startswith("-"):
            command = arg
        else:
            result_args.append(arg)
    return command, result_args

def read_config(conffile):
    if not conffile:
        raise SystemExit("configuration file not specified")
    try:
        return config.Properties.load(conffile)
    except IOError:
        raise SystemExit("failed to read configuration from " + conffile)

def run():
    optparser = exchange_optparse.create_parser()
    usgstr = "%s COMMAND [ARGS]\n" % (os.path.basename(sys.argv[0]))
    usgstr = usgstr + "\nwhere COMMAND can be one of:\n"
    for k in cmd.Command.get_commands():
        usgstr = usgstr + " - %s\n"%k
    usgstr = usgstr + "\nto get more information about a specific command, write %s <COMMAND> --help\n"%(os.path.basename(sys.argv[0]))
    
    optparser.set_usage(usgstr)
    
    optparser.add_option(
        "--conf", dest="conf", default=DEFAULT_CONFIG,
        help="The default configuration file to extract server info from unless overridden by other options"
    )

    optparser.add_option(
        "--noconf", dest="noconf", default=False, action="store_true",
        help="If conf file not should be identified and only options should be used.")

    optparser.add_option(
        "--url", dest="server_url",
        help="Exchange server URL.",
    )
    
    optparser.add_option(
        "-v", "--verbose", dest="verbose",
        action="store_true",
        help="be verbose",
    )
    optparser.add_option(
        "-t", "--type", dest="type",
        help="Type of encryption to use, currently the internal crypto or keyczar.")
    
    optparser.add_option(
        "-k", "--key", dest="key",
        help="path to private key to sign messages with"
    )
    optparser.add_option(
        "-n", "--name", dest="name",
        help="the name to use (if it differs from the key path basename)"
    )

    command_name, args = extract_command(sys.argv[1:])

    if not command_name:
        optparser.print_usage()
        raise SystemExit(1)

    try:
        command = cmd.Command.get_implementation_by_name(command_name)()
    except LookupError:
        print("'%s' is not a valid command." % command_name, file=sys.stderr)
        raise SystemExit(1)
    
    optparser.set_usage(
        "%s %s [OPTIONS]" % (
            os.path.basename(sys.argv[0]),
            command_name
        )
    )
    command.update_optionparser(optparser)

    opts, args = optparser.parse_args(args)

    serverUrl = "https://localhost:8089"
    cryptoType = "crypto"
    keyPath = None
    nodeName = None

    if not opts.noconf and os.path.exists(opts.conf):
        conf = read_config(opts.conf)
        serverUrl = conf.get("baltrad.exchange.uri", "https://localhost:8089")
        cryptoProviders = conf.get("baltrad.exchange.auth.providers", "crypto")
        cryptoProviders = cryptoProviders.split(",")
        cryptos = [x.strip() for x in cryptoProviders]
        if "crypto" in cryptos:
            cryptoType = "crypto"
        elif "keyczar" in cryptos:
            cryptoType = "keyczar"
        else:
            cryptoType = "noauth"
        keyPath = conf.get("baltrad.exchange.auth.%s.private.key"%cryptoType, None)
        nodeName = conf.get("baltrad.exchange.node.name", None)
    else:
        print("Property file is not used")

    if opts.type is not None:
        cryptoType = opts.type
    if opts.key is not None:
        keyPath = opts.key
    if opts.name is not None:
        nodeName = opts.name

    logging.basicConfig(format="%(message)s")
    if opts.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    auth = rest.NoAuth()
    if keyPath:
        if cryptoType == "crypto":
            auth = rest.CryptoAuth(keyPath, nodeName)
        elif cryptoType=="tink":
            auth = rest.TinkAuth(keyPath, nodeName)
        else:
            auth = rest.NoAuth()

    database = rest.RestfulServer(serverUrl, auth)

    try:
        return command.execute(database, opts, args)
    except cmd.ExecutionError as e:
        optparser.print_usage()
        sys.exit(1)
