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
import datetime

from bexchange.matching import metadata_matcher, filters

from baltrad.bdbcommon import oh5, expr
from baltrad.bdbcommon.oh5.meta import Metadata
from baltrad.bdbcommon.oh5.node import Attribute, Group

class test_matcher(unittest.TestCase):
    def setUp(self):
        self._matcher = metadata_matcher.metadata_matcher()
        self._manager = filters.filter_manager()
    
    def tearDown(self):
        self._matcher = None

    def test_always(self):
        meta = Metadata();
        meta.add_node("/", Group("what"))
        meta.add_node("/what", Attribute("source", "WMO:02606"))
        meta.add_node("/what", Attribute("date", datetime.date(2000, 1, 2)))
        meta.add_node("/what", Attribute("time", datetime.time(12, 5)))
        meta.add_node("/what", Attribute("object", "pvol"))

        v = {"filter_type":"always_filter", "value":""}

        ifilter = self._manager.from_value(v)

        self.assertEqual(True, self._matcher.match(meta, ifilter.to_xpr()))

    def test_and_always(self):
        meta = Metadata();
        meta.add_node("/", Group("what"))
        meta.add_node("/what", Attribute("source", "WMO:02606"))
        meta.add_node("/what", Attribute("date", datetime.date(2000, 1, 2)))
        meta.add_node("/what", Attribute("time", datetime.time(12, 5)))
        meta.add_node("/what", Attribute("object", "pvol"))

        v = {"filter_type": "and_filter", "value": [{"filter_type":"always_filter", "value":""}, {"filter_type":"always_filter", "value":""}]}

        ifilter = self._manager.from_value(v)

        self.assertEqual(True, self._matcher.match(meta, ifilter.to_xpr()))
