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

## Commands provided by the baltrad-exchange-zmq

## @file
## @author Anders Henja, SMHI
## @date 2024-01-11
from __future__ import print_function        

from abc import abstractmethod, ABCMeta
import abc

import os, sys
import socket
import urllib.parse as urlparse
import pkg_resources
import datetime,time,logging
import subprocess
from tempfile import NamedTemporaryFile

logger = logging.getLogger("bexchange.client.zmqcmd")

class ExecutionError(RuntimeError):
    pass

class Command(object):
    """command-line client command interface
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def update_optionparser(self, parser):
        raise NotImplementedError()
    
    @abstractmethod
    def execute(self, opts, args):
        """execute this command

        :param opts: options passed from command line
        :param args: arguments passed from command line
        """
        raise NotImplementedError()

    def __call__(self, opts, args):
        return self.execute(opts, args)

    @classmethod
    def get_implementation_by_name(cls, name):
        """get an implementing class by name

        the implementing class is looked up from 'baltrad.zmq.commands'
        entry point. 

        :raise: :class:`LookupError` if not found
        """
        try:
            return pkg_resources.load_entry_point(
                "bexchange",
                "bexchange.zmq.commands",
                name
            )
        except ImportError:
            raise LookupError(name)

    @classmethod
    def get_commands(cls):
        return pkg_resources.get_entry_map("bexchange")["bexchange.zmq.commands"].keys()

class Monitor(Command):
    def update_optionparser(self, parser):
        usg = parser.get_usage().strip()

        description = """
        
Connects to a publisher and monitors the published files.
        """

        usage = usg + description

        parser.set_usage(usage)

        parser.add_option(
            "--address", dest="address",
            default="tcp://localhost:8079",
            help="The address of the publisher that should be connected to.")

        parser.add_option(
            "--hmac", dest="hmac",
            default=None,
            help="The hmac key to be used for authenticating the messages.")

        parser.add_option(
            "--dburi", 
            default="sqlite:////tmp/baltrad-zmq-monitor.db",
            help="The uri name for the db-file")

        parser.add_option(
            "--nrfiles", dest="nrfiles",
            default=0,
            type="int",
            help="The number of files to be handled before breaking. If 0, the endless loop")

        parser.add_option(
            "--tmpdir", 
            type="path", 
            action="store",
            help="location where temporary files should be stored")

        parser.add_option(
            "--quantities",
            action="store_true",
            default=False,
            help="If quantities should be extracted or not. Default False.")

    def execute(self, opts, args):
        try:
            import zmq
        except ImportError:
            print("pyzmq is not installed! Aborting!")
            sys.exit(127)
        from bexchange.net.zmq.zmqmonitor import zmqmonitor

        logger.info("Starting monitor")
        monitor = zmqmonitor(opts.address, opts.hmac, opts.dburi, opts.tmpdir, opts.quantities)
        monitor.run(opts.nrfiles)
