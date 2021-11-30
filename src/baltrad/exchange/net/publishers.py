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

from baltrad.exchange.client import rest
from threading import Thread
from queue import Queue, Full
from keyczar import keyczar 
import http.client as httplib
import pysftp
import ftplib
import urllib.parse as urlparse
import logging
import datetime
import base64
import importlib
from baltrad.exchange.matching import filters
from baltrad.exchange.matching.filters import filter_manager
from baltrad.exchange.naming.namer import metadata_namer
from tempfile import NamedTemporaryFile
import shutil
from baltrad.exchange.decorators.decorator import decorator_manager

logger = logging.getLogger("baltrad.exchange.server.backend")

##
# Base class used by all publishers
#
class publisher(object):
    """Base class used by all publishers
    """
    def __init__(self, backend, name, active, ifilter, connections, decorators):
        """constructor

        :param backend: The backend implementation
        :param name: The name identifying this publication
        :param active: If this publication is active or not
        :param ifilter: The baltrad.exchange.matching.filters.filter
        :param connections: The connection(s) to use.
        :param decorators: A list of decorators that will modify file before publishing it.
        """
        self._backend = backend
        self._name = name
        self._active = active
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
    def __init__(self, backend, name, active, ifilter, connections, decorators, extra_arguments):
        """constructor

        :param backend: The backend implementation
        :param name: The name identifying this publication
        :param active: If this publication is active or not
        :param ifilter: The baltrad.exchange.matching.filters.filter
        :param connections: The connection(s) to use.
        :param decorators: A list of decorators that will modify file before publishing it.
        :param extra_arguments: A dictionary containing attributes. 
                               "threads" is used to describe how many threads that should be used
                               "queue_size" describes how big the queue can be before publications are discarded.
        """

        super(standard_publisher, self).__init__(backend, name, active, ifilter, connections, decorators)
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

    def publish(self, file, meta):
        tmpfile = NamedTemporaryFile()
        with open(file, "rb") as fp:
            shutil.copyfileobj(fp, tmpfile)
        tmpfile.flush()
        
        logger.info("Decorating file with %d decorators before adding it on queue"%len(self._decorators))
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
        for c in self._connections:
            c.publish(tmpfile.name, meta)
        tmpfile.close()
        
    def consumer(self):
        while True:
            tmpfile, meta = self._queue.get()
            try:
                self.do_publish(tmpfile, meta)
            except:
                logger.exception("Failed to publish file %s"%(tmpfile.name))
            finally:
                self._queue.task_done()

    def start(self):
        for i in range(self._nrthreads):
            t = Thread(target=self.consumer)
            t.daemon = True
            self._threads.append(t)
            t.start() 

    def stop(self):
        for t in self._threads:
            t.join()


class publisher_connection(object):
    def __init__(self, backend):
        self._backend = backend
    
    def publish(self, path, meta):
        pass
    
    def get_backend(self):
        return self._backend
    
class file_copy(publisher_connection):
    """Publishes a file to the file system. Either by using specific rule or using a file storage
    """
    def __init__(self, backend, arguments):
        """Constructor
        :param storage: The storage
        """
        super(file_copy, self).__init__(backend)
        self._storages = []
        if "file_storage" in arguments:
            self._storages = arguments["file_storage"]
    
    def publish(self, file, meta):
        sm = self.get_backend().get_storage_manager()
        for s in self._storages:
            if sm.has_storage(s):
                storage = sm.get_storage(s)
                storage.store(file, meta)

class adapter(object):
    def __init__(self, host, metanamer, create_missing_directories=True, failover=False):
        super(adapter, self).__init__()
        self._host = host
        self._namer = metanamer
        self._create_missing_directories = create_missing_directories
        self._failover = failover

    def hostname(self):
        return self._host

    def name(self, metadata):
        return self._namer.name(metadata)
    
    def create_missing_directories(self):
        return self._create_missing_directories
    
    def isfailover(self):
        return self._failover
    
    def isbackup(self):
        return not self.isfailover()

    def publish(self, path, meta):
        raise Exception("Not implemented")

class sftp_adapter(adapter):
    def __init__(self, host, port, user, password, key, metanamer, create_missing_directories=True, failover=False):
        super(sftp_adapter, self).__init__(host, metanamer, create_missing_directories, failover)
        self._port = port
        self._user = user
        self._password = password
        self._key= key
    
    def port(self):
        return self._port
    
    def user(self):
        return self._user
    
    def password(self):
        return self._password

    def publish(self, path, meta):
        publishedname = self.name(meta)
        logger.debug("sftp_adapter: connecting to: host=%s, port=%d, user=%s"%(self.hostname(), self.port(), self.user()))
        with pysftp.Connection(self.hostname(), port=self.port(), username=self.user(), password=self.password()) as c:
            bdir = os.path.dirname(publishedname)
            fname = os.path.basename(publishedname)
            logger.info("Connected to %s"%self.hostname())
            if self.create_missing_directories():
                c.makedirs(bdir)
            c.chdir(bdir)
            logger.info("Uploading %s as %s to %s"%(path, fname, self.hostname()))
            c.put(path, fname)

