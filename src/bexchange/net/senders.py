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

## Provides support for creating different type of senders

## @file
## @author Anders Henja, SMHI
## @date 2021-12-01
from abc import abstractmethod
import logging
import importlib
import urllib.parse as urlparse
import http.client as httplib
import datetime
import base64
import os
import ssl
import stat
import uuid
import paramiko
import ftplib
import shutil
from paramiko import SSHClient
from scp import SCPClient

from bexchange.naming.namer import metadata_namer
from bexchange.client import rest
from bexchange.net.sftpclient import sftpclient

from baltradcrypto import crypto
from baltradcrypto.crypto.keyczarcrypto import keyczar_signer

logger = logging.getLogger("bexchange.net.senders")

class sender(object):
    """Base sender. All classes implementing this should send the specified file path to a recipient over a specific protocol. 
    """
    def __init__(self, backend, aid):
        """Constructor
        :param backend: The server backend
        :param aid: An id identifying this sender
        """
        super(sender, self).__init__()
        self._backend = backend
        self._id = aid
        
    def id(self):
        """Returns this uploader id
        """
        return self._id

    def backend(self):
        """Returns the server backend
        """
        return self._backend

    @abstractmethod
    def send(self, path, meta):
        """Sends path with the metadata meta
        :param path: Path to file to be uploaded
        :param meta: Metadata of the uploaded file
        """
        raise Exception("Not implemented")

class storage_sender(sender):
    """Sends files using a number of storages.
    """
    def __init__(self, backend, aid, arguments):
        """Constructor
        :param backend: The backend
        :param aid: Id for this sender
        :param arguments: Dictionary containg at least:
        {
          "file_storage":[
            "<name of storage", 
            ...
          ]
        }
        """
        super(storage_sender, self).__init__(backend, aid)
        self._storages = []
        if "file_storage" in arguments:
            self._storages = arguments["file_storage"]
    
    def send(self, file, meta):
        """Sends the file on all storages associated with self
        :param file: path to file that should be sent
        :param meta: the meta object for all metadata of file
        """
        sm = self.backend().get_storage_manager()
        for s in self._storages:
            if sm.has_storage(s):
                storage = sm.get_storage(s)
                storage.store(file, meta)    
    

class dex_sender(sender):
    """Legacy DEX communication sending files to old nodes.
    """
    def __init__(self, backend, aid, arguments):
        """Constructor
        :param backend: The backend
        :param aid: Id for this sender
        :param arguments: Dictionary containg at least:
         {
           "address":"http://localhost:8080",
           "crypto":{
             "sign":true,
             "libname":"keyczar",
             "nodename":"anders-nzxt",
             "privatekey":"/opt/baltrad2/etc/bltnode-keys/anders-nzxt.priv"
           }         
         }
        """
        super(dex_sender, self).__init__(backend, aid)
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
        
        self._signer = keyczar_signer.read(self._privatekey)

    def _generate_headers(self, uri):
        """Creates the headers that should be added to the dex message
        :param uri: The uri that should be added
        :return: the headers as a dictonary
        """
        datestr = datetime.datetime.now().strftime("%a, %e %B %Y %H:%M:%S")
        contentMD5 = base64.b64encode(uri.encode("utf-8"))
        message = ("POST" + '\n' + uri + '\n' + "application/x-hdf5" + '\n' + str(contentMD5, "utf-8") + '\n' + datestr)
        signature = self._signer.sign(message)
        headers = {"Node-Name": self._nodename, 
                   "Content-Type": "application/x-hdf5",
                   "Content-MD5": contentMD5, 
                   "Date": datestr, 
                   "Authorization": self._nodename + ':' + signature}
        return headers
  
    def _split_uri(self, uri):
        """Splits an uri to the individual parts.
        :param uri: The uri to be split
        :return: tuple of scheme, host and query
        """
        urlparts = urlparse.urlsplit(uri)
        scheme = urlparts[0]
        host = urlparts[1]
        query = urlparts[2]    
        return (scheme, host, query)
  
    def _post(self, scheme, host, query, data, headers):
        """Posts the message to the recipient.
        :param scheme: The scheme to use, https or http
        :param host: the host that should be connected to (including port)
        :param query: the query data
        :param data: the data to be added to message
        :param headers: the headers to add to message
        :return: a tuple of status, reason and any data
        """
        if scheme == "https":
            conn = httplib.HTTPSConnection(host, context = ssl._create_unverified_context())
        else:
            conn = httplib.HTTPConnection(host)

        try:
            conn.request("POST", query, data, headers)
            response = conn.getresponse()
        except Exception as e:
            raise Exception("Failed to post message to: %s"%self._nodename, e)
        finally:
            conn.close();
      
        return response.status, response.reason, response.read()
  
    def send(self, path, meta):
        """Sends the file to the dex server
        :param file: path to file that should be sent
        :param meta: the meta object for all metadata of file
        """
        uri = "%s/BaltradDex/post_file.htm"%self._address
        (scheme, host, query) = self._split_uri(uri)
        headers = self._generate_headers(uri)
 
        fp = open(path, 'rb')
    
        try:
            return self._post(scheme, host, query, fp.read(), headers)
        finally:
            fp.close()    

