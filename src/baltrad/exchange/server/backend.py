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

## The server backend that provides all functionality to the clients. 

## @file
## @author Anders Henja, SMHI
## @date 2021-08-18

from baltrad.exchange import backend
from baltrad.exchange.server import sqlbackend
from baltrad.exchange.matching import filters, metadata_matcher
from baltrad.exchange.storage import storages
from baltrad.exchange.processor import processors
from baltrad.exchange.server.subscription import subscription_manager
from baltrad.exchange.net import publishers
from baltrad.exchange.runner import runners
from baltrad.exchange import auth

import glob
import json
import time, datetime
import threading
import os,stat
import uuid
from types import SimpleNamespace
import logging
from baltrad.bdbcommon import oh5, expr

from baltrad.bdbcommon.oh5 import (
    Attribute,
    Group,
    Metadata,
    Source,
)
#from symbol import subscript
from baltrad.exchange.net.publishers import publisher_manager
from builtins import issubclass
from baltrad.exchange.util import message_aware

logger = logging.getLogger("baltrad.exchange.server.backend")

class HandledFiles(object):
    """Keeps track of recently handled files. Probably should be either a sqlite db or
    a dictionary variant with an aged limit.
    """
    def __init__(self, limit=500):
        self.limit = limit
        self._handled = []
        self.lock = threading.Lock()
        
    def handled(self, bdbhash):
        return bdbhash in self._handled

    def add(self, bdbhash):
        with self.lock:
            if bdbhash in self._handled:
                return False
            self._handled.insert(0, bdbhash)
            if len(self._handled) > self.limit:
                self._handled.pop()
        return True

