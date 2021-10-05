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
from baltrad.exchange.net import publishers

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
    def __init__(self, confdirs, nodename, privatekey, odim_source_file):
        self.confdirs = confdirs
        self.nodename = nodename
        self.privatekey = privatekey
        
        self.handled_files = HandledFiles()
        
        self._hasher = oh5.MetadataHasher()
        
        self.subscriptions = []
        self.publications = []
        self.storage_manager = storages.storage_manager()
        
        self.odim_source_file = odim_source_file
        self.source_manager = sqlbackend.SqlAlchemySourceManager()
        self.source_manager.add_sources(self.read_bdb_sources(self.odim_source_file))
        self.filter_manager = filters.filter_manager()

        self.initialize_configuration(self.confdirs)
    
    def get_storage_manager(self):
        return self.storage_manager    

     
    def initialize_configuration(self, confdirs):
        for d in confdirs:
            logger.info("Processing directory: %s" % d)
            self.process_conf_dir(d.strip())
    
    def read_bdb_sources(self, odim_source_file):
        with open(odim_source_file) as f:
            return oh5.Source.from_rave_xml(f.read())
    
    def process_conf_dir(self, d):
        files = glob.glob("%s/*.json"%d)
        
        for f in files:
            with open(f,"r") as fp:
                data = json.load(fp)
                if "publication" in data:
                    p = publisher_manager.from_conf(data["publication"], self)
                    self.publications.append(p)
                elif "subscription" in data:
                    self.subscriptions.append(data["subscription"])
                    #if "crypto" in data["subscription"]:
                    #    c = data["subscription"]["crypto"]
                    #    if "libname" in c and c["libname"] == "keyczar":
                    #        pass
                
                elif "storage" in data:
                    s = self.storage_manager.from_value(data["storage"])
                    logger.info("Adding storage: %s of type %s"%(s.name(), s.type))
                    self.storage_manager.add_storage(s)

    @classmethod
    def from_conf(cls, conf):
        """create an instance from configuration
        parameters are looked up under *'baltrad.exchange.server'*.
        """
        nodename = conf.get("baltrad.exchange.node.name")
        
        fconf = conf.filter("baltrad.exchange.server.")
        
        privatekey = conf.get("baltrad.exchange.key.private", default="/etc/baltrad/exchange/keys/%s.priv"%nodename)
        
        configdirs = fconf.get_list("config.dirs", default="/etc/baltrad/exchange/config", sep=",") #fconf.get("config.dirs", default="/etc/baltrad/exchange/config")

        odim_source_file = fconf.get("odim_source")
        return SimpleBackend(
            configdirs,
            nodename,
            privatekey,
            odim_source_file
          )

    def store_file(self, path, credentials):
        st = time.time()
        meta = self.metadata_from_file(path)
        metadataTime = time.time()
        
        logger.info("File with: %s, %s" % (meta.bdb_metadata_hash, meta.bdb_source_name))
        
        if not self.handled_files.add(meta.bdb_metadata_hash):
            logger.info("File recently handled, ignoring it: %s, %s" % (meta.bdb_metadata_hash, meta.bdb_source_name))
            return None
        
        for subscription in self.subscriptions: # Should only be passive subscriptions here. Active subscriptions should be handled in separate threads.
            #if credentials is not None:
            #    if "crypto" in subscription:
            #        c = subscription["crypto"]
            #        if c["libname"] == "keyzcar":
            #            if len(credentials) > 1 and credentials[0] == "keyczar":
            #                ka = auth.KeyczarAuth()
            if "filter" in subscription:
                filter_ = self.filter_manager.from_value(subscription["filter"])
                matcher = metadata_matcher.metadata_matcher()
                if matcher.match(meta, filter_.to_xpr()):
                    if "storage" in subscription:
                        stores = subscription["storage"]
                        if not isinstance(stores, list):
                            stores = [stores]
                        for storage in stores:
                            self.storage_manager.store(storage, path, meta)
                    self.publish(path, meta)

        return meta

    def publish(self, path, meta):
        for publication in self.publications:
                matcher = metadata_matcher.metadata_matcher()
                if publication.active() and matcher.match(meta, publication.filter().to_xpr()):
                    publication.publish(path, meta)
    
    def metadata_from_file(self, path):
        return self.metadata_from_file_internal(path)
    
    def metadata_from_file_bdb(self, path):
        pass
    
    def metadata_from_file_internal(self, path):
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
            
    