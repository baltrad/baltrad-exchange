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

## Commands provided by the baltrad-exchange-config tool

## @file
## @author Anders Henja, SMHI
## @date 2021-08-18
from __future__ import print_function        

from abc import abstractmethod, ABCMeta
import abc

import json
import os, sys
import socket
import urllib.parse as urlparse
import pkg_resources
import datetime,time
import subprocess
from tempfile import NamedTemporaryFile

from http import client as httplibclient

# This should always be available
from baltrad.exchange import crypto
from baltrad.exchange.crypto import keyczarcrypto

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

    def __call__(self,opts, args):
        return self.execute(opts, args)

    @classmethod
    def get_implementation_by_name(cls, name):
        """get an implementing class by name

        the implementing class is looked up from 'baltrad.exchange.config.commands'
        entry point. 

        :raise: :class:`LookupError` if not found
        """
        try:
            return pkg_resources.load_entry_point(
                "baltrad.exchange",
                "baltrad.exchange.config.commands",
                name
            )
        except ImportError:
            raise LookupError(name)

    @classmethod
    def get_commands(cls):
        return pkg_resources.get_entry_map("baltrad.exchange")["baltrad.exchange.config.commands"].keys()

class CreateKeys(Command):
    def update_optionparser(self, parser):
        parser.add_option(
            "--type", dest="type", default="crypto",
            help="Library to use for generating key-pair to create. Default: crypto (which is the internal key handling). Other libraries can be keyczar ")

        parser.add_option(
            "--encryption", dest="encryption", default="dsa",
            help="Encryption method to use. For internal use you can either choose dsa or rsa. Default is: dsa")

        parser.add_option(
            "--destination", dest="destination", default=".",
            help="Directory where the keys should be placed. Default is current directory.")

        parser.add_option(
            "--nodename", dest="nodename",
            help="Name of the node for this server.")
        
    
    def execute(self, opts, args):
        if not opts.nodename:
            raise Exception("Must specify --nodename")
        
        if opts.type == "crypto":
            self.create_crypto_key(opts)
        elif opts.type == "keyczar":
            self.create_keyczar_keys(opts)
        else:
            print("Unsupported encryption library: %s"%opts.library)

    def create_crypto_key(self, opts):
        if opts.encryption != "dsa" and opts.encryption != "rsa":
            print("Only supported encryption are dsa or rsa when using internal crypto")
            return
        
        privatek = crypto.create_key(encryption=opts.encryption)
        
        if not os.path.exists(opts.destination):
            os.makedirs(opts.destination)
        
        privatek.exportPEM("%s/%s.private"%(opts.destination, opts.nodename))
        privatek.publickey().exportPEM("%s/%s.public"%(opts.destination, opts.nodename))
        privatek.publickey().exportJSON("%s/%s_public.json"%(opts.destination, opts.nodename), opts.nodename)

        print("Created: ")
        print("  Private key: %s/%s.private"%(opts.destination, opts.nodename))
        print("  Public  key: %s/%s.public"%(opts.destination, opts.nodename))
        print("  Public json: %s/%s_public.json"%(opts.destination, opts.nodename))

    def createdir(self, d):
        if not os.path.exists(d):
            os.mkdir(dir)
        elif not os.path.isdir(d):
            raise Exception("%s exists but is not a directory"%d)

    def create_keyczar_keys(self, opts):
        if opts.encryption != "dsa":
            print("Only supported encryption is dsa for keyczar crypto")
            return
        

        if not os.path.exists(opts.destination):
            os.makedirs(opts.destination)
        
        privkeyfolder = "%s/%s.priv"%(opts.destination, opts.nodename)
        pubkeyfolder = "%s/%s.pub"%(opts.destination, opts.nodename)
        
        keyczar_signer = keyczarcrypto.create_keyczar_key()
        keyczar_verifier = keyczarcrypto.keyczar_verifier(keyczar_signer._key)
        
        keyczar_signer.export(privkeyfolder, opts.nodename)
        keyczar_verifier.export(pubkeyfolder, opts.nodename)

        print("Created: ")
        print("  Private key: %s"%privkeyfolder)
        print("  Public  key: %s"%pubkeyfolder)

class PostJsonMessage(Command):
    def update_optionparser(self, parser):
        parser.set_usage(parser.get_usage().strip() + " MESSAGE")

    def execute(self, server, opts, args):
        entry = server.post_json_message(args[0])
        #for path in args: 
        #    with open(path, "rb") as data:
        #        entry = server.store(data)
        #    print("%s stored"%(path))