class rest_sender(sender):
    """Sends a file to another node that is running bexchange. The rest sender uses the internal crypto library for signing messages
    which currently supports DSA & RSA keys. DSA uses DSS, RSA uses pkcs1_15.
    """
    def __init__(self, backend, aid, arguments):
        """Constructor
        :param backend: The backend
        :param aid: Id for this sender
        :param arguments: Dictionary containg at least:
         {
           "address":"http://localhost:8080",
           "protocol_version":"1.0",
           "crypto":{
             "libname":"exchange-crypto",
             "nodename":"anders-silent",
             "privatekey":"/etc/baltrad/exchange/cryptos/anders-silent.private"
           }         
         }
        """
        super(rest_sender, self).__init__(backend, aid)
        self._address = None
        self._nodename = None
        self._privatekey = None
        self._version = "1.0"
        if "crypto" not in arguments:
            raise RuntimeError("Must provide crypto object when initializing a rest connection")
        
        if "address" not in arguments:
            raise RuntimeError("Must provide address when initializing a rest connection")

        cr = arguments["crypto"]
        if "libname" in cr and cr["libname"] != "crypto":
            raise RuntimeError("Only valid crypto type for protocol is currently the internal crypto")
        
        self._privatekey = cr["privatekey"]
        if not os.path.exists(self._privatekey):
            raise RuntimeError("The private key doesn't exist or is not readable: %s"%self._privatekey)

        self._nodename = cr["nodename"]
        self._address = arguments["address"]
        
        if "version" in arguments:
            self._version = arguments["version"]
        self._signer = crypto.load_key(self._privatekey)
        if not isinstance(self._signer, crypto.private_key):
            raise Exception("Can't use key: %s for signing"%self._privatekey)
            
    def send(self, path, meta):
        """Sends the file to the bexchange server
        :param file: path to file that should be sent
        :param meta: the meta object for all metadata of file
        """        
        auth = rest.CryptoAuth(self._privatekey, self._nodename)
        server = rest.RestfulServer(self._address, auth)
        with open(path, "rb") as data:
            entry = server.store(data)

class baseuri_sender(sender):
    """Base class for basic file transmission protocols like sftp, ftp, ...
    """
    def __init__(self, backend, aid, arguments):
        """Constructor
        :param backend: The backend
        :param aid: Id for this sender
        :param arguments: Dictionary containg at least:
         {
           "uri":"....",
           "create_missing_directory":true
         }
         This is a base class so the uri is parsed and appropriate members are set. There is no support for any sort of 
         routing appropriate scheme to correct sender.
        """
        super(baseuri_sender, self).__init__(backend, aid)
        self._arguments = arguments
        self._uri = None
        self._hostname = None
        self._port = 22
        self._username = None
        self._password = None
        self._namer = None
        self._create_missing_directories = True
        
        if "create_missing_directories" in arguments:
            self._create_missing_directories = arguments["create_missing_directories"]
            
        if "uri" in arguments and arguments["uri"]:
            self._uri = arguments["uri"]
            uri = urlparse.urlparse(self._uri)
            self._hostname = uri.hostname
            if uri.port:
                self._port = uri.port
            if uri.username:
                self._username = uri.username
            if uri.password:
                self._password = uri.password
            self._namer = metadata_namer(uri.path)

    def name(self, meta):
        """Creates a unique name from the metadatanamer created from the uri
        :param meta: Metadata to use when creating the name
        """
        return self._namer.name(meta)

    def create_missing_directories(self):
        """Returns if missing directories should be created or not
        """
        return self._create_missing_directories

    def hostname(self):
        """Returns the hostname extracted from the uri
        """
        return self._hostname

    def port(self):
        """Returns the port number extracted from the uri.
        """
        return self._port
    
    def username(self):
        return self._username
    
    def password(self):
        return self._password


