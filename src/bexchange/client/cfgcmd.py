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

import json, tarfile
import os, sys, re
import socket
import urllib.parse as urlparse
import pkg_resources
import datetime,time
import subprocess
from tempfile import TemporaryDirectory

from http import client as httplibclient

# This should always be available
from bexchange import config
from bexchange.odimutil import metadata_helper
from bexchange.server import sqlbackend
from bexchange.matching.filters import filter_manager
from bexchange.matching.metadata_matcher import metadata_matcher
from baltrad.bdbcommon import oh5
from bexchange.net import dexutils

from baltradcrypto import crypto
from baltradcrypto.crypto import keyczarcrypto

# Default configuration file.
DEFAULT_CONFIG = "/etc/baltrad/exchange/etc/baltrad-exchange.properties"

DEFAULT_TEMPLATE = "/etc/baltrad/exchange/etc/exchange-template.json"


class ExecutionError(RuntimeError):
    pass

def read_config(conffile):
    if not conffile:
        raise SystemExit("configuration file not specified")
    try:
        return config.Properties.load(conffile)
    except IOError:
        raise SystemExit("failed to read configuration from " + conffile)

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

        the implementing class is looked up from 'bexchange.config.commands'
        entry point. 

        :raise: :class:`LookupError` if not found
        """
        try:
            return pkg_resources.load_entry_point(
                "bexchange",
                "bexchange.config.commands",
                name
            )
        except ImportError:
            raise LookupError(name)

    @classmethod
    def get_commands(cls):
        return pkg_resources.get_entry_map("bexchange")["bexchange.config.commands"].keys()

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

class TestFilter(Command):
    def update_optionparser(self, parser):
        usg = parser.get_usage().strip()

        description = """

Provides functionality for matching a file against a json filter. The matching uses the baltrad-db metadata querying and will generate 
a odim-source sqlite database so that the _bdb/source_name, _bdb/source:WMO and other bdb-specific meta attributes can be ued. This is 
in contrast with the naming that instead uses _baltrad/ as prefix for internal meta data usage.

The returned response will be either MATCHING or NOT MATCHING.

Example: baltrad-exchange-config test_filter --odim-source=/etc/baltrad/rave/config/odim_source.xml
                                             --filter=etc/example_subscription.json
                                             /data/in1/sehem_scan_20200414T160000Z.h5

        """

        usage = usg + " <filename>"  + description

        parser.set_usage(usage)        
        #parser.set_usage(parser.get_usage().strip() + " <filename>")

        parser.add_option(
            "--odim-source", dest="odim_source",
            help="The odim source file to use for identifying the source of a file. This command will create a temporary source in /tmp unless underwise specified.")
        
        parser.add_option(
            "--dburi", dest="dburi", default="sqlite:////tmp/bec-config-test-sources.db",
            help="The location where odim sources can be found. Default is to create a temporary db under /tmp.")
        
        parser.add_option(
            "--filter", dest="filter",
            help="Specifies a file containing a filter. Can be either a subscription or publication cfg-file or else a separate file containing toplevel 'filter'")

        parser.add_option(
            "--filter-path", dest="filter_path", default=None,
            help="Path within the json entry where the filter can be found."
        )

    def execute(self, opts, args):
        with open(opts.odim_source) as f:
            sources = oh5.Source.from_rave_xml(f.read())
        source_manager = sqlbackend.SqlAlchemySourceManager(opts.dburi)
        source_manager.add_sources(sources)
        hasher = oh5.MetadataHasher()
        meta = metadata_helper.metadata_from_file(source_manager, hasher, args[0])

        if not opts.filter:
            raise Exception("Need to specify filter file")
        
        with open(opts.filter) as fp:
            json_cfg = json.load(fp)

        if opts.filter_path:
            tmp_json_cfg = json_cfg
            tokens=opts.filter_path.split("/")
            if tokens[0]=="":
                tokens=tokens[1:]

            for t in tokens:
                if t in tmp_json_cfg:
                    tmp_json_cfg = tmp_json_cfg[t]
                else:
                    raise Exception("No such entry: %s"%opts.filter_path)
            tfilter = filter_manager().from_value(tmp_json_cfg)
        else:
            if "subscription" in json_cfg and "filter" in json_cfg["subscription"]:
                tfilter = filter_manager().from_value(json_cfg["subscription"]["filter"])
            elif "publication" in json_cfg and "filter" in json_cfg["publication"]:
                tfilter = filter_manager().from_value(json_cfg["publication"]["filter"])
            elif "filter" in json_cfg:
                tfilter = filter_manager().from_value(json_cfg["filter"])
            else:
                raise Exception("Unsupported json-format")

        matcher = metadata_matcher()
        if matcher.match(meta, tfilter.to_xpr()):
            print("MATCHING")
        else:
            print("NOT MATCHING")

class CreatePublication(Command):
    def update_optionparser(self, parser):
        usg = parser.get_usage().strip()

        description = """

