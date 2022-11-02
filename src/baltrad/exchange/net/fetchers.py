from abc import ABC, abstractmethod
import logging
import importlib
import uuid
import urllib.parse as urlparse
import re
import fnmatch
from tempfile import NamedTemporaryFile

from baltrad.exchange.net.sftpclient import sftpclient

logger = logging.getLogger("baltrad.exchange.net.fetchers")

class fetcher(object):
    """Base fetcher. All classes implementing this should provide ability to fetch files in some way. 
    """
    def __init__(self, backend, aid):
        """Constructor
        :param backend: The server backend
        :param aid: An id identifying this fetcher
        """
        super(fetcher, self).__init__()
        self._backend = backend
        self._id = aid
        
    def id(self):
        """Returns this fetcher id
        """
        return self._id

    def backend(self):
        """Returns the server backend
        """
        return self._backend

    @abstractmethod
    def fetch(self):
        """Fetches some files
        """
        raise NotImplementedError("Not implemented")

class baseuri_fetcher(fetcher):
    """Base class for fetching data using basic file transmission protocols like sftp, ftp, ...
    """
    def __init__(self, backend, aid, arguments):
        """Constructor
        :param backend: The backend
        :param aid: Id for this fetcher
        :param arguments: Dictionary containg at least:
         {
           "uri":"....",
           "create_missing_directory":true
         }
         This is a base class so the uri is parsed and appropriate members are set. There is no support for any sort of 
         routing appropriate scheme to correct fetcher.
        """
        super(baseuri_fetcher, self).__init__(backend, aid)
        self._arguments = arguments
        self._uri = None
        self._hostname = None
        self._port = 22
        self._username = None
        self._password = None
        
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
            self._path = uri.path

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

    def path(self):
        return self._path

class sftp_fetcher(baseuri_fetcher):
    """Fetcher files using sftp
    """
    def __init__(self, backend, aid, arguments):
        """Constructor
        :param backend: The backend
        :param aid: Id for this fetcher
        :param arguments: Dictionary containg at least:
         {
           "uri":"....",
           "create_missing_directory":true
         }
        """
        super(sftp_fetcher, self).__init__(backend, aid, arguments)
        self._pattern = None
        self._fnpattern = None
        self._pattern_matcher = None
        
        if "pattern" in arguments and arguments["pattern"]:
            self._pattern = arguments["pattern"]
        if "fnpattern" in arguments and arguments["fnpattern"]:
            self._fnpattern = arguments["fnpattern"]
            
        if not self._pattern and not self._fnpattern:
            raise Exception("Missing 'pattern' and/or 'fnpattern' in fetcher configuration")
        if self._pattern:
            self._pattern_matcher = re.compile(self._pattern)
        
        
    def fetch(self):
        """Publishes the file using sftp.
        :param file: path to file that should be published
        :param meta: the meta object for all metadata of file
        """
        with sftpclient(self.hostname(), port=self.port(), username=self.username(), password=self.password()) as c:
            files = c.listdir(self.path())
            for f in files:
                if self._fnpattern and not fnmatch.fnmatch(f, self._fnpattern):
                    continue
                if self._pattern_matcher and not self._pattern_matcher.match(f):
                    continue
                
                fullname = "%s/%s"%(self.path(), f)
                if not c.isfile(fullname):
                    continue
                kwargs={}
                #kwargs["dir"] = "" when specifying a target dir where all temp files should be placed
                with NamedTemporaryFile(**kwargs) as tfo:
                    c.getfo(fullname, tfo)
                    self.backend().store_file(fullname, self.id())
        
class fetcher_manager:
    def __init__(self):
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
           
        fetcherargs = {}
        if "arguments" in arguments:
            fetcherargs = arguments["arguments"]
        if clz.find(".") > 0:
            logger.info("Creating fetcher '%s'"%clz)
            lastdot = clz.rfind(".")
            module = importlib.import_module(clz[:lastdot])
            classname = clz[lastdot+1:]

            return getattr(module, classname)(backend, aid, fetcherargs)
        else:
            raise Exception("Must specify class as module.class")