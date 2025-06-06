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

from bexchange import backend
from bexchange.server import sqlbackend
from bexchange.matching import filters, metadata_matcher
from bexchange.storage import storages
from bexchange.processor import processors
from bexchange.server.subscription import subscription_manager
from bexchange.net import publishers
from bexchange.runner import runners
from bexchange import auth, util
from bexchange.odimutil import metadata_helper
from bexchange.statistics.statistics import statistics_manager
from bexchange.db import sqldatabase

import glob
import json
import time, datetime
import threading
import os,stat,sys
import uuid
import pyinotify
from threading import Thread
import re

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
from bexchange.net.publishers import publisher_manager
from builtins import issubclass
from bexchange.util import message_aware

logger = logging.getLogger("bexchange.server.backend")

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
        """ Adds the hash to internal list. Will return True if hash added otherwise
        False.
        """
        with self.lock:
            if bdbhash in self._handled:
                return False
            self._handled.insert(0, bdbhash)
            if len(self._handled) > self.limit:
                self._handled.pop()
        return True

class monitor_conf_dir_inotify_handler(pyinotify.ProcessEvent):
    """Helper class to monitor a list of folders containing configuration files. Only will process
    files ending with .json. Both added and removed events will be forwarded.
    """
    FILE_PATTERN=".+.json$"
    MASK=pyinotify.IN_CLOSE_WRITE | pyinotify.IN_MOVED_TO | pyinotify.IN_DELETE | pyinotify.IN_MOVED_FROM
    def __init__(self, folders, fn_file_written, fn_file_removed):
        self._folders = folders
        self._fn_file_written = fn_file_written
        self._fn_file_removed = fn_file_removed
        self._wm = pyinotify.WatchManager()
        self._notifier = pyinotify.Notifier(self._wm, self)

    def run(self):
        """The runner for the thread. Starts the inotify notifier loop
        """
        try:
            self._notifier.loop()
        finally:
            logger.error("Leaving loop")

    def match_file(self, filename):
        """Matches the file so that it is following the wanted pattern. Typically *.json.
        :param filename: the filename that should be verified.
        """
        bname = os.path.basename(filename)
        return re.match(self.FILE_PATTERN, bname) != None

    def process_IN_CLOSE_WRITE(self, event):
        """Will be called by the inotify notifier when file event occurs.
        :param event: The file event
        """
        logger.debug("IN_CLOSE_WRITE: %s"%event.pathname)
        try:
            if not self.match_file(event.pathname):
                return
            if self._fn_file_written:
                self._fn_file_written(event.pathname)
        except:
            logger.exception("Failure in IN_CLOSE_WRITE")

    def process_IN_MOVED_TO(self, event):
        """Will be called by the inotify notifier when file event occurs.
        :param event: The file event
        """
        logger.debug("IN_MOVED_TO: %s"%event.pathname)
        try:
            if not self.match_file(event.pathname):
                return
            if self._fn_file_written:
                self._fn_file_written(event.pathname)
        except:
            logger.exception("Failure in IN_MOVED_TO")

    def process_IN_MOVED_FROM(self, event):
        """Will be called by the inotify notifier when file event occurs.
        :param event: The file event
        """
        logger.debug("IN_MOVED_FROM: %s"%event.pathname)
        try:
            if not self.match_file(event.pathname):
                return
            if self._fn_file_removed:
                self._fn_file_removed(event.pathname)
        except:
            logger.exception("Failure in IN_MOVED_FROM")

    def process_IN_DELETE(self, event):
        """Will be called by the inotify notifier when file event occurs.
        :param event: The file event
        """
        logger.debug("IN_DELETE: %s"%event.pathname)
        try:
            if not self.match_file(event.pathname):
                return
            if self._fn_file_removed:
                self._fn_file_removed(event.pathname)
        except:
            logger.exception("Failure in IN_DELETE")

    def start(self):
        """Starts the configuration file monitor
        """
        for folder in self._folders:
            logger.info("monitor_conf_dir_inotify_handler watching '%s'"%(folder))
            self._wm.add_watch(folder, self.MASK)

        self._thread = Thread(target=self.run)
        self._thread.daemon = True
        self._thread.start()

class config_handler(object):
    """Helper class that is registered for all configuration files so that it is possible
    to handle runtime changes.
    """
    def __init__(self, removed, modified, o):
        self._removed = removed
        self._modified = modified
        self._object = o
    
    def removed(self, fname):
        self._removed(fname, self._object)

    def modified(self, fname):
        self._modified(fname, self._object)


