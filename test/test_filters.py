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

## Tests baltrad.exchange.matching.filters

## @file
## @author Anders Henja, SMHI
## @date 2021-08-18
from __future__ import absolute_import

import unittest

from bexchange.matching import filters

from baltrad.bdbcommon import oh5, expr
from baltrad.bdbcommon.oh5.node import Attribute, Group

class test_filters(unittest.TestCase):
    def setUp(self):
        self.manager = filters.filter_manager()
    
    def tearDown(self):
        self.manager = None

    def test_attribute_filter_name_repr(self):
        self.assertEqual("attribute_filter", filters.attribute_filter.name_repr())

    def test_attribute_filter_from_conf(self):
        v = {"filter_type": "attribute_filter", 
             "name": "some/value", 
             "operation": "=", 
             "value_type": "string", 
             "value": "sehem"}
        
        ifilter = filters.attribute_filter.from_value(v, self.manager)
        self.assertEqual("some/value", ifilter.name)
        self.assertEqual("=", ifilter.operation)
        self.assertEqual("string", ifilter.value_type)
        self.assertEqual("sehem", ifilter.value)
        
    def test_attribute_filter_to_xpr(self):
        ifilter = filters.attribute_filter("some/value", "=", "string", "sehem")
        expected = [expr.symbol("="), [expr.symbol("attr"), "some/value", "string"], "sehem"]
        self.assertEqual(expected, ifilter.to_xpr())

    def test_and_filter_name_repr(self):
        self.assertEqual("and_filter", filters.and_filter.name_repr())

    def test_and_filter_from_conf(self):
        v = {"filter_type": "and_filter",
             "value":[
                 {"filter_type": "attribute_filter", 
                  "name": "some/value", 
                  "operation": "=", 
                  "value_type": "string", 
                  "value": "sehem"},
                 {"filter_type": "attribute_filter", 
                  "name": "some/othervalue", 
                  "operation": "=", 
                  "value_type": "double", 
                  "value": 1.5}
                 ]}
        
        ifilter = filters.and_filter.from_value(v, self.manager)
        self.assertEqual(2, len(ifilter.value))
        self.assertTrue(isinstance(ifilter.value[0], filters.attribute_filter))
        self.assertEqual("some/value", ifilter.value[0].name)
        self.assertEqual("=", ifilter.value[0].operation)
        self.assertEqual("string", ifilter.value[0].value_type)
        self.assertEqual("sehem", ifilter.value[0].value)
        self.assertTrue(isinstance(ifilter.value[1], filters.attribute_filter))
        self.assertEqual("some/othervalue", ifilter.value[1].name)
        self.assertEqual("=", ifilter.value[1].operation)
        self.assertEqual("double", ifilter.value[1].value_type)
        self.assertEqual(1.5, ifilter.value[1].value, 4)

    def test_and_filter_to_xpr(self):
        ifilter = filters.and_filter([filters.attribute_filter("some/value", "=", "string", "sehem"), filters.attribute_filter("some/othervalue", "=", "double", 1.5)])
        expected = [expr.symbol("and"), [expr.symbol("="), [expr.symbol("attr"), "some/value", "string"], "sehem"], [expr.symbol("="), [expr.symbol("attr"), "some/othervalue", "double"], 1.5]]
        self.assertEqual(expected, ifilter.to_xpr())
        
    def test_or_filter_name_repr(self):
        self.assertEqual("or_filter", filters.or_filter.name_repr())

    def test_or_filter_from_conf(self):
        v = {"filter_type": "or_filter",
             "value":[
                 {"filter_type": "attribute_filter", 
                  "name": "some/value", 
                  "operation": "=", 
                  "value_type": "string", 
                  "value": "sehem"},
                 {"filter_type": "attribute_filter", 
                  "name": "some/othervalue", 
                  "operation": "=", 
                  "value_type": "double", 
                  "value": 1.5}
                 ]}
        
        ifilter = filters.or_filter.from_value(v, self.manager)
        self.assertEqual(2, len(ifilter.value))
        self.assertTrue(isinstance(ifilter.value[0], filters.attribute_filter))
        self.assertEqual("some/value", ifilter.value[0].name)
        self.assertEqual("=", ifilter.value[0].operation)
        self.assertEqual("string", ifilter.value[0].value_type)
        self.assertEqual("sehem", ifilter.value[0].value)
        self.assertTrue(isinstance(ifilter.value[1], filters.attribute_filter))
        self.assertEqual("some/othervalue", ifilter.value[1].name)
        self.assertEqual("=", ifilter.value[1].operation)
        self.assertEqual("double", ifilter.value[1].value_type)
        self.assertEqual(1.5, ifilter.value[1].value, 4)

    def test_or_filter_to_xpr(self):
        ifilter = filters.or_filter([filters.attribute_filter("some/value", "=", "string", "sehem"), filters.attribute_filter("some/othervalue", "=", "double", 1.5)])
        expected = [expr.symbol("or"), [expr.symbol("="), [expr.symbol("attr"), "some/value", "string"], "sehem"], [expr.symbol("="), [expr.symbol("attr"), "some/othervalue", "double"], 1.5]]
        self.assertEqual(expected, ifilter.to_xpr())   
        
    def test_not_filter_name_repr(self):
        self.assertEqual("not_filter", filters.not_filter.name_repr())

    def test_not_filter_from_conf(self):
        v = {"filter_type": "not_filter",
             "value":{"filter_type": "attribute_filter", 
                  "name": "some/value", 
                  "operation": "=", 
                  "value_type": "string", 
                  "value": "sehem"
               }
            }
        ifilter = filters.not_filter.from_value(v, self.manager)

        self.assertTrue(isinstance(ifilter.value, filters.attribute_filter))
        self.assertEqual("some/value", ifilter.value.name)
        self.assertEqual("=", ifilter.value.operation)
        self.assertEqual("string", ifilter.value.value_type)
        self.assertEqual("sehem", ifilter.value.value)

    def test_not_filter_to_xpr(self):
        ifilter = filters.not_filter(filters.attribute_filter("some/value", "=", "string", "sehem"))
        expected = [expr.symbol("not"), [expr.symbol("="), [expr.symbol("attr"), "some/value", "string"], "sehem"]]
        self.assertEqual(expected, ifilter.to_xpr())

    def test_always_filter_to_xpr(self):
        ifilter = filters.always_filter()
        self.assertEqual(True, ifilter.to_xpr())