class sftp_sender(baseuri_sender):
    """Sends files over sftp
    """
    def __init__(self, backend, aid, arguments):
        """Constructor
        :param backend: The backend
        :param aid: Id for this sender
        :param arguments: Dictionary containg at least:
         {
           "uri":"....",
           "create_missing_directory":true
         }
        """
        super(sftp_sender, self).__init__(backend, aid, arguments)

    def send(self, path, meta):
        """Sends the file using sftp.
        :param file: path to file that should be sent
        :param meta: the meta object for all metadata of file
        """        
        publishedname = self.name(meta)
        logger.debug("sftp_adapter: connecting to: host=%s, port=%d, user=%s"%(self.hostname(), self.port(), self.username()))
        with sftpclient(self.hostname(), port=self.port(), username=self.username(), password=self.password()) as c:
            bdir = os.path.dirname(publishedname)
            fname = os.path.basename(publishedname)
            logger.info("Connected to %s"%self.hostname())
            if self.create_missing_directories():
                c.makedirs(bdir)
            c.chdir(bdir)
            logger.info("sftp_sender: Uploading %s as %s to %s"%(path, fname, self.hostname()))
            c.put(path, fname)

class scp_sender(baseuri_sender):
    """Publishes files over scp
    """
    def __init__(self, backend, aid, arguments):
        """Constructor
        :param backend: The backend
        :param aid: Id for this sender
        :param arguments: Dictionary containg at least:
         {
           "uri":"....",
           "create_missing_directory":true
         }
        """
        super(scp_sender, self).__init__(backend, aid, arguments)
        
    def send(self, path, meta):
        """Sends the file using scp.
        :param file: path to file that should be sent
        :param meta: the meta object for all metadata of file
        """
        ssh = None
        scp = None
        try:
            ssh = SSHClient()
            ssh.load_system_host_keys()
            ssh.connect(self.hostname(), self.port(), self.username(), self.password());
            scp = SCPClient(ssh.get_transport())
            publishedname = self.name(meta)
            if self.create_missing_directories():
                dirname = os.path.dirname(publishedname)
                ssh.exec_command("test -d %s || mkdir -p %s"%(dirname, dirname))
            logger.info("scp_sender: Uploading %s as %s to %s"%(path, publishedname, self.hostname()))
            scp.put(path, publishedname)
        finally:
            if scp:
                try:
                    scp.close()
                except:
                    pass

