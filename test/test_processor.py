# Copyright (C) 2022- Swedish Meteorological and Hydrological Institute (SMHI)
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
## @date 2022-10-12
from __future__ import absolute_import

import unittest
from unittest.mock import MagicMock

from bexchange.processor.processors import processor_manager, processor

class test_processor(processor):
    def __init__(self, backend, name, active, extra_arguments):
        super(test_processor, self).__init__(backend, name, active)
        self._args = extra_arguments
    
    def name(self):
        return "test_processor"
    
    def run(self, path, metadata):
        return None

class test_processor_manager(unittest.TestCase):
    def test_create_processor(self):
        #name, clz, backend, active, extra_arguments)
        backend = MagicMock()
        extra_args={}
        extra_args["hej"]="yay"
        clz = processor_manager.create_processor("testit", "test_processor.test_processor", backend, True, extra_args)
        self.assertTrue(clz._args == extra_args)

    #def test_create_instance_invalid_arguments(self):
    #    try:
    #        clz = decorator_manager.create("test_decorator.test_filter", ["a1"])
    #        self.fail("Expected TypeError")
    #    except TypeError:
    #        pass
