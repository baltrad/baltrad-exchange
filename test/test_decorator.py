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

## Tests baltrad.exchange.naming.namer

## @file
## @author Anders Henja, SMHI
## @date 2021-08-18
from __future__ import absolute_import

import unittest
from unittest.mock import MagicMock
from bexchange.decorators.decorator import decorator_manager, decorator

class test_filter(decorator):
    def __init__(self, backend, allow_discard, arg1, arg2):
        super(test_filter, self).__init__(backend, allow_discard)
        self.arg1=arg1
        self.arg2=arg2
    
    def decorate(self, inf):
        return inf

class test_decorator_manager(unittest.TestCase):
    def test_create_instance(self):
        backend = MagicMock()
        clz = decorator_manager.create(backend, "test_decorator.test_filter", True, {"arg1":"a1", "arg2":"a2"})
        self.assertEqual(True, clz.allow_discard())
        self.assertEqual("a1", clz.arg1)
        self.assertEqual("a2", clz.arg2)        

    def test_create_instance_invalid_arguments(self):
        try:
            backend = MagicMock()
            clz = decorator_manager.create(backend, "test_decorator.test_filter", True, {"arg1":"a1"})
            self.fail("Expected TypeError")
        except TypeError:
            pass