class ftp_adapter(adapter):
    def __init__(self, host, port, user, password, metanamer, create_missing_directories=True, failover=False):
        super(ftp_adapter, self).__init__(host, metanamer, create_missing_directories, failover)
        self._port = port
        self._user = user
        self._password = password
    
    def port(self):
        return self._port
    
    def user(self):
        return self._user
    
    def password(self):
        return self._password

    def publish(self, path, meta):
        publishedname = self.name(meta)
        print("ftp_adapter: connecting to: host=%s, port=%d, user=%s"%(self.hostname(), self.port(), self.user()))
        bdir = os.path.dirname(publishedname)
        fname = os.path.basename(publishedname)
        print("bdir=%s, fname=%s"%(bdir, fname))
        ftp = self.connect()
        if bdir != "/":
            try:
                logger.info("CWD: %s"%bdir)
                ftp.cwd(bdir)
            except ftplib.Error as e :
                if self.create_missing_directories():
                    ftp.mkd(bdir)
                    ftp.cwd(bdir)
                else:
                    raise e
        try:
            ftp.storbinary("STOR %s"%fname, open(path, "rb"))
            logger.info("Published %s to %s"%(fname, self.hostname()))
        finally:
            ftp.quit()
        
    ##
    # Connects to remote server
    def connect(self):
        ftp = ftplib.FTP(self.hostname())
        ftp.login(self._user, self._password)
        return ftp
        
class uri_connection(publisher_connection):
    """Publishes a file over sftp to a remote system. Can both specify primary and secondary connection and if secondary should be used
    as fail-over or as a mirror.
    """
    def __init__(self, backend, arguments):
        super(uri_connection, self).__init__(backend)
        self._primary = None
        self._secondary = None
        if "primary" in arguments:
            self._primary = self.create_connection_adapter(arguments["primary"])
        if "secondary" in arguments and arguments["secondary"]:
            self._secondary = self.create_connection_adapter(arguments["secondary"])

    def create_connection_adapter(self, arguments):
        scheme = "sftp"
        host = None
        port = 22
        user = None
        password = None
        key = None
        namer = None
        failover = False
        create_missing_directories = True
        if "failover" in arguments:
            failover = arguments["failover"]
        if "create_missing_directories" in arguments:
            create_missing_directories = arguments["create_missing_directories"]

        if "uri" in arguments and arguments["uri"]:
            uri = urlparse.urlparse(arguments["uri"])
            scheme = uri.scheme
            host = uri.hostname
            if uri.port:
                port = uri.port
            if uri.username:
                user = uri.username
            if uri.password:
                password = uri.password
            namer = metadata_namer(uri.path)
            if scheme == "sftp":
                return sftp_adapter(host, port, user, password, key, namer, create_missing_directories, failover)
            elif scheme == "ftp":
                return ftp_adapter(host, port, user, password, namer, create_missing_directories, failover)

    def publish(self, path, meta):
        primary_failed=False
        try:
            self._primary.publish(path, meta)
        except:
            logger.exception("Failed to upload %s to %s"%(self._primary.name(meta), self._primary.hostname()))
            primary_failed=True
        
        if self._secondary and (primary_failed or self._secondary.isbackup()):
            try:
                self._secondary.publish(path, meta)
            except:
                logger.exception("Failed to upload %s to %s"%(self._secondary.name(meta), self._secondary.hostname()))

