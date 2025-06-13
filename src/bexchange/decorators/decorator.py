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

## Decorators are used for modifying, changing, or in other way alter an ODIM H5 file.

## @file
## @author Anders Henja, SMHI
## @date 2021-08-30
import importlib
import sys
import logging
from datetime import timedelta, datetime, timezone

logger = logging.getLogger("bexchange.decorators.decorator")

##
# Decorator
class decorator(object):
    """A decorator is used for modifying a file before it is distributed. Incomming files are not decorated before they are saved. Instead, if that function is
    wanted a copy-publisher should be used instead.
    """
    def __init__(self, backend, discard_on_none):
        self._backend = backend
        self._discard_on_none = discard_on_none
    
    def backend(self):
        """
        :return: the backend
        """
        return self._backend

    def discard_on_none(self):
        """ Returns if this decorator has been configured to discard file completely when decorator is returning None
        """
        return self._discard_on_none
    
    def decorate(self, ino, meta):
        """If this decorator decorates the infile, then a new temporary file will be created and returned.
        :param ino: A tempfile.NamedTemporaryFile instance
        :returns: A tempfile.NamedTemporaryFile instance
        """
        raise Exception("Not implemented")

##
# Example..
class example_filter(decorator):
    def __init__(self, backend, discard_on_none, arg1, arg2):
        super(example_filter, self).__init__(backend, discard_on_none)
        self.arg1=arg1
        self.arg2=arg2
    
    def decorate(self, inf, meta):
        return inf

##
# MAX age filter.
class max_age_filter(decorator):
    """ MAX age filter that will indicate if file should be removed or not. allow_discard is enforced to True since this is a filter.
    """
    def __init__(self, backend, allow_discard, max_acceptable_age=0, max_acceptable_age_block=0, target_name=None):
        """ Constructor
        :param backend: the backend
        :param allow_discard: not used (will be enforced to True)
        :param max_acceptable_age: Max age before an alert message is written
        :param max_acceptable_age_block: Max age before the file is discarded
        """
        super(max_age_filter, self).__init__(backend, True)  # We force discarding of files since that is the reason for this filter
        self._max_acceptable_age = max_acceptable_age
        self._max_acceptable_age_block = max_acceptable_age_block
        self._target_name = target_name
    
    def decorate(self, inf, meta):
        """ Will  use the metadata to know if the file should be filtered or not.
        """
        if self._max_acceptable_age > 0 and self._max_acceptable_age_block > 0:
            fileUTC = datetime(meta.what_date.year, meta.what_date.month, meta.what_date.day, meta.what_time.hour, meta.what_time.minute, meta.what_time.second, tzinfo=timezone.utc)
            nowUTC = datetime.now(timezone.utc)
            file_delay = nowUTC - fileUTC
            if file_delay < timedelta(seconds = self._max_acceptable_age):
                pass
            elif file_delay >= timedelta(seconds = self._max_acceptable_age) and file_delay < timedelta(seconds=self._max_acceptable_age_block):
                if meta.what_object == "SCAN":
                    logger.info("Alert message: the SCAN %s with elangle %2.1f from %s was processed %5.2f s after nominal /what/time"% \
                        (meta.what_time, meta.find_node("/dataset1/where/elangle").value, meta.bdb_source_name, file_delay.total_seconds()))
                else:
                    logger.info("Alert message: the PVOL from %s was processed %5.2f s after nominal /what/time"%(meta.what_time, meta.bdb_source_name, file_delay.total_seconds()))
            elif file_delay > timedelta(seconds = self._max_acceptable_age_block):
                target_str=""
                if self._target_name:
                    target_str = " to %s"%self._target_name

                if meta.what_object == "SCAN":
                    logger.info("Block message: the SCAN %s with elangle %2.1f from %s was blocked{target_str}, it is %5.2f s after nominal /what/time (threshold %5.2f s)"% \
                        (meta.what_time, meta.find_node("/dataset1/where/elangle").value, meta.bdb_source_name, file_delay.total_seconds(), float(self._max_acceptable_age_block)))
                else:
                    logger.info("Block message: the PVOL %s from %s was blocked{target_str}, it is %5.2f s after nominal /what/time (threshold %5.2f s)"% \
                        (meta.what_time, meta.bdb_source_name, file_delay.total_seconds(), float(self.max_acceptable_file_age_block)))
                return None
        return inf


##
# Manager that handles the creation of decorators from a class name and a number of arguments.
#
class decorator_manager:
    """The manager for creating decorators used within bexchange. If a class extends the decorator
    class it can be created by invoking decorator_manager.create("module....class name", arguments as a list) 
    """
    def __init__(self):
        """Constructor
        """
        pass
    
    @classmethod
    def create(self, backend, clz, discard_on_none, arguments):
        """Creates an instance of clz with specified arguments
        :param clz: class name specified as <module>.<classname>
        :param discard_on_none: If decorate returns None, then this file should be discarded.
        :param arguments: a list of arguments that should be used to initialize the class       
        """
        logger.info("Creating decorator: %s"%clz)
        if clz.find(".") > 0:
            lastdot = clz.rfind(".")
            module = importlib.import_module(clz[:lastdot])
            classname = clz[lastdot+1:]
            return getattr(module, classname)(backend, discard_on_none, **arguments)
        else:
            raise Exception("Must specify class as module.class")