class SimpleBackend(backend.Backend):
    """A backend taking care of the exchange

    :param engine_or_url: an SqlAlchemy engine or a database url
    :param storage: a `~.storage.FileStorage` instance to use.
    """
    def __init__(self, confdirs, nodename, authmgr, source_db_uri, odim_source_file):
        """Constructor
        :param confdirs: a list of directories where the configuration (.json) files can be found
        :param nodename: name of this node
        :param authmgr: the authorization manager for registering keys
        :param source_db_uri: The uri to the source db
        :param odim_source_file: the file containing odim sources for identification of incomming files
        """
        self.confdirs = confdirs
        self.nodename = nodename
        self.authmgr = authmgr
        
        self.handled_files = HandledFiles()
        
        self._hasher = oh5.MetadataHasher()
        
        self.subscriptions = []
        self.publications = []
        self.storage_manager = storages.storage_manager()
        self.processor_manager = processors.processor_manager()
        self.odim_source_file = odim_source_file
        self.source_manager = sqlbackend.SqlAlchemySourceManager(source_db_uri)
        self.source_manager.add_sources(self.read_bdb_sources(self.odim_source_file))
        self.filter_manager = filters.filter_manager()
        self.runner_manager = runners.runner_manager()

        self.initialize_configuration(self.confdirs)
    
    def get_storage_manager(self):
        """
        :returns the storage manager used
        """
        return self.storage_manager    

    def get_auth_manager(self):
        """
        :returns the authorization manager used
        """
        return self.authmgr

    def initialize_configuration(self, confdirs):
        """Initializes the configuration from each dir
        :param confdirs: a list of directories where the configuration (.json) files can be found
        """
        for d in confdirs:
            logger.info("Processing directory: %s" % d)
            self.process_conf_dir(d.strip())
    
    def read_bdb_sources(self, odim_source_file):
        """Reads and parses the odim sources
        :param odim_source_file: file containing the odim source definitions
        :returns a list of odim sources
        """
        with open(odim_source_file) as f:
            return oh5.Source.from_rave_xml(f.read())
    
    def process_conf_dir(self, d):
        """process one configuration dir. Will scan for all .json files in provided directory and determine
        if the files can be used for configuration or not.
        :param d: a directory containing configuration files
        """
        files = glob.glob("%s/*.json"%d)
        
        for f in files:
            logger.info("Processing configuration file: %s"%f)
            with open(f,"r") as fp:
                data = json.load(fp)
                if "publication" in data:
                    p = publisher_manager.from_conf(data["publication"], self)
                    self.publications.append(p)

                elif "subscription" in data:
                    subs = subscription_manager.from_conf(data["subscription"], self)
                    self.subscriptions.append(subs)
                
                elif "storage" in data:
                    #s = self.storage_manager.from_value(data["storage"])
                    s = self.storage_manager.from_conf(data["storage"], self)
                    logger.info("Adding storage: %s of type %s"%(s.name(), type(s)))
                    self.storage_manager.add_storage(s)
                
                elif "runner" in data:
                    runner = self.runner_manager.from_conf(data["runner"], self)
                    logger.info("Adding runner: %s"%(str(runner)))
                    self.runner_manager.add_runner(runner)
                
                elif "processor" in data:
                    p = processors.processor_manager.from_conf(data["processor"], self)
                    logger.info("Adding processor: %s"%(p.name()))
                    self.processor_manager.add_processor(p)
        
        self.runner_manager.start()

    @classmethod
    def from_conf(cls, conf):
        """create an instance from configuration
        parameters are looked up under *'baltrad.exchange.server'*.
        """
        nodename = conf.get("baltrad.exchange.node.name")
        
        fconf = conf.filter("baltrad.exchange.server.")
        
        authmgr = auth.auth_manager.from_conf(conf)
        
        configdirs = fconf.get_list("config.dirs", default="/etc/baltrad/exchange/config", sep=",") #fconf.get("config.dirs", default="/etc/baltrad/exchange/config")

        source_db_uri = fconf.get("source_db_uri", default="sqlite:///var/cache/baltrad/exchange/source.db")

        odim_source_file = fconf.get("odim_source")
        return SimpleBackend(
            configdirs,
            nodename,
            authmgr,
            source_db_uri,
            odim_source_file
          )

    def store_file(self, path, nid):
        """handles an incomming file and determines if it should be managed by the subscriptions or not.
        :param path: the full path to the file to be handled
        :param nodename: the name/id of the node that the file comes from
        :returns the metadata from the file
        """
        meta = self.metadata_from_file(path)

        logger.info("Received file from %s: %s, %s, %s %s" % (nid, meta.bdb_metadata_hash, meta.bdb_source_name, meta.what_date, meta.what_time))
        
        if not self.handled_files.add(meta.bdb_metadata_hash):
            logger.info("File recently handled, ignoring it: %s, %s" % (meta.bdb_metadata_hash, meta.bdb_source_name))
            return None
        
        for subscription in self.subscriptions: # Should only be passive subscriptions here. Active subscriptions should be handled in separate threads.
            if len(subscription.allowed_ids()) > 0 and nid not in subscription.allowed_ids():
                continue
            
            if subscription.filter_matching(meta):
                for storage in subscription.storages():
                    self.storage_manager.store(storage, path, meta)

                self.publish(path, meta)
                    
                self.processor_manager.process(path, meta)
        return meta

    def post_message(self, json_message, nodename):
        """ensures that a posted message arrives to interested parties
        :param json_message: The json message
        :type path: string
        :param nodename: The origin that sent the message
        """
        for r in self.runner_manager.get_runners():
            if isinstance(r, message_aware):
                r.handle_message(json_message, nodename)

    def publish(self, path, meta):
        """publishes the file on each interested publisher
        :param path: full path to the file to be published
        :param meta: meta of file to be published
        """
        for publication in self.publications:
            matcher = metadata_matcher.metadata_matcher()
            if publication.active() and matcher.match(meta, publication.filter().to_xpr()):
                publication.publish(path, meta)
    
    def metadata_from_file(self, path):
        """creates metadata from the file
        :param path: full path to the file
        :returns the metadata
        """
        return self.metadata_from_file_internal(path)
    
    def metadata_from_file_bdb(self, path):
        """creates metadata from the file by adding it to the bdb
        :param path: full path to the file
        :returns the metadata
        """
        pass
    
    def metadata_from_file_internal(self, path):
        """creates metadata from the file
        :param path: full path to the file
        :returns the metadata
        """
        meta = oh5.Metadata.from_file(path)
        if not meta.what_source:
            raise LookupError("No source in metadata")
        
        metadata_hash = self._hasher.hash(meta)
        source = self.source_manager.get_source(meta)
        
        meta.bdb_source = source.to_string()
        meta.bdb_source_name = source.name
        meta.bdb_metadata_hash = metadata_hash
        meta.bdb_file_size = os.stat(path)[stat.ST_SIZE]
        
        logger.debug("Got a source identifier: %s"%str(meta.bdb_source))

        stored_timestamp = datetime.datetime.utcnow()
        meta.bdb_stored_date = stored_timestamp.date()
        meta.bdb_stored_time = stored_timestamp.time()

        return meta        
            
    