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

from baltrad.exchange import exchange_optparse
from baltrad.exchange.client import cmd,rest

def extract_command(args):
    command = None
    result_args = []
    for arg in args:
        if not command and not arg.startswith("-"):
            command = arg
        else:
            result_args.append(arg)
    return command, result_args

def run():
    optparser = exchange_optparse.create_parser()
    usgstr = "%s COMMAND [ARGS]\n" % (os.path.basename(sys.argv[0]))
    usgstr = usgstr + "\nwhere COMMAND can be one of:\n"
    for k in cmd.Command.get_commands():
        usgstr = usgstr + " - %s\n"%k
    usgstr = usgstr + "\nto get more information about a specific command, write %s <COMMAND> --help\n"%(os.path.basename(sys.argv[0]))
    
    optparser.set_usage(usgstr)
    
    optparser.add_option(
        "--url", dest="server_url",
        default="https://localhost:8089",
        help="Exchange server URL",
    )
    optparser.add_option(
        "-v", "--verbose", dest="verbose",
        action="store_true",
        help="be verbose",
    )
    optparser.add_option(
        "-k", "--keyczar-key", dest="keyczar_key",
        help="path to keyczar key to sign messages with"
    )
    optparser.add_option(
        "-n", "--keyczar-name", dest="keyczar_name",
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
        "%s %s [--url=SERVER_URL]" % (
            os.path.basename(sys.argv[0]),
            command_name
        )
    )
    command.update_optionparser(optparser)

    opts, args = optparser.parse_args(args)

    logging.basicConfig(format="%(message)s")
    if opts.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if opts.keyczar_key:
        auth = rest.KeyczarAuth(opts.keyczar_key, opts.keyczar_name)
    else:
        auth = rest.NoAuth()

    database = rest.RestfulServer(opts.server_url, auth)
    
    try:
        return command.execute(database, opts, args)
    except cmd.ExecutionError as e:
        raise SystemExit(e)
