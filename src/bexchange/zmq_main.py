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

## Main functions for the baltrad-exchange-zmq

## @file
## @author Anders Henja, SMHI
## @date 2024-01-11
from __future__ import print_function

import logging
import os
import sys

from bexchange import config,exchange_optparse
from bexchange.client import zmqcmd

def extract_command(args):
    command = None
    result_args = []
    for arg in args:
        if not command and not arg.startswith("-"):
            command = arg
        else:
            result_args.append(arg)
    return command, result_args

def add_loghandler(logger, handler, formatter=None):   
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def run():
    optparser = exchange_optparse.create_parser()
    usgstr = "%s COMMAND [ARGS]\n" % (os.path.basename(sys.argv[0]))
    usgstr = usgstr + "\nwhere COMMAND can be one of:\n"
    for k in zmqcmd.Command.get_commands():
        usgstr = usgstr + " - %s\n"%k
    usgstr = usgstr + "\nto get more information about a specific command, write %s <COMMAND> --help\n"%(os.path.basename(sys.argv[0]))
    
    optparser.set_usage(usgstr)
    
    optparser.add_option(
        "-v", "--verbose", dest="verbose",
        action="store_true",
        help="be verbose")

    optparser.add_option(
        "--logfile", type="path", action="store",
        help="location of the log file"
    )
    command_name, args = extract_command(sys.argv[1:])

    if not command_name:
        optparser.print_usage()
        raise SystemExit(1)

    try:
        command = zmqcmd.Command.get_implementation_by_name(command_name)()
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

    default_formatter = logging.Formatter('%(asctime)-15s %(levelname)-8s %(message)s')
    #logging.basicConfig(format="'%(asctime)-15s %(levelname)-8s %(message)s'")
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if opts.verbose:
        logger.setLevel(logging.DEBUG)

    if opts.logfile:
        handler = logging.handlers.WatchedFileHandler(opts.logfile)
        add_loghandler(logger, handler, default_formatter)
    else:
        handler = logging.StreamHandler(sys.stdout)
        add_loghandler(logger, handler, default_formatter)

    try:
        return command.execute(opts, args)
    except zmqcmd.ExecutionError as e:
        optparser.print_usage()
        sys.exit(1)
