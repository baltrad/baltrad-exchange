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

## Different type of publishers

## @file
## @author Anders Henja, SMHI
## @date 2021-08-18
import os

from bexchange.client import rest
from threading import Thread
from queue import Queue, Full
import http.client as httplib
import ftplib
import urllib.parse as urlparse
import logging
import datetime
import base64
import importlib
from bexchange.matching import filters
from bexchange.matching.filters import filter_manager
from bexchange.naming.namer import metadata_namer
from tempfile import NamedTemporaryFile
import shutil
from bexchange.decorators.decorator import decorator_manager
from bexchange.net.connections import connection_manager
from bexchange.statistics.statistics import statistics_manager

logger = logging.getLogger("bexchange.net.publishers")

##
# Base class used by all publishers
#
class publisher(object):
    """Base class used by all publishers
    """
    def __init__(self, backend, name, active, origin, ifilter, connections, decorators):
        """constructor

        :param backend: The backend implementation
        :param name: The name identifying this publication
        :param active: If this publication is active or not
        :param origin: The origin if the publication is tunneled. Can be seen as a subscription_id filter in most cases.
        :param ifilter: The bexchange.matching.filters.filter
        :param connections: The connection(s) to use.
        :param decorators: A list of decorators that will modify file before publishing it.
        """
        self._backend = backend
        self._name = name
        self._active = active
        self._origin = origin
        self._filter = ifilter
        self._connections = connections
        self._decorators = decorators
    
    def publish(self, file, meta):
        """publishes a file

        :param file: The temp file instance
        :param meta: The metadata
        :return: metadata extracted from the file
        """
        raise RuntimeError("Not implemented")
    
    def backend(self):
        """Returns the backend
        :return: the backend
        """
        return self._backend
    
    def name(self):
        """Returns the name
        :return: the name
        """
        return self._name
    
    def active(self):
        """Returns if this publication is active or not
        :return: if this publication is active or not
        """
        return self._active
    
    def origin(self):
        """
        :return the list of origins that should trigger this publication
        """
        return self._origin

    def filter(self):
        """Returns the filter
        :return: the filter
        """
        return self._filter
    
    def connections(self):
        """Returns the connection(s)
        :return: the connection(s)
        """
        return self._connections
    
    def decorators(self):
        """Returns the decorator(s)
        :return: the decorator(s)
        """
        return self._decorators

    def start(self):
        """A publisher should most likely be managing threads and as such a start method is needed
        """
        raise RuntimeError("Not implemented")

    def stop(self):
        """A publisher should most likely be managing threads and as such a stop method is needed joining the threads
        """
        raise RuntimeError("Not implemented")

