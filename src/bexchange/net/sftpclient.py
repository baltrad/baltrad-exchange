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

## sftpclient implementation

## @file
## @author Anders Henja, SMHI
## @date 2022-11-01
import os
import paramiko
import logging
import stat

logger = logging.getLogger("bexchange.net.sftpclient")

class sftpclient(object):
    """ Implementation of a sftpclient using paramiko
    """
    def __init__(self, host, port, username, password, timeout=30.0, banner_timeout=30):
        """Constructor
        :param host: The host name
        :param port: The port number
        :param username: User to login as
        :param password: Password
        :param timeout: The connection timeout (default 30 seconds)
        :param banner_timeout: The banner connection timeout (default 30 seconds)
        """
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._timeout = timeout
        self._banner_timeout = banner_timeout
        self._sftp = None
        self._client = None

    def hostname(self):
        """
        :return the hostname
        """
        return self._host
    
    def port(self):
        """
        :return the port number
        """
        return self._port
    
    def username(self):
        """
        :return the username
        """
        return self._username
    
    def password(self):
        """
        :return the password
        """
        return self._password
        
    def disconnect(self):
        """ Disconnects from the sftp server
        """
        if self._sftp:
            try:
                self._sftp.close()
            except:
                logger.exception("Failed to close sftp connection")
            self._sftp = None

        if self._client:
            try:
                self._client.close()
            except:
                logger.exception("Failed to close client connection")
            self._client = None        
    
    def connect(self):
        """
        (Re)connects to the sftp server
        """
        self.disconnect()
        try:
            self._client = paramiko.SSHClient()
            self._client.load_system_host_keys()
            self._client.connect(self.hostname(), port=self.port(), username=self.username(), banner_timeout=self._banner_timeout)
            self._sftp = self._client.open_sftp()
            self._sftp.get_channel().settimeout(self._timeout)
        except:
            self._sftp = None
            self._client = None
            raise

    def isfile(self, path):
        """
        :param path: Path name to check
        :return if specified path is a file or not
        """
        try:
            result = stat.S_ISREG(self._sftp.stat(path).st_mode)
        except:
            result = False
        return result

    def isdir(self, path):
        """
        :param path: Path name to check
        :return if specified path is a dir or not
        """
        try:
            result = stat.S_ISDIR(self._sftp.stat(path).st_mode)
        except:
            result = False
        return result
    
    def makedirs(self, targetdir):
        """ Creates the directories if they don't exist
        :param targetdir: The structure to create from current wd
        """
        if self.isdir(targetdir):
            pass
        elif self.isfile(targetdir):
            raise Exception("Can not create directory with same name as file: %s"%targetdir)
        else:
            bdir, bname = os.path.split(targetdir)
            if bdir and not self.isdir(bdir):
                self.makedirs(bdir)
            if bname:
                self._sftp.mkdir(targetdir)
                         
    def chdir(self, dirname):
        """ Changes current directory on server
        :param dirname: The directory to change to
        """
        self._sftp.chdir(dirname)
    
    def listdir(self, dirname):
        """Lists files and directories in the directory
        :param dirname: The directory to list
        :return a list of names
        """
        return self._sftp.listdir(dirname)    
    
    def put(self, filename, targetname):
        """ Uploads the file (filename) to the server named targetname.
        :param filename: Source filename to upload
        :param targetname: The destination name
        """
        self._sftp.put(filename, targetname)

    def get(self, filename, targetname):
        """ Fetches the file (filename) from the server and saves it as targetname.
        :param filename: Source filename to download
        :param targetname: The destination name to save as
        """
        self._sftp.get(filename, targetname)
        
    def getfo(self, remotepath, fl):
        """ Copies the file (remotepath) from the server and writes to an open file.
        Typically used like:
        with NamedTemporaryFile() as fp:
          c.getfo("....", fp)
        :param remotepath: Source filename to download
        :param fl: The destination file object
        """
        self._sftp.getfo(remotepath, fl)
    
    def __enter__(self):
        """
        Enter part when using with ...
        """
        self.connect()
        return self
  
    def __exit__(self, exc_type, exc_value, exc_traceback):
        """
        Exit part when using with ...
        """
        self.disconnect()
  