Creates a publication from the provided template and the provided property-file. If possible, the
property file will be identified by checking standard installation path. An atempt to find the
template will be used base on default location / name as well. The resulting json file should be 
possible to put in the local server config catalogue without modifications. If different sender 
protocols or different connection strategies should be used the configuration file needs to be modified
manually.

Example: baltrad-exchange-config create_publication --desturi=https://remote.baltrad.node --name="pub to remote node" --output=remote_node_publication.json
        """

        usage = usg + description

        parser.set_usage(usage)

        parser.add_option(
            "--conf", dest="conf", default=DEFAULT_CONFIG,
            help="Specified the property file to use to extract all relevant information to create the publication to specified host.")

        parser.add_option(
            "--template", dest="template", default=DEFAULT_TEMPLATE,
            help="The template to use for generating the publication / subscription.")

        parser.add_option(
            "--desturi", dest="desturi", default="https://localhost:8089",
            help="Specified the target of this publication"
        )

        parser.add_option(
            "--name", dest="publication_name",
            help="The name of this publication. MANDATORY!"
        )

        parser.add_option(
            "--output", dest="output",
            help="The output file name. If not specified, output will printed on stdout"
        )

    def execute(self, opts, args):
        cfg = read_config(opts.conf)

        if not os.path.exists(opts.template):
            print("Must provide template")
            sys.exit(1)

        if not opts.publication_name:
            print("Must provide --name")
            sys.exit(1)

        desturi = opts.desturi

        loaded = None
        with open(opts.template) as fp:
            loaded = json.load(fp)
        
        template = loaded["template"]
        template_publication = template["publication"]
        clazz = "bexchange.net.publishers.standard_publisher"
        template_connection = {"sender": "bexchange.net.senders.rest_sender", "protocol":"crypto"}
        if "class" in template_publication:
            clazz = template_publication["class"]
        extra_arguments={}
        if "extra_arguments" in template_publication:
            extra_arguments = template_publication["extra_arguments"]

        if "connection" in template:
            template_connection = template["connection"]

        publication = {}
        publication["__comment__"] = "This is a comment"
        publication["name"] = opts.publication_name
        publication["class"] = clazz
        publication["extra_arguments"] = extra_arguments
        publication["active"] = True

        connection = template_connection
        connection["class"] = "bexchange.net.connections.simple_connection"
        connection["arguments"] = {}
        connection["arguments"]["sender"] = {}
        connection["arguments"]["sender"]["id"] = "%s sender id"%opts.publication_name
        if template_connection["sender"] == "bexchange.net.senders.rest_sender":
            connection["arguments"]["sender"]["class"] = template_connection["sender"]
            connection["arguments"]["sender"]["arguments"] = {}
            connection["arguments"]["sender"]["arguments"]["address"] = opts.desturi
            connection["arguments"]["sender"]["arguments"]["protocol_version"] = "1.0"

            encryption = "crypto"
            if "encryption" in template_connection:
                encryption = template_connection["encryption"]
            if encryption == "crypto":
                connection["arguments"]["sender"]["arguments"]["crypto"] = {}
                connection["arguments"]["sender"]["arguments"]["crypto"]["libname"] = "crypto"
                connection["arguments"]["sender"]["arguments"]["crypto"]["nodename"] = cfg.get("baltrad.exchange.node.name")
                connection["arguments"]["sender"]["arguments"]["crypto"]["privatekey"] = cfg.get("baltrad.exchange.auth.crypto.private.key")
            else:
                print("Unsupported template encryption")
                sys.exit(0)
        else:
            print("Unsupported template sender")
            sys.exit(1)

        publication["connection"] = connection
        publication["filter"] = template["filter"]

        json_publication={"publication":publication}

        output = json.dumps(json_publication, sort_keys=True, indent=4)
        if opts.output:
            if os.path.exists(opts.output):
                print("File %s already exists"%opts.output)
            else:
                with open(opts.output, "w") as fp:
                    fp.write(output)
                    fp.flush()
        else:
            print(output)

class CreateSubscription(Command):
    def update_optionparser(self, parser):
        usg = parser.get_usage().strip()

        description = """

