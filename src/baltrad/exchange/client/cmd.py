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
import os, sys
import socket
import urllib.parse as urlparse
import pkg_resources
import datetime,time
import subprocess
from tempfile import NamedTemporaryFile

from http import client as httplibclient

try:
    import tink
    from tink import signature
    from tink import aead
    from tink import core
    from tink import cleartext_keyset_handle
except:
    pass

# This should always be available
from baltrad.exchange import crypto

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

    @classmethod
    def get_commands(cls):
        return pkg_resources.get_entry_map("baltrad.exchange")["baltrad.exchange.client.commands"].keys()

class StoreFile(Command):
    def update_optionparser(self, parser):
        parser.set_usage(parser.get_usage().strip() + " FILE [, FILE]")

    def execute(self, server, opts, args):
        for path in args: 
            with open(path, "rb") as data:
                entry = server.store(data)
            print("%s stored"%(path))

class BatchTest(Command):
    SRC_MAPPING={
        "sekrn":"WMO:02032,RAD:SE40,PLC:Kiruna,CMT:sekrn,NOD:sekrn",
        "sella":"WMO:02092,RAD:SE41,PLC:Luleå,CMT:sella,NOD:sella",
        "seosd":"WMO:02200,RAD:SE42,PLC:Östersund,CMT:seosd,NOD:seosd",
        "seoer":"WMO:02262,RAD:SE43,PLC:Örnsköldsvik,CMT:seoer,NOD:seoer",
        "sehuv":"WMO:02334,RAD:SE44,PLC:Hudiksvall,CMT:sehuv,NOD:sehuv",
        "selek":"WMO:02430,RAD:SE45,PLC:Leksand,CMT:selek,NOD:selek",
        "sehem":"WMO:02588,RAD:SE47,PLC:Hemse,CMT:sehem,NOD:sehem",
        "seatv":"WMO:02570,RAD:SE48,PLC:Åtvidaberg,CMT:seatv,NOD:seatv",
        "sevax":"WMO:02600,RAD:SE49,PLC:Vara,CMT:sevax,NOD:sevax",
        "seang":"WMO:02606,RAD:SE50,PLC:Ängelholm,CMT:seang,NOD:seang",
        "sekaa":"WMO:02666,RAD:SE51,PLC:Karlskrona,CMT:sekaa,NOD:sekaa",
        "sebaa":"WMO:00000,RAD:SE52,PLC:Bålsta,CMT:sebaa,NOD:sebaa",
        }
    def update_optionparser(self, parser):
        parser.add_option(
            "--basefile", dest="basefile",
            help="Basefile that should be modified and injected")
        
        parser.add_option(
            "--datetime", dest="datetime",
            help="Datetime")

        parser.add_option(
            "--sources", dest="sources",
            default="sekrn,sella,seosd,seoer,sehuv,selek,sehem,seatv,sevax,seang,sekaa,sebaa",
            help="The sources")
    
        parser.add_option(
            "--periods", dest="periods", type="int",
            default=1,
            help="Number of periods")
        
        parser.add_option(
            "--interval", dest="interval", type="int",
            default=5,
            help="Minutes between each period")
    
    def execute(self, server, opts, args):
        import _raveio, _polarvolume, _polarscan
        if not opts.basefile:
            raise "No basefile provided"
        
        dt = self.parse_datetime_str(opts.datetime, opts.interval)
        if not opts.datetime:
            dt = self.get_closest_time(opts.interval)
        
        for pindex in range(opts.periods):
            tstr = (dt + datetime.timedelta(minutes = pindex*opts.interval)).strftime("%Y%m%d%H%M%S")
            o = _raveio.open(opts.basefile).object
            d = tstr[:8]
            t = tstr[8:]
            o.date = d
            o.time = t
            
            for src in opts.sources.split(","):
                o.source = self.SRC_MAPPING[src]
                rio = _raveio.new()
                rio.object = o
                with NamedTemporaryFile() as f:
                    rio.save(f.name)
                    with open(f.name, "rb") as data:
                        entry = server.store(data)                    

    def get_closest_time(self, interval):
        t = time.localtime()
        oz = t.tm_min%interval
        return datetime.datetime(t.tm_year,t.tm_mon,t.tm_mday,t.tm_hour,t.tm_min-oz,0)

    def parse_datetime_str(self, dtstr, interval):
        year = int(dtstr[:4])
        month = int(dtstr[4:6])
        mday = int(dtstr[6:8])
        hour = int(dtstr[8:10])
        minute = int(dtstr[10:12])
        minute = minute - minute%interval
        return datetime.datetime(year,month,mday,hour,minute,0)

