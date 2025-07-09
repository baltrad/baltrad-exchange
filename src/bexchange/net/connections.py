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
from bexchange import util
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
                logger.info("failover_connection: Successfully sent file to %s, ID:'%s'"%(sender.id(), util.create_fileid_from_meta(meta)))
                successful = True
                break
            except:
                logger.exception("failover_connection: Failed to send file to %s, ID:'%s', trying next in list"%(sender.id(), util.create_fileid_from_meta(meta)))
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
                logger.info("Successfully sent file to %s, ID:'%s'"%(sender.id(), util.create_fileid_from_meta(meta)))
            except Exception as e:
                logger.exception("Failed to send file to %s, ID:'%s'"%(sender.id(), util.create_fileid_from_meta(meta)))

class distributed_connection(publisher_connection):
    """Distributed connection, expects a list of senders in arguments. Where all senders are run. This is the same
    behavior as the backup connection but it's here for readability.
    """
    def __init__(self, backend, arguments):
        super(distributed_connection, self).__init__(backend)
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
                logger.info("Successfully sent file to %s, ID:'%s'"%(sender.id(), util.create_fileid_from_meta(meta)))
            except Exception as e:
                logger.exception("Failed to send file to %s, ID:'%s'"%(sender.id(), util.create_fileid_from_meta(meta)))

class combined_connection(publisher_connection):
    """Combined connection is a way to combine different connection types into one so that you for example can
    have different connections in one. For example, assume that you always wants a file to be sent to a specific
    target and then that you want a sequence of fail over connections after that.
    """
    def __init__(self, backend, arguments):
        super(combined_connection, self).__init__(backend)
        self._connections = []
        if "connections" in arguments:
            for conncfg in arguments["connections"]:
                if "class" in conncfg:
                    args = []
                    if "arguments" in conncfg:
                        args = conncfg["arguments"]
                    self._connections.append(connection_manager.from_conf(backend, conncfg["class"], args))
        else:
            raise Exception("Requires 'connections' in arguments")
        
    def publish(self, path, meta):
        """ Publishes the file to all connections for this connection
        :param path: the file path
        :param meta: the metadata 
        """
        for connection in self._connections:
            try:
                connection.publish(path, meta)
            except Exception as e:
                logger.exception("Failed to publish file to %s, ID:'%s'"%(sender.id(), util.create_fileid_from_meta(meta)))


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
            logger.info("Creating connection handler '%s'"%clz)
            lastdot = clz.rfind(".")
            module = importlib.import_module(clz[:lastdot])
            classname = clz[lastdot+1:]
            return getattr(module, classname)(backend, arguments)
        else:
            raise Exception("Must specify class as module.class")