class ftp_sender(baseuri_sender):
    """Publishes files over ftp
    """
    def __init__(self, backend, aid, arguments):
        """Constructor
        :param backend: The backend
        :param aid: Id for this sender
        :param arguments: Dictionary containg at least:
         {
           "uri":"....",
           "create_missing_directory":true
         }
        """
        super(ftp_sender, self).__init__(backend, aid, arguments)
        if self._uri:
            uri = urlparse.urlparse(self._uri)
            if not uri.port:
                self._port = 21
        
    def send(self, path, meta):
        """Sends the file using ftp.
        :param file: path to file that should be published
        :param meta: the meta object for all metadata of file
        """        
        publishedname = self.name(meta)
        logger.info("ftp_sender: connecting to: host=%s, port=%d, user=%s"%(self.hostname(), self.port(), self.username()))
        bdir = os.path.dirname(publishedname)
        fname = os.path.basename(publishedname)
        ftp = self.connect()
        if bdir != "/":
            try:
                logger.info("CWD: %s"%bdir)
                ftp.cwd(bdir)
            except ftplib.Error as e :
                if self.create_missing_directories():
                    self.change_and_create_dir(ftp, bdir)
                else:
                    raise e
        try:
            logger.info("ftp_sender: Uploading %s as %s to %s"%(path, fname, self.hostname()))
            ftp.storbinary("STOR %s"%fname, open(path, "rb"))
        finally:
            ftp.quit()

    def does_dir_exist(self, ftp, path):
        """Tests if the specified directory exist using the provided ftp-connection
        :param ftp: the ftp connection
        :param path: the path to test
        :return: True or False
        """
        dirlist = []
        dtolist = os.path.dirname(path)
        dtotest = os.path.basename(path)
        ftp.retrlines("LIST %s"%dtolist, dirlist.append)
        for f in dirlist:
            if f.split()[-1] == dtotest and f.upper().startswith('D'):
                return True
        return False

    def change_and_create_dir(self, ftp, path):
        """Changes directory and creates specified directory.
        :param ftp: The ftp connection
        :param path: The path to create"""
        if not self.does_dir_exist(ftp, path):
            nextpath = os.path.dirname(path)
            createdir = os.path.basename(path)
            if nextpath == "/" or nextpath == "":
                raise Exception("Not even root folder exist")  
            self.change_and_create_dir(ftp, nextpath)
            logger.info("Changing directory to: %s and creating %s"%(nextpath, createdir))
            ftp.cwd(nextpath)
            ftp.mkd(createdir)
            ftp.cwd(createdir)
            logger.info("Current working directory: %s/%s"%(nextpath, createdir))
        else:
            ftp.cwd(path)
        
    ##
    # Connects to remote server
    def connect(self):
        """Connects to the host specified by host  / port.
        :return: the ftp connection
        """
        ftp = ftplib.FTP()
        ftp.connect(self.hostname(), self.port())
        ftp.login(self.username(), self.password())
        return ftp

class copy_sender(sender):
    """Sends files by copying them
    """
    def __init__(self, backend, aid, arguments):
        """Constructor
        :param backend: The backend
        :param aid: Id for this sender
        :param arguments: Dictionary containg at least:
         {
           "path":"....",
           "create_missing_directory":true
         }
        """
        super(copy_sender, self).__init__(backend, aid)
        self._path = arguments["path"]
        self._create_missing_directories = True
        if "create_missing_directories" in arguments:
            self._create_missing_directories = arguments["create_missing_directories"]
        self._namer = metadata_namer(self._path)

    def name(self, meta):
        """Creates the name to use when copying the file from the metadata
        :param meta: The metadata
        :return: the name to use for destination
        """
        return self._namer.name(meta)
    
    def create_missing_directories(self):
        """
        :return: if missing directories should be created or not
        """
        return self._create_missing_directories
    
    def send(self, path, meta):
        """Sends the file using copy.
        :param file: path to file that should be sent
        :param meta: the meta object for all metadata of file
        """        
        publishedname = self.name(meta)
        dirname = os.path.dirname(publishedname)
        filename = os.path.basename(publishedname)
        logger.info("copy_sender: copying %s to %s"%(filename, dirname))
        if not os.path.exists(dirname) and self.create_missing_directories():
            os.makedirs(dirname)
        logger.info("copy_sender: Copying %s to %s"%(path, publishedname))
        shutil.copyfile(path, publishedname)

class sender_manager:
    def __init__(self):
        """Constructor
        """
        pass

    @classmethod
    def from_conf(self, backend, arguments):
        """Creates an instance of clz with specified arguments
        :param arguments: a list of arguments that should be used to initialize the class       
        """
        aid=None
        clz = arguments["class"]
        if "id" in arguments:
            aid = arguments["id"]
        else:
            aid = "%s-%s"%(clz, str(uuid.uuid4())) # If id not specified, then we create an id 
           
        senderargs = {}
        if "arguments" in arguments:
            senderargs = arguments["arguments"]
        if clz.find(".") > 0:
            logger.debug("Creating sender '%s'"%clz)
            lastdot = clz.rfind(".")
            module = importlib.import_module(clz[:lastdot])
            classname = clz[lastdot+1:]

            return getattr(module, classname)(backend, aid, senderargs)
        else:
            raise Exception("Must specify class as module.class")