class dex_connection(publisher_connection):
    def __init__(self, backend, arguments):
        """Constructor
        :param storage: The storage
        """
        super(dex_connection, self).__init__(backend)
        self._address = None
        self._nodename = None
        self._privatekey = None
        if "crypto" not in arguments:
            raise RuntimeError("Must provide crypto object when initializing a dex connection")
        if "address" not in arguments:
            raise RuntimeError("Must provide address when initializing a dex connection")
        
        self._address = arguments["address"]
        
        cr = arguments["crypto"]
        if "libname" in cr and cr["libname"] != "keyczar":
            raise RuntimeError("Only valid crypto type for dex protocol is keyczar")
        
        self._privatekey = cr["privatekey"]
        
        if not os.path.exists(self._privatekey):
            raise RuntimeError("Keyczar private key doesn't exist or is not readable: %s"%self._privatekey)
        self._nodename = cr["nodename"]
        
        self._signer = keyczar.Signer.Read(self._privatekey)
        
    def _generate_headers(self, uri):
        datestr = datetime.datetime.now().strftime("%a, %e %B %Y %H:%M:%S")
        contentMD5 = base64.b64encode(uri.encode("utf-8"))
        message = (b"POST" + b'\n' + uri.encode("utf-8") + b'\n' + b"application/x-hdf5" + b'\n' + contentMD5 + b'\n' + datestr.encode("utf-8"))
        signature = self._signer.Sign(message)
        headers = {"Node-Name": self._nodename, 
                   "Content-Type": "application/x-hdf5",
                   "Content-MD5": contentMD5, 
                   "Date": datestr, 
                   "Authorization": self._nodename + ':' + signature}
        return headers
  
    def _split_uri(self, uri):
        urlparts = urlparse.urlsplit(uri)
        host = urlparts[1]
        query = urlparts[2]    
        return (host, query)
  
    def _post(self, host, query, data, headers):
        conn = httplib.HTTPConnection(host)
        try:
            conn.request("POST", query, data, headers)
            response = conn.getresponse()
        finally:
            conn.close();
      
        return response.status, response.reason, response.read()
  
    def publish(self, path, meta):
        uri = "%s/BaltradDex/post_file.htm"%self._address
        (host, query) = self._split_uri(uri)
        headers = self._generate_headers(uri)
 
        fp = open(path, 'rb')
    
        try:
            return self._post(host, query, fp, headers)
        finally:
            fp.close()    

class rest_connection(publisher_connection):
    def __init__(self, backend, arguments):
        """Constructor
        """
        super(rest_connection, self).__init__(backend)
        self._address = None
        self._nodename = None
        self._privatekey = None
        self._version = "1.0"

        if "crypto" not in arguments:
            raise RuntimeError("Must provide crypto object when initializing a rest connection")
        
        if "address" not in arguments:
            raise RuntimeError("Must provide address when initializing a rest connection")

        cr = arguments["crypto"]
        if "libname" in cr and cr["libname"] != "keyczar":
            raise RuntimeError("Only valid crypto type for dex protocol is keyczar")
        
        self._privatekey = cr["privatekey"]
        if not os.path.exists(self._privatekey):
            raise RuntimeError("Keyczar private key doesn't exist or is not readable: %s"%self._privatekey)

        self._nodename = cr["nodename"]
        self._address = arguments["address"]
        
        if "version" in arguments:
            self._version = arguments["version"]
                
        self._signer = keyczar.Signer.Read(self._privatekey)
            
    def publish(self, path, meta):
        auth = rest.KeyczarAuth(self._privatekey, self._nodename)
        server = rest.RestfulServer(self._address, auth)
        with open(path, "rb") as data:
            entry = server.store(data)

class publisher_manager:
    def __init__(self):
        pass

    @classmethod
    def create(self, clz, backend, arguments):
        """Creates an instance of clz with specified arguments
        :param clz: class name specified as <module>.<classname>
        :param arguments: a list of arguments that should be used to initialize the class       
        """
        if clz.find(".") > 0:
            logger.info("Creating publisher connection '%s'"%clz)
            lastdot = clz.rfind(".")
            module = importlib.import_module(clz[:lastdot])
            classname = clz[lastdot+1:]
            print("%s"%str(arguments))
            return getattr(module, classname)(backend, arguments)
        else:
            raise Exception("Must specify class as module.class")

    @classmethod
    def create_publisher(self, name, clz, backend, active, filter, connections, decorators, extra_arguments):
        """Creates an instance of clz with specified arguments
        :param clz: class name specified as <module>.<classname>
        :param arguments: a list of arguments that should be used to initialize the class       
        """
        if clz.find(".") > 0:
            logger.info("Creating publisher '%s'"%clz)
            lastdot = clz.rfind(".")
            module = importlib.import_module(clz[:lastdot])
            classname = clz[lastdot+1:]
            print("%s"%str(extra_arguments))
            return getattr(module, classname)(backend, name, active, filter, connections, decorators, extra_arguments)
        else:
            raise Exception("Must specify class as module.class")
    
    @classmethod
    def from_conf(self, config, backend):
        filter_manager = filters.filter_manager()
        name = "unknown"
        publisher_clazz = "baltrad.exchange.net.publishers.standard_publisher"
        active = False
        connections = []
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
                connection = self.create(conncfg["class"], backend, args)
                connections.append(connection)

        if "decorators" in config:
            decoratorconf =  config["decorators"]
            for ds in decoratorconf:
                decorator = decorator_manager.create(ds["decorator"], ds["arguments"])
                decorators.append(decorator)

        if "filter" in config:
            ifilter = filter_manager.from_value(config["filter"])
        
        p = self.create_publisher(name, publisher_clazz, backend, active, ifilter, connections, decorators, extra_arguments)
        p.start()
        return p
