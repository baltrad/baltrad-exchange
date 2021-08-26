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
from queue import Queue
from keyczar import keyczar 
import http.client as httplib
import urllib.parse as urlparse
import logging
import datetime
import base64
from baltrad.exchange.matching import filters
from baltrad.exchange.matching.filters import filter_manager
from tempfile import NamedTemporaryFile
import shutil

logger = logging.getLogger("baltrad.exchange.server.backend")

##
# Base class used by all publishers
#
class publisher(object):
    """Base class used by all publishers
    """
    def __init__(self, ifilter, active):
        self._filter = ifilter
        self._active = active
    
    def publish(self, file):
        raise RuntimeError("Not implemented")
    
    def filter(self):
        return self._filter
    
    def active(self):
        return self._active

##
# 
class null_publisher(publisher):
    """Does not publish anything"""
    def __init__(self, ifilter, active):
        super(null_publisher, self).__init__(ifilter, active)
    
    def publish(self, file):
        pass

class dex_publisher(publisher):
    """Publishes a file to a DEX node"""
    def __init__(self, ifilter, active, address, nodename, privatekey):
        super(dex_publisher, self).__init__(ifilter, active)
        self.address = address
        self.nodename = nodename
        self.privatekey = privatekey
        self._signer = keyczar.Signer.Read(self.privatekey)
        self.threads=[]
        self.queue = Queue()
    
    def _generate_headers(self, uri):
        datestr = datetime.datetime.now().strftime("%a, %e %B %Y %H:%M:%S")
        contentMD5 = base64.b64encode(uri.encode("utf-8"))
        message = (b"POST" + b'\n' + uri.encode("utf-8") + b'\n' + b"application/x-hdf5" + b'\n' + contentMD5 + b'\n' + datestr.encode("utf-8"))
        signature = self._signer.Sign(message)
        headers = {"Node-Name": self.nodename, 
                   "Content-Type": "application/x-hdf5",
                   "Content-MD5": contentMD5, 
                   "Date": datestr, 
                   "Authorization": self.nodename + ':' + signature}
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
  
    def send_file(self, path):
        uri = "%s/BaltradDex/post_file.htm"%self.address
        (host, query) = self._split_uri(uri)
        headers = self._generate_headers(uri)
 
        fp = open(path.name, 'rb')
    
        try:
            return self._post(host, query, fp, headers)
        finally:
            path.close()
            fp.close()
        
    
    def publish(self, file):
        tmpfile = NamedTemporaryFile()
        with open(file, "rb") as fp:
            shutil.copyfileobj(fp, tmpfile)
        tmpfile.flush()
        self.queue.put(tmpfile)

    def consumer(self):
        while True:
            f = self.queue.get()
            try:
                self.send_file(f)
            except:
                logger.exception("Failed to publish file: %s to %s"%(f, self.address))
            finally:
                self.queue.task_done()
            
    def start(self):
        for i in range(2):
            t = Thread(target=self.consumer)
            t.daemon = True
            self.threads.append(t)
            t.start() 

    def stop(self):
        for t in self.threads:
            t.join()

    @classmethod
    def from_conf(cls, ifilter, active, config):
        if "protocol" not in config or config["protocol"] != "dex":
            raise RuntimeError("Invalid connection config used for dex publisher")
        
        address = config["address"]
        cr = config["crypto"]
        if "libname" in cr and cr["libname"] != "keyczar":
            raise RuntimeError("Only valid crypto type for dex protocol is keyczar")
        privkey = cr["privatekey"]
        if not os.path.exists(privkey):
            raise RuntimeError("Keyczar private key doesn't exist or is not readable: %s"%privkey)
        nodename = cr["nodename"]

        #auth = rest.NoAuth()
        #if "sign" in cr and cr["sign"] == True:
        #    auth = rest.KeyczarAuth(privkey, nodename)

        #server = rest.RestfulServer(server_url, auth)
    
        publisher = dex_publisher(ifilter, active, address, nodename, privkey)
        publisher.start()
        return publisher

class rest_publisher(publisher):
    """Publishes a file using the rest protocol"""
    
    def __init__(self, ifilter):
        super(rest_publisher, self).__init__(ifilter)
    
    def publish(self, file):
        pass

class publisher_manager:
    def __init__(self):
        pass

    @classmethod
    def from_conf(self, config):
        filter_manager = filters.filter_manager()
        active = False
        if "connection" not in config or "filter" not in config:
            raise AttributeError("connection and filter must exist in configuration")
        
        if "active" in config:
            active = config["active"]
        
        if "connection" in config:
            conn = config["connection"]
            if "protocol" in conn:
                protocol = conn["protocol"]
                if protocol == "dex":
                    return dex_publisher.from_conf(filter_manager.from_value(config["filter"]), active, config["connection"])
                elif protocol == "rest":
                    return null_publisher(filter_manager.from_value(config["filter"]), active)
                elif protocol == "null":
                    return null_publisher(filter_manager.from_value(config["filter"]), active)
        raise Exception("Unsupported connection type")
        