class CreateKeys(Command):
    def update_optionparser(self, parser):
        parser.add_option(
            "--library", dest="library", default="internal",
            help="Library to use for generating key-pair to create. Default: Use internal key generation. Other libraries can be tink ")

        parser.add_option(
            "--encryption", dest="encryption", default="dsa",
            help="Encryption method to use. For internal use you can either choose dsa or rsa. Default is: dsa")

        parser.add_option(
            "--destination", dest="destination", default=".",
            help="Directory where the keys should be placed. Default is current directory.")

        parser.add_option(
            "--nodename", dest="nodename",
            help="Name of the node for this server.")
        
    
    def execute(self, server, opts, args):
        if not opts.nodename:
            raise Exception("Must specify --nodename")
        
        if opts.library == "internal":
            self.create_internal_key(opts)
        elif opts.library == "tink":
            self.create_tink_key(opts)
        #elif opts.library == "keyczar":
        #    self.create_keyczar_keys(opts)
        else:
            print("Unsupported encryption library: %s"%opts.library)

    def create_internal_key(self, opts):
        if opts.encryption != "dsa" and opts.encryption != "rsa":
            print("Only supported encryption are dsa or rsa when using internal crypto")
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

    def create_tink_key(self, opts):
        signature.register()

        #parser.add_option(
        #    "--encryption", dest="encryption", default="ed25519",
        #    help="Encryption method to use. Default is: ed25519")
        
        privkey = "private_%s.json"%opts.nodename
        pubkey = "public_%s.json"%opts.nodename
        
        #handle = tink.new_keyset_handle(signature.signature_key_templates.ECDSA_P256)
        handle = tink.new_keyset_handle(signature.signature_key_templates.ED25519)
        public_handle = handle.public_keyset_handle()
  
        with open(privkey, "wt") as kf:
            cleartext_keyset_handle.write(tink.JsonKeysetWriter(kf), handle)
    
        with open(pubkey, "wt") as kf:
            writer = tink.JsonKeysetWriter(kf)
            cleartext_keyset_handle.write(tink.JsonKeysetWriter(kf), public_handle)

    def createdir(self, d):
        if not os.path.exists(d):
            os.mkdir(dir)
        elif not os.path.isdir(d):
            raise Exception("%s exists but is not a directory"%d)

    #def keyczar_tool(self, *module_args):
    #    python_bin = sys.executable
    #    keytool = "keyczar.tool.keyczart"
    #    args = [python_bin, "-m", keytool]
    #    args.extend(module_args)
    #    ocode = subprocess.call(args)
    #    if ocode != 0:
    #        raise Exception("keytool command failed")
    #  
    #def create_priv_pub_keys(self, keys_root, nodename):
    #    priv_nodekey = "%s/%s.priv"%(keys_root, nodename)
    #    pub_nodekey = "%s/%s.pub"%(keys_root, nodename)
    #    if not os.path.exists(priv_nodekey):
    #        self.createdir(priv_nodekey)
    #        self.keyczar_tool("create",
    #            "--location=%s" % priv_nodekey,
    #            "--purpose=sign",
    #            "--name=%s" % nodename,
    #            "--asymmetric=dsa")
    #        self.keyczar_tool("addkey",
    #            "--location=%s" % priv_nodekey,
    #            "--status=primary")
    # 
    #    if not os.path.exists(pub_nodekey):
    #        self.createdir(pub_nodekey)
    #        self.keyczar_tool("pubkey",
    #            "--location=%s" % priv_nodekey,
    #            "--destination=%s" % pub_nodekey)
    #                   
    #def create_keyczar_keys(self, opts):
    #    pass