Creates a subscription package from the provided template and the provided property-file. If possible, the
property file will be identified by checking standard installation path. An atempt to find the
template will be used base on default location / name as well. The output will be a tarball containing of one 
public key and one subscription.json file together with a README file that explains how to use the tarball.
This tar ball should be sent to the admin for the remote server.

Example: baltrad-exchange-config create_subscription --output=subscription_bundle.tar
        """

        usage = usg + description

        parser.set_usage(usage)

        parser.add_option(
            "--conf", dest="conf", default=DEFAULT_CONFIG,
            help="Specified the property file to use to extract all relevant information to create the publication to specified host.")

        parser.add_option(
            "--template", dest="template", default=DEFAULT_TEMPLATE,
            help="The template to use for generating the publication / subscription.")

        parser.add_option(
            "--output", dest="output",
            help="The output file name. Must contain .tar och .tgz or .tar.gz suffix. Will default to <nodename>.tar.gz"
        )

    def execute(self, opts, args):
        cfg = read_config(opts.conf)

        if not os.path.exists(opts.template):
            print("Must provide template. Try copying exchange-template.json from examples!")
            sys.exit(1)

        if not cfg.get("baltrad.exchange.node.name"):
            print("No baltrad.exchange.node.name in property file")
            sys.exit(1)

        output_name = "%s.tar.gz"%cfg.get("baltrad.exchange.node.name")
        if opts.output:
            output_name = opts.output

        if not output_name.endswith(".tar") and not output_name.endswith(".tgz") and not output_name.endswith(".tar.gz"):
            print("output file must end with .tar, .tar.gz or .tgz")
            sys.exit(1)

        loaded = None
        with open(opts.template) as fp:
            loaded = json.load(fp)
        
        template = loaded["template"]
        template_publication = template["publication"]
        clazz = "bexchange.net.publishers.standard_publisher"
        template_connection = {"sender": "bexchange.net.senders.rest_sender", "protocol":"crypto"}
        if "class" in template_publication:
            clazz = template_publication["class"]
        extra_arguments={}
        if "extra_arguments" in template_publication:
            extra_arguments = template_publication["extra_arguments"]
        if "connection" in template:
            template_connection = template["connection"]


        subscription = {}
        subscription["__comment__"] = "This is a comment"
        subscription["_id"] = "subscription from %s"%cfg.get("baltrad.exchange.node.name")
        subscription["active"] = True
        subscription["storage"] = ["default_storage"]
        subscription["_statdef"] = [{"id":"stat-subscription-1", "type": "count"}]
        subscription["allow_duplicates"] = False
        subscription["allowed_ids"] = []

        cryptos = []

        with TemporaryDirectory() as tmpdir:
            foldername = re.sub("(\.tar\.gz|\.tar|\.tgz)$", '', output_name)
            dirname="%s/%s"%(tmpdir, foldername)
            os.makedirs(dirname)

            if template_connection["sender"] == "bexchange.net.senders.rest_sender":
                cryptod = {}
                cryptod["auth"] = "crypto"
                cryptod["conf"] = {}
                cryptod["conf"]["nodename"] = cfg.get("baltrad.exchange.node.name")
                cryptod["conf"]["creator"] = "baltrad.exchange.crypto"
                cryptod["conf"]["pubkey"] = "%s.public"%cfg.get("baltrad.exchange.node.name")
                cryptod["conf"]["type"] = "public"

                privatek = crypto.load_key(cfg.get("baltrad.exchange.auth.crypto.private.key"))
                publick = privatek.publickey()
                publick.exportPEM("%s/%s.public"%(dirname, cfg.get("baltrad.exchange.node.name")))

                cryptod["conf"]["keyType"] = publick.algorithm()

                cryptos.append(cryptod)
            else:
                print("Unsupported template sender")
                sys.exit(1)

            subscription["cryptos"] = cryptos
            subscription["filter"] = template["filter"]

            json_subscription={"subscription":subscription}
            output = json.dumps(json_subscription, sort_keys=True, indent=4)

            with open("%s/%s-subscription.json"%(dirname, cfg.get("baltrad.exchange.node.name")), "w") as fp:
                fp.write(output)
                fp.close()

            with open("%s/README"%dirname, "w") as fp:
                fp.write(self.README(cfg.get("baltrad.exchange.node.name")))
                fp.close()

            tmode = "w"
            if output_name.endswith(".tgz") or output_name.endswith(".tar.gz"):
                tmode = "w:gz"

            with tarfile.open(output_name, tmode) as tar:
                tar.add(dirname, arcname=foldername)

            print("Created %s"%output_name)           

    def README(self, nodename):
        return """Origin: %s
