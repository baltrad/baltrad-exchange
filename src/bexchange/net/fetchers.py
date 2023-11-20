from abc import abstractmethod
import logging
import importlib
import uuid
import urllib.parse as urlparse
import re
import os
import fnmatch
from tempfile import NamedTemporaryFile, TemporaryDirectory
from paramiko import SSHClient
from scp import SCPClient
import ftplib
import glob

from bexchange.net.sftpclient import sftpclient

logger = logging.getLogger("bexchange.net.fetchers")

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
    def fetch(self, **kwargs):
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

    def uri(self):
        return self._uri

    def hostname(self):
        """Returns the hostname extracted from the uri
        """
        return self._hostname

    def port(self):
        """Returns the port number extracted from the uri.
        """
        return self._port
    
    def set_port(self, portno):
        """ Sets the portnumber
        :param portno: The portnumber to use
        """
        self._port = portno
    
    def username(self):
        """
        :return the user name
        """
        return self._username
    
    def password(self):
        """
        :return the password
        """
        return self._password

    def path(self):
        """
        :return the path
        """
        return self._path

class baseuri_patternmatching_fetcher(baseuri_fetcher):
    """Base class for fetching data using basic file transmission protocols like sftp, ftp, ...
    """
    def __init__(self, backend, aid, arguments):
        """Constructor
        :param backend: The backend
        :param aid: Id for this fetcher
        :param arguments: Dictionary containg at least
         {
           "uri":"...."
         }
         This is a base class so the uri is parsed and appropriate members are set. There is no support for any sort of 
         routing appropriate scheme to correct fetcher.
        """
        super(baseuri_patternmatching_fetcher, self).__init__(backend, aid, arguments)
        self._pattern = None
        self._fnpattern = None
        self._pattern_matcher = None
        
        if "pattern" in arguments and arguments["pattern"]:
            self._pattern = arguments["pattern"]
        if "fnpattern" in arguments and arguments["fnpattern"]:
            self._fnpattern = arguments["fnpattern"]
        if self._pattern:
            self._pattern_matcher = re.compile(self._pattern)

    def fnpattern(self):
        """Returns the fnpattern
        :return: the filename pattern, like \*.h5
        """
        return self._fnpattern
    
    def pattern(self):
        """
        :return the regular expression matching pattern
        """
        return self._pattern
    
    def pattern_matcher(self):
        """
        :return the pattern matcher for the regular expression if there is one
        """
        return self._pattern_matcher

class sftp_fetcher(baseuri_patternmatching_fetcher):
    """Fetcher files using sftp
    """
    def __init__(self, backend, aid, arguments):
        """Constructor
        :param backend: The backend
        :param aid: Id for this fetcher
        :param arguments: Dictionary containg at least:
         {
           "uri":"....",
         }
        """
        super(sftp_fetcher, self).__init__(backend, aid, arguments)
        if not self.fnpattern() and not self.pattern():
            raise Exception("Neither fnpattern or pattern provided") 
        
    def fetch(self, **kwargs):
        """Fetches the file using sftp.
        :param file: path to file that should be published
        :param meta: the meta object for all metadata of file
        """
        logger.debug("Running sftp_fetcher: %s"%self.hostname())
        with sftpclient(self.hostname(), port=self.port(), username=self.username(), password=self.password()) as c:
            files = c.listdir(self.path())
            for f in files:
                if self.fnpattern() and not fnmatch.fnmatch(f, self.fnpattern()):
                    continue
                if self.pattern_matcher() and not self.pattern_matcher().match(f):
                    continue
                
                fullname = "%s/%s"%(self.path(), f)
                if not c.isfile(fullname):
                    continue
                ntfargs={"dir":self.backend().get_tmp_folder()}
                with NamedTemporaryFile(**ntfargs) as tfo:
                    c.getfo(fullname, tfo)
                    self.backend().store_file(fullname, self.id())

