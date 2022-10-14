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

## Various types of processors.

## @file
## @author Anders Henja, SMHI
## @date 2022-10-05
import json
import logging
import os
import shutil
import importlib

from baltrad.exchange.naming import namer

logger = logging.getLogger("baltrad.exchange.processor")

class processor:
    def __init__(self, backend, name, active, extra_arguments=None):
        self._backend = backend
        self._name = name
        self._active = active
    
    def backend(self):
        return self._backend
    
    def name(self):
        return self._name
    
    def active(self):
        return self._active
    
    def process(self, path, metadata):
        """ The process function. Must be non-blocking. Otherwise this will lock up threads.
        This means that the path/metadata should be put on a queue or in some other way passed
        on to the actual processing-part without locking up the resources.
        """
        raise NotImplementedError()

    def start(self):
        pass
    
    def stop(self):
        pass

class example_processor(processor):
    def __init__(self, backend, name, active, extra_arguments):
        super(example_processor, self).__init__(backend, name, active)
        self._name = name

    def process(self, path, meta):
        logger.debug("Running processor %s of type %s"%(self.name(), self.name_repr()))
        
class processor_manager:
    """ The processor manager. Will ensure that files are passed on to the processors.
    """
    def __init__(self):
        """Constructor
        """
        self.processors={}

    def add_processor(self, processor):
        """Adds a processor to the manager
        :param processor: The processor that should be added
        """
        self.processors[processor.name()] = processor

    def process(self, file, meta):
        """ Passes on the file to all registered processors. It is up to the processor to determine how
        the provided file should be handled.
        """
        pass

    @classmethod
    def create_processor(self, name, clz, backend, active, extra_arguments):
        """Creates an instance of clz with specified arguments
        :param clz: class name specified as <module>.<classname>
        :param arguments: a list of arguments that should be used to initialize the class       
        """
        if clz.find(".") > 0:
            logger.info("Creating processor '%s'"%clz)
            lastdot = clz.rfind(".")
            module = importlib.import_module(clz[:lastdot])
            classname = clz[lastdot+1:]
            return getattr(module, classname)(backend, name, active, extra_arguments)
        else:
            raise Exception("Must specify class as module.class")
    
    @classmethod
    def from_conf(self, config, backend):
        name = "unknown"
        active = False
        extra_arguments = {}
        
        name = config["name"]
        processor_clazz = config["class"]
        if "extra_arguments" in config:
            extra_arguments = config["extra_arguments"]

        if "active" in config:
            active = config["active"]
        
        p = self.create_processor(name, processor_clazz, backend, active, extra_arguments)
        
        p.start()
        
        return p
        
