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

## A decorator indicating abstract classmethods

## @file
## @author Anders Henja, SMHI
## @date 2021-08-18
from abc import ABC, abstractmethod

class abstractclassmethod(classmethod):
    """A decorator indicating abstract classmethods.

    Similar to abstractmethod.

    Usage:

        class C(metaclass=ABCMeta):
            @abstractclassmethod
            def my_abstract_classmethod(cls, ...):
                ...
    """

    __isabstractmethod__ = True

    def __init__(self, callable):
        callable.__isabstractmethod__ = True
        super(abstractclassmethod, self).__init__(callable)

class message_aware(ABC):
    @abstractmethod
    def handle_message(self, json_message, nodename):
        """Implement to handle the json message
        :param json_message: The json message
        """
        raise NotImplementedError("Not implemented handle_message")
    