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

## Various types of storages.

## @file
## @author Anders Henja, SMHI
## @date 2021-08-18
import json
import logging
import os
import shutil
import stat
from abc import abstractmethod
import importlib

from baltrad.exchange.naming import namer
logger = logging.getLogger("baltrad.exchange.server.backend")

class storage(object):
    """Base class for all storages
    """
    def __init__(self):
        """Constructor
        """
        super(storage, self).__init__()
    
    @abstractmethod
    def name(self):
        """
        :return the name identifying this storage
        """
        raise NotImplementedError()
    
    @abstractmethod
    def store(self, path, meta):
        """ Passes on the file to the storage
        :param path: The full path to the file to be stored
        :param meta: The meta data for this file.
        """
        raise NotImplementedError()

class none_storage(storage):
    """Simple storage that does nothing
    """
    def __init__(self, name, backend, **kwargs):
        """Constructor
        :param name: The name identifying this storage
        """
        super(none_storage, self).__init__()        
        self._name = name

    def store(self, path, meta):
        """ Does nothing but prints that a file would have been stored
        :param path: The full path to the file to be stored
        :param meta: The meta data for this file.
        """
        logger.info("[none_storage - %s]: Would store file %s - %s - %s"%(self.name(), meta.what_source, meta.what_date, meta.what_time))

    def name(self):
        """
        :return the name identifying this storage
        """
        return self._name

class file_store:
    def __init__(self, path, name_pattern, simulate=False):
        self.path = path
        self.name_pattern = name_pattern
        self.namer = namer.metadata_namer(self.name_pattern)
        self._simulate = simulate
    
    def store(self, path, meta):
        oname = "%s/%s"%(self.path, self.namer.name(meta))
        if self._simulate:
            logger.info("[SIMULATE]: Stored file:  %s"%oname)
            return

        dname = os.path.dirname(oname)
        if not os.path.exists(dname):
            os.makedirs(dname, exist_ok=True)    
        shutil.copy(path, oname)        
        os.chmod(oname, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH)
        logger.info("Stored file: %s"%(oname))

class file_storage(storage):
    """A basic file storage that allows separation of files based on object types. A typical structure passed to kwargs would be
    "structure":[
      {"object":"SCAN",
       "path":"/tmp/baltrad_bdb",
       "name_pattern":"${_baltrad/datetime_l:15:%Y/%m/%d/%H/%M}/${_bdb/source:NOD}_${/what/object}.tolower()_${/what/date}T${/what/time}Z_${/dataset1/where/elangle}.h5"
      },
      {"path":"/tmp/baltrad_bdb",
       "name_pattern":"${_baltrad/datetime_l:15:%Y/%m/%d/%H/%M}/${_bdb/source:NOD}_${/what/object}.tolower()_${/what/date}T${/what/time}Z.h5"
      }
    ]
    """
    def __init__(self, name, backend, **kwargs):
        """Constructor
        :param name: The name of this storage
        :param backend: The backend (NOT USED)
        :param kwargs: the configuration required for the file storage.
        """
        super(file_storage, self).__init__()
        self._name = name
        self._backend = backend
        self._simulate = False
        self.structures = {}
        if not "structure" in kwargs:
            raise Exception("Missing key 'structure' in configuration")
        self.structure_d = kwargs["structure"]

        if "simulate" in kwargs and isinstance(kwargs["simulate"], bool):
            self._simulate = kwargs["simulate"]
        
        for s in self.structure_d:
            if ("object" in s and not s["object"]) or "object" not in s:
                self.structures["default"]=file_store(s["path"],s["name_pattern"], self._simulate)
            else:
                self.structures[s["object"]]=file_store(s["path"],s["name_pattern"], self._simulate)

    def get_attribute_value(self, name, meta):
        """
        :param name: Name of attribute
        :param meta: Metadata from where value for name should be taken
        :return the value for the name or None if not found
        """
        try:
            return meta.node(name).value
        except LookupError:
            return None

    def store(self, path, meta):
        """ Stores a file in the correct directory structure
        :param path: The path to the file to be stored
        :param meta: The meta data for the file
        """
        q = self.get_attribute_value("/what/object", meta)
        logger.debug("Using storage %s"%str(self.structures))
        if q in self.structures:
            self.structures[q].store(path, meta)
        elif "default" in self.structures:
            self.structures["default"].store(path, meta)
        else:
            logger.info("Ignoring %s object of type: " % q)

    def name(self):
        """
        :return the name of this storage
        """
        return self._name
 
class storage_manager:
    """ The storage manager
    """
    def __init__(self):
        """Constructor
        """
        self.storage={}
    
    def add_storage(self, storage):
        """ Adds a storage instance to the internal list
        :param storage: The created storage that is a subclass of  baltrad.exchange.storage.storages.storage
        """
        self.storage[storage.name()] = storage
    
    def get_storage(self, name):
        """
        :param name: Name of the storage
        :return the storage with provided name
        """
        return self.storage[name]
    
    def has_storage(self, name):
        """
        :param name: Name of the storage
        :return if there is a storage with specified name
        """
        return name in self.storage
    
    def store(self, name, path, meta):
        """Stores a file in the specified storage.
        :param name: Name in which the file should be stored
        :param path: The file name that should be stored
        :param meta: Metadata about the file that should be stored
        """
        self.storage[name].store(path, meta)
        
    @classmethod
    def create_storage(self, clz, name, backend, extra_arguments):
        """Creates an instance of clz with specified arguments
        :param clz: class name specified as <module>.<classname>
        :param arguments: a list of arguments that should be used to initialize the class       
        """
        if clz.find(".") > 0:
            logger.debug("Creating storage '%s'"%clz)
            lastdot = clz.rfind(".")
            module = importlib.import_module(clz[:lastdot])
            classname = clz[lastdot+1:]
            return getattr(module, classname)(name, backend, **extra_arguments)
        else:
            raise Exception("Must specify class as module.class")
    
    @classmethod
    def from_conf(self, config, backend):
        """Creates a storage from the specified configuration if it is possible
        :param config: A runner config pattern. Should at least contain the following
        { "class":"<packagename>.<classname>",
          "name":<name of storage>,
          "arguments":{}"
        }
        """
        arguments = {}
        storage_clazz = config["class"]
        name = config["name"]
        if "arguments" in config:
            arguments = config["arguments"]

        
        p = self.create_storage(storage_clazz, name, backend, arguments)
        
        return p