class SimpleBackend(backend.Backend):
    """A backend taking care of the exchange

    :param engine_or_url: an SqlAlchemy engine or a database url
    :param storage: a `~.storage.FileStorage` instance to use.
    """
    def __init__(self, confdirs, nodename, authmgr, db_uri, source_db_uri, odim_source_file, tmpfolder=None):
        """Constructor
        :param confdirs: a list of directories where the configuration (.json) files can be found
        :param nodename: name of this node
        :param authmgr: the authorization manager for registering keys
        :param db_uri: general database uri for miscellaneous purposes
        :param source_db_uri: The uri to the source db
        :param odim_source_file: the file containing odim sources for identification of incomming files
        :param tmpfolder: The temporary folder to use if specified
        """
        self.confdirs = confdirs
        self.nodename = nodename
        self.tmpfolder = tmpfolder
        self.authmgr = authmgr

        self.handled_files = HandledFiles()
        
        self._hasher = oh5.MetadataHasher()
        
        self.subscriptions = []
        self.publications = []
        self.storage_manager = storages.storage_manager()
        self.processor_manager = processors.processor_manager()
        self.odim_source_file = odim_source_file
        self.sqldatabase = sqldatabase.SqlAlchemyDatabase(db_uri)
        self.source_manager = sqlbackend.SqlAlchemySourceManager(source_db_uri)
        self.source_manager.add_sources(self.read_bdb_sources(self.odim_source_file))
        self.filter_manager = filters.filter_manager()
        self.runner_manager = runners.runner_manager()
        self.statistics_manager = statistics_manager(self.sqldatabase)

        self.statistics_incomming = False
        self.statistics_duplicates = False
        self.statistics_add_entries = False
        self.statistics_file_handling = False

        self.max_content_length = None

        self._starttime = datetime.datetime.now()

        self._current_configuration_files = {}

        self.initialize_configuration(self.confdirs)

        logger.info("Starting configuration file monitoring")

        self.conf_monitor = monitor_conf_dir_inotify_handler(self.confdirs, self.conf_file_written, self.conf_file_removed)

        self.conf_monitor.start()

        logger.info("System initialized")

    def conf_file_written(self, filename):
        logger.info("File written: %s"%filename)
        if filename in self._current_configuration_files:
            self._current_configuration_files[filename].modified(filename)
        else:
            self.add_configuration_file(filename, True)

    def conf_file_removed(self, filename):
        logger.info("Filed removed: %s"%filename)
        if filename in self._current_configuration_files:
            self._current_configuration_files[filename].removed(filename)
        else:
            logger.warn(f"File {filename} not registered in monitored directory but still triggering event.. !?")

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

    def get_tmp_folder(self):
        """Returns the global temporary folder name if defined
        :return the temporary folder name
        """
        return self.tmpfolder

    def get_statistics_manager(self):
        """
        :returns the statistics manager
        """
        return self.statistics_manager

    def initialize_configuration(self, confdirs):
        """Initializes the configuration from each dir
        :param confdirs: a list of directories where the configuration (.json) files can be found
        """
        for d in confdirs:
            logger.info("Processing directory: %s" % d)
            self.process_conf_dir(d.strip())

        logger.info("Starting runners")
        self.runner_manager.start()

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
            self.add_configuration_file(f)

    def add_configuration_file(self, f, runtime=False):
        """Adds the configuration from a configuration file to the system.
        :param f: The filename containing the configuration in json format
        :param runtime: If the configuration is added at startup (False) or during operational run (True)
        """
        logger.info("Processing configuration file: %s"%f)
        with open(f,"r") as fp:
            data = json.load(fp)
            if "publication" in data:
                p = publisher_manager.from_conf(data["publication"], self)
                if p:
                    logger.info("Adding publication from configuration file: %s"%(f))
                    self.publications.append(p)
                    self._current_configuration_files[f] = config_handler(self.publication_removed, self.publication_modified, p)

            elif "subscription" in data:
                subs = subscription_manager.from_conf(data["subscription"], self)
                if subs:
                    logger.info("Adding subscription from configuration file: %s"%(f))
                    self.subscriptions.append(subs)
                    self._current_configuration_files[f] = config_handler(self.subscription_removed, self.subscription_modified, subs)

            elif "storage" in data:
                s = self.storage_manager.from_conf(data["storage"], self)
                logger.info("Adding storage from configuration file %s"%(f))
                self.storage_manager.add_storage(s)

                self._current_configuration_files[f] = config_handler(self.storage_removed, self.storage_modified, s)

            elif "runner" in data:
                runner = self.runner_manager.from_conf(data["runner"], self)
                if runner:
                    logger.info("Adding runner from configuration file %s"%(f))
                    self.runner_manager.add_runner(runner)
                    self._current_configuration_files[f] = config_handler(self.runner_removed, self.runner_modified, runner)
                    if runtime:
                        runner.start()
                        logger.info(f"Runner started")

            elif "processor" in data:
                p = processors.processor_manager.from_conf(data["processor"], self)
                if p:
                    logger.debug("Adding processor from configuration file %s"%(f))
                    self.processor_manager.add_processor(p)
                    self._current_configuration_files[f] = config_handler(self.processor_removed, self.processor_modified, p)

            else:
                logger.info("Could not identify content of configuration file %s"%f)

    def processor_modified(self, fname, o):
        """Called when a processor configuration file is modified.,
        :param fname: the filename affected
        :param o: the actual processor
        """
        self.processor_removed(fname, o)

        self.add_configuration_file(fname, True)

    def processor_removed(self, fname, o):
        """Called when removing a processor during runtime operation
        :param fname: the filename affected
        :param o: the actual processor
        """
        if fname in self._current_configuration_files:
            del self._current_configuration_files[fname]

        self.processor_manager.remove_processor(o.name())

        logger.info("Processor removed: %s"%fname)

    def storage_modified(self, fname, o):
        """Called when a storage configuration file is modified.,
        :param fname: the filename affected
        :param o: the actual storage
        """
        self.storage_removed(fname, o)

        self.add_configuration_file(fname, True)

    def storage_removed(self, fname, o):
        """Called when removing a storage during runtime operation
        :param fname: the filename affected
        :param o: the actual storage
        """
        if fname in self._current_configuration_files:
            del self._current_configuration_files[fname]

        self.storage_manager.remove_storage(o.name())

        logger.info("Storage removed: %s"%fname)

    def subscription_modified(self, fname, o):
        """Called when a subscription configuration file is modified.,
        :param fname: the filename affected
        :param o: the actual subscription
        """
        self.subscription_removed(fname, o)

        self.add_configuration_file(fname, True)

    def subscription_removed(self, fname, o):
        """Called when removing a subscription during runtime operation
        :param fname: the filename affected
        :param o: the actual subscription
        """
        if fname in self._current_configuration_files:
            del self._current_configuration_files[fname]

        self.subscriptions.remove(o)

        logger.info("Subscription removed: %s"%fname)

    def publication_modified(self, fname, o):
        """Called when a publication configuration file is modified.,
        :param fname: the filename affected
        :param o: the actual publication
        """
        self.publication_removed(fname, o)
        self.add_configuration_file(fname, True)


    def publication_removed(self, fname, o):
        """Called when removing a publication during runtime operation
        :param fname: the filename affected
        :param o: the actual publication
        """
        if fname in self._current_configuration_files:
            del self._current_configuration_files[fname]

        if o in self.publications:
            try:
                o.stop()
            except:
                logger.exception("Failed to stop publication")
            self.publications.remove(o)

        logger.info("Publication removed: %s"%fname)

    def publication_modified(self, fname, o):
        """Called when a publication configuration file is modified.,
        :param fname: the filename affected
        :param o: the actual publication
        """
        self.publication_removed(fname, o)
        self.add_configuration_file(fname, True)

    def runner_removed(self, fname, o):
        """Called when removing a runner during runtime operation
        :param fname: the filename affected
        :param o: the actual runner
        """
        if fname in self._current_configuration_files:
            del self._current_configuration_files[fname]
        self.runner_manager.remove(o)
        logger.info("Runner removed: %s"%fname)

    def runner_modified(self, fname, o):
        """Called when a runner configuration file is modified.,
        :param fname: the filename affected
        :param o: the actual runner
        """
        self.runner_removed(fname, o)
        self.add_configuration_file(fname, True)

    @classmethod
    def from_conf(cls, conf):
        """create an instance from configuration
        parameters are looked up under *'baltrad.exchange.server'*.
        """
        nodename = conf.get("baltrad.exchange.node.name")

        tmpfolder = conf.get("baltrad.exchange.tmp.folder", None)
        
        fconf = conf.filter("baltrad.exchange.server.")

        authmgr = auth.auth_manager.from_conf(conf)
        
        configdirs = fconf.get_list("config.dirs", default="/etc/baltrad/exchange/config", sep=",")

        source_db_uri = fconf.get("source_db_uri", default="sqlite:///var/cache/baltrad/exchange/source.db")

        db_uri = fconf.get("db_uri", default="sqlite:///var/cache/baltrad/exchange/baltrad-exchange.db")

        stat_incomming = fconf.get("statistics.incomming", False)
        stat_duplicates = fconf.get("statistics.duplicates", False)
        stat_add_entries = fconf.get("statistics.add_individual_entry", False)
        stat_file_handling = fconf.get("statistics.file_handling_time", False)

        pluginconf = fconf.filter("plugin.directory.")
        ctr = 1
        plugindir = pluginconf.get("%d"%ctr, "").strip()
        while plugindir:
            sys.path.insert(0, plugindir)
            ctr = ctr + 1
            plugindir = pluginconf.get("%d"%ctr, "").strip()

        odim_source_file = fconf.get("odim_source")
        backend = SimpleBackend(
            configdirs,
            nodename,
            authmgr,
            db_uri,
            source_db_uri,
            odim_source_file,
            tmpfolder = tmpfolder
          )

        backend.max_content_length = conf.get_int("baltrad.exchange.max_content_length", 33554432)

        backend.statistics_incomming = stat_incomming
        backend.statistics_duplicates = stat_duplicates
        backend.statistics_add_entries = stat_add_entries
        backend.statistics_file_handling = stat_file_handling

        return backend

    def store_file(self, path, nid):
        """handles an incomming file and determines if it should be managed by the subscriptions or not.
        :param path: the full path to the file to be handled
        :param nodename: the name/id of the node that the file comes from
        :returns the metadata from the file
        """
        startTime = time.time()

        meta = self.metadata_from_file(path)

        if self.max_content_length is not None and meta.bdb_file_size > self.max_content_length:
            # We won't do anything about the file and will not indicate that anything has gone wrong. We just return the metadata without any more action
            logger.info("Received a file that is too large (%d) from %s, ID:'%s'" % (meta.bdb_file_size, nid, util.create_fileid_from_meta(meta)))
            return meta

        metadataTime = time.time()

        logger.info("store_file: Received file from %s: ID:'%s'" % (nid, util.create_fileid_from_meta(meta)))
        
        if self.statistics_incomming:
            self.get_statistics_manager().increment("server-incomming", nid, meta, self.statistics_add_entries, optime=int((metadataTime - startTime)*1000), optime_info="metadata")

        already_handled = not self.handled_files.add(meta.bdb_metadata_hash)
        if already_handled:
            logger.info("store_file: File recently handled: %s, %s" % (nid, util.create_fileid_from_meta(meta)))
            if self.statistics_duplicates:
                self.get_statistics_manager().increment("server-duplicates", nid, meta, self.statistics_add_entries)

            do_raiseduplicateexception=True
            for subscription in self.subscriptions:
                if subscription.allow_duplicates():
                    do_raiseduplicateexception=False

            if do_raiseduplicateexception:
                from bexchange.net.exceptions import DuplicateException
                raise DuplicateException("Received duplicate ID:'%s'" % (util.create_fileid_from_meta(meta)))

        for subscription in self.subscriptions: # Should only be passive subscriptions here. Active subscriptions should be handled in separate threads.
            if already_handled and not subscription.allow_duplicates():
                continue
            
            if len(subscription.allowed_ids()) > 0 and nid not in subscription.allowed_ids():
                continue
            
            if subscription.filter_matching(meta):
                logger.debug("store_file: filter matching for subscription with id: %s, ID:'%s'"%(subscription.id(), util.create_fileid_from_meta(meta)))
                for storage in subscription.storages():
                    self.storage_manager.store(storage, path, meta)

                for statplugin in subscription.get_statistics_plugins():
                    statplugin.increment(nid, meta)

                self.publish(subscription.id(), path, meta)
                    
                self.processor_manager.process(path, meta)
        
        finishedTime = time.time()

        logger.info("store_file: Total processing time of file from %s, ID:'%s', %d ms" % (nid, util.create_fileid_from_meta(meta), int((finishedTime - startTime)*1000)))

        if self.statistics_file_handling:
            self.get_statistics_manager().increment("server-filehandling", nid, meta, True, False, optime=int((finishedTime - startTime)*1000), optime_info="total")

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

    def publish(self, sid, path, meta):
        """publishes the file on each interested publisher
        :param sid: The subscription id if any
        :param path: full path to the file to be published
        :param meta: meta of file to be published
        """
        for publication in self.publications:
            matcher = metadata_matcher.metadata_matcher()
            origin = publication.origin()
            if len(origin) == 0 or (len(publication.origin()) > 0 and sid in publication.origin()):
                if publication.active() and matcher.match(meta, publication.filter().to_xpr()):
                    logger.debug("publish: publishing file using: %s %s"%(publication.name(), publication))
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
        return metadata_helper.metadata_from_file(self.source_manager, self._hasher, path)
            
    def get_server_uptime(self):
        """
        :return: the server uptime as a tuple of (days, hours, minutes, seconds)
        """
        td = (datetime.datetime.now() - self._starttime)
        hours = td.seconds // 3600
        minutes = (td.seconds % 3600) // 60
        seconds = td.seconds % 60
        return (td.days, hours, minutes, seconds)


    def get_server_nodename(self):
        """
        :return: the nodename of this server
        """
        return self.nodename

    def get_server_publickey(self):
        """
        :return: the public crypto key in PEM encoding that can be used by recipient to verify messages with
        """
        provider = self.authmgr.get_provider("crypto")
        if provider:
            return provider.getPublicKey(self.nodename).PEM()