class standard_publisher(publisher):
    """Standard publisher used for most situations. Provides two arguments. One is threads. The other is queue_size.
    """
    def __init__(self, backend, name, active, origin, ifilter, connections, decorators, extra_arguments):
        """constructor

        :param backend: The backend implementation
        :param name: The name identifying this publication
        :param active: If this publication is active or not
        :param origin: When tunneling for example subscriptions, then specify list of ids
        :param ifilter: The bexchange.matching.filters.filter
        :param connections: The connection(s) to use.
        :param decorators: A list of decorators that will modify file before publishing it.
        :param extra_arguments: A dictionary containing attributes. 
                               "threads" is used to describe how many threads that should be used
                               "queue_size" describes how big the queue can be before publications are discarded.
        """

        super(standard_publisher, self).__init__(backend, name, active, origin, ifilter, connections, decorators)
        nrthreads=1
        queue_size=100
        if "threads" in extra_arguments:
            nrthreads = extra_arguments["threads"]
        if "queue_size" in extra_arguments:
            queue_size = extra_arguments["queue_size"]
            
        self._nrthreads = nrthreads
        self._queue_size = queue_size
        self._threads=[]
        self._queue = Queue(self._queue_size)

        self._statistics_ok_plugin = None
        self._statistics_error_plugin = None

        if "statistics_ok" in extra_arguments:
            self._statistics_ok_plugin = statistics_manager.plugin_from_conf(extra_arguments["statistics_ok"], backend.get_statistics_manager())
        if "statistics_error" in extra_arguments:
            self._statistics_error_plugin = statistics_manager.plugin_from_conf(extra_arguments["statistics_error"], backend.get_statistics_manager())

    def publish(self, file, meta):
        """Passes on a file to the consumer queue that will be consumed and passed on to the connections.
        :param file: Actual file to be duplicated and sent.
        :param meta: The metadata to be verified by the connections
        """
        tmpfile = NamedTemporaryFile()
        with open(file, "rb") as fp:
            shutil.copyfileobj(fp, tmpfile)
        tmpfile.flush()
        
        logger.debug("Decorating file with %d decorators before adding it on queue"%len(self._decorators))
        if len(self._decorators) > 0:
            for d in self._decorators:
                logger.info("Decorator %s"%type(d))
                tmpfile = d.decorate(tmpfile)
            tmpfile.flush()
            meta = self.backend().metadata_from_file(tmpfile.name)
        
        try:
            self._queue.put((tmpfile, meta), False)
        except Full as e:
            logger.exception("Queue for publisher %s is full."%self.name())

    def do_publish(self, tmpfile, meta):
        """Passes a file to all connections
        """
        for c in self._connections:
            c.publish(tmpfile.name, meta)
        tmpfile.close()
        
    def consumer(self):
        """ The consumer called by the individual threads. Will grab one entry from the queue and pass it on to the connections.
        """
        while True:
            tmpfile, meta = self._queue.get()
            try:
                self.do_publish(tmpfile, meta)
                if self._statistics_ok_plugin:
                    self._statistics_ok_plugin.increment("", meta)
            except:
                logger.exception("Failed to publish file %s"%(tmpfile.name))
                if self._statistics_error_plugin:
                    self._statistics_error_plugin.increment("", meta)
            finally:
                self._queue.task_done()

    def start(self):
        """ Starts all consumer threads as daemon threads
        """
        for i in range(self._nrthreads):
            t = Thread(target=self.consumer)
            t.daemon = True
            self._threads.append(t)
            t.start() 

    def stop(self):
        """Joins the threads
        """
        for t in self._threads:
            t.join()

class publisher_manager:
    """The manager used for creating publishers from configuration
    """
    def __init__(self):
        """Constructor
        """
        pass

    @classmethod
    def create_publisher(self, name, clz, backend, active, origin, filter, connections, decorators, extra_arguments):
        """Creates an instance of clz with specified arguments
        :param clz: class name specified as <module>.<classname>
        :param arguments: a list of arguments that should be used to initialize the class       
        """
        if clz.find(".") > 0:
            logger.debug("Creating publisher '%s'"%clz)
            lastdot = clz.rfind(".")
            module = importlib.import_module(clz[:lastdot])
            classname = clz[lastdot+1:]
            return getattr(module, classname)(backend, name, active, origin, filter, connections, decorators, extra_arguments)
        else:
            raise Exception("Must specify class as module.class")
    
    @classmethod
    def from_conf(self, config, backend):
        """Creates the publisher instance from provided configuration.
        :param config: The json config in a dict
        :param backend: The backend the publisher shall have access to
        :return: the created publisher
        """
        filter_manager = filters.filter_manager()
        name = "unknown"
        publisher_clazz = "bexchange.net.publishers.standard_publisher"
        active = False
        connections = []
        subscription_origin = []
        ifilter = None
        decorators = []
        extra_arguments = {}
        
        if "name" in config:
            name = config["name"]
        
        if "class" in config:
            publisher_clazz = config["class"]

        if "extra_arguments" in config:
            extra_arguments = config["extra_arguments"]

        if "active" in config:
            active = config["active"]
        
        if "connection" in config:
            conncfg = config["connection"]
            if "class" in conncfg:
                args = []
                if "arguments" in conncfg:
                    args = conncfg["arguments"]
                connection = connection_manager.from_conf(backend, conncfg["class"], args)
                connections.append(connection)

        if "subscription_origin" in config:
            subscription_origin = config["subscription_origin"]
            if not isinstance(subscription_origin, list):
                subscription_origin = list(subscription_origin)

        if "decorators" in config:
            decoratorconf =  config["decorators"]
            for ds in decoratorconf:
                decorator = decorator_manager.create(ds["decorator"], ds["arguments"])
                decorators.append(decorator)

        if "filter" in config:
            ifilter = filter_manager.from_value(config["filter"])
        
        p = self.create_publisher(name, publisher_clazz, backend, active, subscription_origin, ifilter, connections, decorators, extra_arguments)

        p.start()
        return p
