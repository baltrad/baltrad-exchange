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

## Abstract backend

## @file
## @author Anders Henja, SMHI
## @date 2021-08-18

from abc import abstractmethod, ABCMeta

import pkg_resources

from baltrad.exchange.util import abstractclassmethod

from baltrad.exchange import config

class DuplicateEntry(Exception):
    """thrown to indicate that an entry already exists
    """

class IntegrityError(RuntimeError):
    """thrown to indicate a conflict between resources
    """
    pass

class Backend(object):
    """Backend interface
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def store(self, path):
        """store a file in the database
        :param path: path to the file
        :type path: string
        """
        raise NotImplementedError()

    @abstractmethod
    def metadata_from_file(self, path):
        """Parses a file and returns the metadata for this file.
        :param path: path to the file
        :type path: string
        :return the metadata for this file
        """
        raise NotImplementedError()
    
    @abstractmethod
    def get_storage_manager(self):
        """Returns the storage manager
        :return the storage manager
        """
        raise NotImplementedError()    
    
    @abstractmethod
    def get_auth_manager(self):
        """Returns the auth manager
        :return the auth manager
        """
        raise NotImplementedError()    
