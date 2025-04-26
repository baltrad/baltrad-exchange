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

from bexchange.naming import namer

logger = logging.getLogger("bexchange.processor")

class processor:
    """Base class to be used by all processor implementations
    """
    def __init__(self, backend, name, active, extra_arguments=None):
        """Constructor
        :param backend: The backend that this processor should have access to
        :param name: Name that identifies this processor
        :param active: If this processor should be active or not
        :param extra_arguments: The extra arguments used when creating the processor
        """
        self._backend = backend
        self._name = name
        self._active = active
    
    def backend(self):
        """
        :return: the backend instance
        """
        return self._backend
    
    def name(self):
        """
        :return: the name of this processor
        """
        return self._name
    
    def active(self):
        """
        :return: if this processor is active or not
        """
        return self._active
    
    def process(self, path, metadata):
        """ The process function. Must be non-blocking. Otherwise this will lock up threads.
        This means that the path/metadata should be put on a queue or in some other way passed
        on to the actual processing-part without locking up the resources.
        """
        raise NotImplementedError()

    def start(self):
        """Starts this processor. Typically by starting a thread or consumer pool
        """
        pass
    
    def stop(self):
        """Stops this processor. Typically by joining a number of threads
        """
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

    def remove_processor(self, name):
        """Removes a processor from the manager
        :param name: The name of the processor that should be removed
        """
        if name in self.processors:
            try:
                self.processors[name].stop()
            except:
                logger.exception("Failed to stop processor: %s"%name)

            try:
                del self.processors[name]
            except:
                logger.exception("Failed to remove processor: %s"%name)

    def process(self, file, meta):
        """ Passes on the file to all registered processors. It is up to the processor to determine how
        the provided file should be handled.
        """
        for key, processor in self.processors.items():
            try:
                processor.process(file, meta) 
            except:
                logger.exception("Processor: %s could not process file %s"%(key, file))

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
        """Creates a processor instance from provided json config
        :param config: The json config as a dictionary
        :param backend: The backend this processor should have access to
        :return: the processor instance
        """
        name = "unknown"
        active = False
        extra_arguments = {}
        
        name = config["name"]
        processor_clazz = config["class"]
        if "extra_arguments" in config:
            extra_arguments = config["extra_arguments"]

        if "active" in config:
            active = config["active"]
        
        if active:
            p = self.create_processor(name, processor_clazz, backend, active, extra_arguments)
            p.start()
            return p
        else:
            logger.info("Processor with name %s is not active"%name)

        return None
        