Created: %s

This folder contains two different files. One is a public key originating from %s and the
other is the currently provided subscription configuration.  The public key should be placed in the public key root folder, 
typically /etc/baltrad/exchange/crypto-keys/.

The subscription configuration describes what the template assumes is published from the remote server. If you for example
just want a subset of what is provided, please notifiy the remote server admin about this so that they can modify the 
outgoing publication to keep both their and your bandwidth usage limited.
"""%(nodename, datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), nodename)

class SendDexKey(Command):
    def update_optionparser(self, parser):
        usg = parser.get_usage().strip()

        description = """

In order to be able to setup this node to send files to a DEX-instance it is nessecary to send a key for approval
to the dex-node. The user must specify the public key to pass on as well as the node-name that will be used for 
signing the data. 
NOTE! This is a deprecated behaviour and is just there for backward compatibility purposes.


Example: baltrad-exchange-config send_dexkey --url=https://remote.server --pubkey=... --nodename=....
        """

        usage = usg + description

        parser.set_usage(usage)

        parser.add_option(
            "--url", dest="url",
            help="Specify the url that should receive the public key. The url will get BaltradDex/post_key.htm appended to it.")

        parser.add_option(
            "--pubkey", dest="pubkey",
            help="The public key filename that should be passed to the remote server")

        parser.add_option(
            "--nodename", dest="nodename",
            help="The node-name that will be used during the validation of the signature"
        )

    def execute(self, opts, args):
        if not os.path.exists(opts.pubkey):
            print("Must provide a valid dex public key");
            sys.exit(1)

        try:
            verifier = keyczarcrypto.load_key(opts.pubkey)
            if not isinstance(verifier, keyczarcrypto.keyczar_verifier):
                print("You shouldn't provide the private key")
                raise Exception("You shouldn't provide the private key")
        except:
            import traceback
            traceback.print_exc()
            print("Failed to send the public key")
            sys.exit(1)

        if not opts.nodename:
            print("Must specify nodename")
            sys.exit(1)
        
        if not opts.url:
            print("Must specify url")
            sys.exit(1)
        
        du = dexutils.dexutils(opts.url, opts.nodename)
        du.send_key(opts.pubkey)

class SendDexFile(Command):
    def update_optionparser(self, parser):
        usg = parser.get_usage().strip()


        description = """

Can be used to pass on a HDF5 file using the dex protocol to a remote server. Useful for verifying
the dex-communication.

NOTE! This is a deprecated behaviour and is just there for backward compatibility purposes.

Example: baltrad-exchange-config send_dexfile --url=https://remote.server --privkey=... --nodename=....  <file> <file2> ....
        """

        usage = usg + " FILE [ FILE]" + description

        parser.set_usage(usage)

        parser.add_option(
            "--url", dest="url",
            help="Specify the url that should receive the public key. The url will get BaltradDex/post_key.htm appended to it.")

        parser.add_option(
            "--privkey", dest="privkey",
            help="The private key that should be used to sign the message")

        parser.add_option(
            "--nodename", dest="nodename",
            help="The node-name that will be used during the validation of the signature"
        )

    def execute(self, opts, args):
        if not os.path.exists(opts.privkey):
            print("Must provide a valid dex private key");
            sys.exit(1)

        try:
            signer = keyczarcrypto.load_key(opts.privkey)
            if not isinstance(signer, keyczarcrypto.keyczar_signer):
                print("You need to provide the private key")
                raise Exception("You need to provide the private key")
        except:
            import traceback
            traceback.print_exc()
            sys.exit(1)

        if not opts.nodename:
            print("Must specify nodename")
            sys.exit(1)

        if not opts.url:
            print("Must specify url")
            sys.exit(1)
        
        if len(args) == 0:
            print("Must provide at least one filename")
            sys.exit(1)

        filenames = []
        for p in args:
            if not os.path.isfile(p):
                print("%s is not a file"%p)
                sys.exit(1)
            filenames.append(p)

        du = dexutils.dexutils(opts.url, opts.nodename)
        for f in filenames:
            du.send_file(opts.privkey, f)