class scp_fetcher(baseuri_patternmatching_fetcher):
    """Fetcher file(s) using scp
    """
    def __init__(self, backend, aid, arguments):
        """Constructor
        :param backend: The backend
        :param aid: Id for this fetcher
        :param arguments: Dictionary containg at least:
         {
           "uri":"....",
         }
        """
        super(scp_fetcher, self).__init__(backend, aid, arguments)
        
    def fetch(self, **kwargs):
        """Fetches the file(s) using scp.
        :param file: path to file that should be published
        :param meta: the meta object for all metadata of file
        """
        logger.debug("Running scp_fetcher: %s"%self.hostname())
        ssh = None
        scp = None
        try:
            ssh = SSHClient()
            ssh.load_system_host_keys()
            ssh.connect(self.hostname(), self.port(), self.username(), self.password());
            _, sout, _ = ssh.exec_command("ls -1 %s"%self.path())
            files = str(sout.read(), "utf-8").split("\n")
            scp = SCPClient(ssh.get_transport())
            tdargs={}
            with TemporaryDirectory(**tdargs) as tmpdir:
                for f in files:
                    if f.strip():
                        bname = os.path.basename(f)
                        fullname = os.path.join(tmpdir, bname)
                        scp.get(f.strip(), fullname)
                        self.backend().store_file(fullname, self.id())
        finally:
            if scp:
                try:
                    scp.close()
                except:
                    pass
            if ssh:
                try:
                    ssh.close()
                except:
                    pass

class ftp_fetcher(baseuri_patternmatching_fetcher):
    """Fetcher file(s) using scp
    """
    def __init__(self, backend, aid, arguments):
        """Constructor
        :param backend: The backend
        :param aid: Id for this fetcher
        :param arguments: Dictionary containg at least:
         {
           "uri":"....",
         }
        """
        super(ftp_fetcher, self).__init__(backend, aid, arguments)
        if self.uri():
            uri = urlparse.urlparse(self.uri())
            if not uri.port:
                self.set_port(21)

    def fetch(self, **kwargs):
        """Fetches the file(s) using ftp.
        :param file: path to file that should be published
        :param meta: the meta object for all metadata of file
        """
        logger.debug("Running ftp_fetcher: %s"%self.hostname())
        ftp = self.connect()
        if not ftp:
            raise Exception("Failed to connect to remove ftp server")

        files=[]
        try:
            ftp.cwd(self.path())
            files = ftp.nlst()
            
            for f in files:
                tdargs={"dir":self.backend().get_tmp_folder()}
                if self.fnpattern() and not fnmatch.fnmatch(f, self.fnpattern()):
                    continue
                if self.pattern_matcher() and not self.pattern_matcher().match(f):
                    continue
                
                with NamedTemporaryFile(**tdargs) as fp:
                    ftp.retrbinary("RETR %s"%f, fp.write)
                    fp.flush()
                    self.backend().store_file(fp.name, self.id())
        finally:
            ftp.quit()

    ##
    # Connects to remote server
    def connect(self):
        ftp = ftplib.FTP()
        ftp.connect(self.hostname(), self.port())
        ftp.login(self.username(), self.password())
        return ftp


class copy_fetcher(fetcher):
    """Fetcher file(s) using copy
    """
    def __init__(self, backend, aid, arguments):
        """Constructor
        :param backend: The backend
        :param aid: Id for this fetcher
        :param arguments: Dictionary containg at least:
         {
           "path":"....",
         }
        """
        super(copy_fetcher, self).__init__(backend, aid)
        self._path = arguments["path"]
        self._pattern = None
        self._fnpattern = "*.h5"
        self._pattern_matcher = None
        
        if "pattern" in arguments and arguments["pattern"]:
            self._pattern = arguments["pattern"]
        if "fnpattern" in arguments and arguments["fnpattern"]:
            self._fnpattern = arguments["fnpattern"]
        if self._pattern:
            self._pattern_matcher = re.compile(self._pattern)


    def fetch(self, **kwargs):
        """Fetches the file(s) using copy.
        :param file: path to file that should be published
        :param meta: the meta object for all metadata of file
        """
        logger.debug("Running copy_fetcher")

        files = glob.glob("%s/%s"%(self._path, self._fnpattern))
        
        for f in files:
            bname = os.path.basename(f)
            if self.pattern_matcher() and not self.pattern_matcher().match(bname):
                continue
            self.backend().store_file(f, self.id())

    def pattern_matcher(self):
        """
        :return the pattern matcher
        """
        return self._pattern_matcher


class fetcher_manager:
    """ Creates fetcher instances from a configuration entry
    """

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
            logger.debug("Creating fetcher '%s'"%clz)
            lastdot = clz.rfind(".")
            module = importlib.import_module(clz[:lastdot])
            classname = clz[lastdot+1:]

            return getattr(module, classname)(backend, aid, fetcherargs)
        else:
            raise Exception("Must specify class as module.class")
