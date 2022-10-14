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
from baltrad.exchange.net.adaptors import adaptor_manager
import logging
import importlib

logger = logging.getLogger("baltrad.exchange.net.adaptors")

class publisher_connection(object):
    """publisher connections are used for publishing files in various ways without taking the protocol / adaptor into account.
    Each (or most) publisher_connection is associated with one or more adaptors.
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
    """Simple connection, only parsing arguments according to. adapter class + arguments. 
    """
    def __init__(self, backend, arguments):
        """Constructor
        :param backend: The backend
        :param arguments: A dictionary with relevant arguments. At least
        {"adaptor":...}
        """
        super(simple_connection, self).__init__(backend)
        if "adaptor" in arguments:
            self._adaptor = adaptor_manager.from_conf(backend, arguments["adaptor"])
        else:
            raise Exception("Requires 'adaptor' in arguments")
    
    def publish(self, path, meta):
        """Publishes the file using the adaptor
        :param path: The path to the file
        :param meta: The metadata of the file
        """
        self._adaptor.publish(path, meta)

class failover_connection(publisher_connection):
    """Failover connection, expects a list of adaptors in arguments. Where they are tried in 
    order until one works. 
    """
    def __init__(self, backend, arguments):
        """Constructor
        :param backend: The backend
        :param arguments: A dictionary with relevant arguments. At least
        {"adaptors":[...]}
        """
        super(failover_connection, self).__init__(backend)
        self._adaptors = []
        if "adaptors" in arguments:
            for adaptor_conf in arguments["adaptors"]:
                self._adaptors.append(adaptor_manager.from_conf(backend, adaptor_conf))
        else:
            raise Exception("Requires 'adaptors' in arguments")
        
    def publish(self, path, meta):
        """Publishes the file using the adaptors. When first successful publishing has successfully
        been transmitted, the method returns. If on the other hand no adaptors are successfully used
        an exception will be thrown.
        :param path: The path to the file
        :param meta: The metadata of the file
        """
        successful = False
        for adaptor in self._adaptors:
            try:
                adaptor.publish(path, meta)
                logger.info("Successfully published %s to %s"%(path, adaptor.id()))
                successful = True
                break
            except Exception as e:
                logger.exception("Failed to publish %s to %s"%(path, adaptor.id()), e);
        if not successful:
            raise Exception("Failed to publish using the failover connection")

class backup_connection(publisher_connection):
    """Backup connection, expects a list of adaptors in arguments. Where all adaptors are run. 
    """
    def __init__(self, backend, arguments):
        super(backup_connection, self).__init__(backend)
        self._adaptors = []
        if "adaptors" in arguments:
            for adaptor_conf in arguments["adaptors"]:
                self._adaptors.append(adaptor_manager.from_conf(backend, adaptor_conf))
        else:
            raise Exception("Requires 'adaptors' in arguments")
        
    def publish(self, path, meta):
        for adaptor in self._adaptors:
            try:
                adaptor.publish(path, meta)
                logger.info("Successfully published %s to %s"%(path, adaptor.id()))
            except Exception as e:
                logger.exception("Failed to publish %s to %s"%(path, adaptor.id()), e);
    
class connection_manager(object):
    def __init__(self):
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
