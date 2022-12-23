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

## Different type of connections

## @file
## @author Anders Henja, SMHI
## @date 2021-12-01
from bexchange.net.senders import sender_manager
import logging
import importlib

logger = logging.getLogger("bexchange.net.connections")

class publisher_connection(object):
    """publisher connections are used for publishing files in various ways without taking the protocol / sender into account.
    Each (or most) publisher_connection is associated with one or more senders.
    """
    def __init__(self, backend):
        """Constructor
        :param backend: The backend
        """
        self._backend = backend
    
    def publish(self, path, meta):
        """Publishes a file in some way using the underlying implementation
        :param path: The path to the file
        :param meta: The metadata of the file
        """
        raise Exception("Not implemented")
    
    def backend(self):
        """Returns the backend
        """
        return self._backend

class simple_connection(publisher_connection):
    """Simple connection, only parsing arguments according to. sender class + arguments. 
    """
    def __init__(self, backend, arguments):
        """Constructor
        :param backend: The backend
        :param arguments: A dictionary with relevant arguments. At least
        {"sender":...}
        """
        super(simple_connection, self).__init__(backend)
        if "sender" in arguments:
            self._sender = sender_manager.from_conf(backend, arguments["sender"])
        else:
            raise Exception("Requires 'sender' in arguments")
    
    def publish(self, path, meta):
        """Publishes the file using the sender
        :param path: The path to the file
        :param meta: The metadata of the file
        """
        self._sender.send(path, meta)

class failover_connection(publisher_connection):
    """Failover connection, expects a list of senders in arguments. Where they are tried in 
    order until one works. 
    """
    def __init__(self, backend, arguments):
        """Constructor
        :param backend: The backend
        :param arguments: A dictionary with relevant arguments. At least
        {"senders":[...]}
        """
        super(failover_connection, self).__init__(backend)
        self._senders = []
        if "senders" in arguments:
            for sender_conf in arguments["senders"]:
                self._senders.append(sender_manager.from_conf(backend, sender_conf))
        else:
            raise Exception("Requires 'senders' in arguments")
        
    def publish(self, path, meta):
        """Publishes the file using the senders. When first successful publishing has successfully
        been transmitted, the method returns. If on the other hand no senders are successfully used
        an exception will be thrown.
        :param path: The path to the file
        :param meta: The metadata of the file
        """
        successful = False
        for sender in self._senders:
            try:
                sender.send(path, meta)
                logger.info("Successfully sent %s to %s"%(path, sender.id()))
                successful = True
                break
            except Exception as e:
                logger.exception("Failed to send %s to %s"%(path, sender.id()), e);
        if not successful:
            raise Exception("Failed to publish using the failover connection")

class backup_connection(publisher_connection):
    """Backup connection, expects a list of senders in arguments. Where all senders are run. 
    """
    def __init__(self, backend, arguments):
        super(backup_connection, self).__init__(backend)
        self._senders = []
        if "senders" in arguments:
            for sender_conf in arguments["senders"]:
                self._senders.append(sender_manager.from_conf(backend, sender_conf))
        else:
            raise Exception("Requires 'senders' in arguments")
        
    def publish(self, path, meta):
        for sender in self._senders:
            try:
                sender.send(path, meta)
                logger.info("Successfully sent %s to %s"%(path, sender.id()))
            except Exception as e:
                logger.exception("Failed to send %s to %s"%(path, sender.id()), e);
    
class connection_manager(object):
    """The connection manager is used for creating connection instances from the provided configuration
    """
    def __init__(self):
        """Constructor
        """
        pass
    
    @classmethod
    def from_conf(self, backend, clz, arguments):
        """Creates an instance of clz with specified arguments
        :param clz: class name specified as <module>.<classname>
        :param arguments: a list of arguments that should be used to initialize the class       
        """
        if clz.find(".") > 0:
            logger.debug("Creating connection handler '%s'"%clz)
            lastdot = clz.rfind(".")
            module = importlib.import_module(clz[:lastdot])
            classname = clz[lastdot+1:]
            return getattr(module, classname)(backend, arguments)
        else:
            raise Exception("Must specify class as module.class")
