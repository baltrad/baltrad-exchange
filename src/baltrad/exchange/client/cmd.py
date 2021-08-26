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

## Commands provided by the baltrad-exchange-client

## @file
## @author Anders Henja, SMHI
## @date 2021-08-18
from __future__ import print_function        

from abc import abstractmethod, ABCMeta
import abc

import json
import os
import socket
import urllib.parse as urlparse
import pkg_resources

from http import client as httplibclient
from keyczar import keyczar

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
    def execute(self, database, opts, args):
        """execute this command

        :param database: a database instance to operate on
        :param opts: options passed from command line
        :param args: arguments passed from command line
        """
        raise NotImplementedError()

    def __call__(self, database, opts, args):
        return self.execute(database, opts, args)

    @classmethod
    def get_implementation_by_name(cls, name):
        """get an implementing class by name

        the implementing class is looked up from 'baltrad.bdbclient.commands'
        entry point. 

        :raise: :class:`LookupError` if not found
        """
        try:
            return pkg_resources.load_entry_point(
                "baltrad.exchange",
                "baltrad.exchange.client.commands",
                name
            )
        except ImportError:
            raise LookupError(name)

class StoreFile(Command):
    def update_optionparser(self, parser):
        parser.set_usage(parser.get_usage().strip() + " FILE [, FILE]")

    def execute(self, server, opts, args):
        for path in args: 
            with open(path, "rb") as data:
                entry = server.store(data)
            print("%s stored"%(path))
