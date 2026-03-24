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

    def test_and_2_values(self):
        meta = Metadata();
        meta.add_node("/", Group("what"))
        meta.add_node("/what", Attribute("source", "WMO:02606"))
        meta.add_node("/what", Attribute("date", datetime.date(2000, 1, 2)))
        meta.add_node("/what", Attribute("time", datetime.time(12, 5)))
        meta.add_node("/what", Attribute("object", "pvol"))

        v = {"filter_type": "and_filter", 
             "value": [
              {"filter_type": "attribute_filter",  "name": "/what/source", "operation": "=", "value_type": "string", "value": ["WMO:02606"]},
              {"filter_type": "attribute_filter",  "name": "/what/date", "operation": "=", "value_type": "string", "value": ["20000102"]}
             ]
            }

        ifilter = self._manager.from_value(v)

        self.assertEqual(True, self._matcher.match(meta, ifilter.to_xpr()))

    def test_and_3_values(self):
        meta = Metadata();
        meta.add_node("/", Group("what"))
        meta.add_node("/what", Attribute("source", "WMO:02606"))
        meta.add_node("/what", Attribute("date", datetime.date(2000, 1, 2)))
        meta.add_node("/what", Attribute("time", datetime.time(12, 5)))
        meta.add_node("/what", Attribute("object", "pvol"))

        v = {"filter_type": "and_filter", 
             "value": [
              {"filter_type": "attribute_filter",  "name": "/what/source", "operation": "=", "value_type": "string", "value": ["WMO:02606"]},
              {"filter_type": "attribute_filter",  "name": "/what/date", "operation": "=", "value_type": "string", "value": ["20000102"]},
              {"filter_type": "attribute_filter",  "name": "/what/time", "operation": "=", "value_type": "string", "value": ["120500"]}
             ]
            }

        ifilter = self._manager.from_value(v)

        self.assertEqual(True, self._matcher.match(meta, ifilter.to_xpr()))

    def test_and_4_values(self):
        meta = Metadata();
        meta.add_node("/", Group("what"))
        meta.add_node("/what", Attribute("source", "WMO:02606"))
        meta.add_node("/what", Attribute("date", datetime.date(2000, 1, 2)))
        meta.add_node("/what", Attribute("time", datetime.time(12, 5)))
        meta.add_node("/what", Attribute("object", "pvol"))

        v = {"filter_type": "and_filter", 
             "value": [
              {"filter_type": "attribute_filter",  "name": "/what/source", "operation": "=", "value_type": "string", "value": ["WMO:02606"]},
              {"filter_type": "attribute_filter",  "name": "/what/date", "operation": "=", "value_type": "string", "value": ["20000102"]},
              {"filter_type": "attribute_filter",  "name": "/what/time", "operation": "=", "value_type": "string", "value": ["120500"]},
              {"filter_type": "attribute_filter",  "name": "/what/object", "operation": "=", "value_type": "string", "value": ["pvol"]}
             ]
            }

        ifilter = self._manager.from_value(v)

        self.assertEqual(True, self._matcher.match(meta, ifilter.to_xpr()))

    def test_and_4_values_False(self):
        meta = Metadata();
        meta.add_node("/", Group("what"))
        meta.add_node("/what", Attribute("source", "WMO:02606"))
        meta.add_node("/what", Attribute("date", datetime.date(2000, 1, 2)))
        meta.add_node("/what", Attribute("time", datetime.time(12, 5)))
        meta.add_node("/what", Attribute("object", "pvol"))

        v = {"filter_type": "and_filter", 
             "value": [
              {"filter_type": "attribute_filter",  "name": "/what/source", "operation": "=", "value_type": "string", "value": ["WMO:02606"]},
              {"filter_type": "attribute_filter",  "name": "/what/date", "operation": "=", "value_type": "string", "value": ["20000102"]},
              {"filter_type": "attribute_filter",  "name": "/what/time", "operation": "=", "value_type": "string", "value": ["120500"]},
              {"filter_type": "attribute_filter",  "name": "/what/object", "operation": "=", "value_type": "string", "value": ["scan"]}
             ]
            }

        ifilter = self._manager.from_value(v)

        self.assertEqual(False, self._matcher.match(meta, ifilter.to_xpr()))

    def test_or_2_values(self):
        meta = Metadata();
        meta.add_node("/", Group("what"))
        meta.add_node("/what", Attribute("source", "WMO:02606"))
        meta.add_node("/what", Attribute("date", datetime.date(2000, 1, 2)))
        meta.add_node("/what", Attribute("time", datetime.time(12, 5)))
        meta.add_node("/what", Attribute("object", "pvol"))

        v = {"filter_type": "or_filter", 
             "value": [
              {"filter_type": "attribute_filter",  "name": "/what/source", "operation": "=", "value_type": "string", "value": ["WMO:02606"]},
              {"filter_type": "attribute_filter",  "name": "/what/date", "operation": "=", "value_type": "string", "value": ["20000102"]}
             ]
            }

        ifilter = self._manager.from_value(v)

        self.assertEqual(True, self._matcher.match(meta, ifilter.to_xpr()))

    def test_or_2_values_oneTrue(self):
        meta = Metadata();
        meta.add_node("/", Group("what"))
        meta.add_node("/what", Attribute("source", "WMO:02606"))
        meta.add_node("/what", Attribute("date", datetime.date(2000, 1, 2)))
        meta.add_node("/what", Attribute("time", datetime.time(12, 5)))
        meta.add_node("/what", Attribute("object", "pvol"))

        v = {"filter_type": "or_filter", 
             "value": [
              {"filter_type": "attribute_filter",  "name": "/what/source", "operation": "=", "value_type": "string", "value": ["WMO:02606"]},
              {"filter_type": "attribute_filter",  "name": "/what/date", "operation": "=", "value_type": "string", "value": ["20260102"]}
             ]
            }

        ifilter = self._manager.from_value(v)

        self.assertEqual(True, self._matcher.match(meta, ifilter.to_xpr()))

    def test_or_3_values(self):
        meta = Metadata();
        meta.add_node("/", Group("what"))
        meta.add_node("/what", Attribute("source", "WMO:02606"))
        meta.add_node("/what", Attribute("date", datetime.date(2000, 1, 2)))
        meta.add_node("/what", Attribute("time", datetime.time(12, 5)))
        meta.add_node("/what", Attribute("object", "pvol"))

        v = {"filter_type": "or_filter", 
             "value": [
              {"filter_type": "attribute_filter",  "name": "/what/source", "operation": "=", "value_type": "string", "value": ["WMO:02606"]},
              {"filter_type": "attribute_filter",  "name": "/what/date", "operation": "=", "value_type": "string", "value": ["20000102"]},
              {"filter_type": "attribute_filter",  "name": "/what/time", "operation": "=", "value_type": "string", "value": ["120500"]}
             ]
            }

        ifilter = self._manager.from_value(v)

        self.assertEqual(True, self._matcher.match(meta, ifilter.to_xpr()))

    def test_or_3_values_twoFalse(self):
        meta = Metadata();
        meta.add_node("/", Group("what"))
        meta.add_node("/what", Attribute("source", "WMO:02606"))
        meta.add_node("/what", Attribute("date", datetime.date(2000, 1, 2)))
        meta.add_node("/what", Attribute("time", datetime.time(12, 5)))
        meta.add_node("/what", Attribute("object", "pvol"))

        v = {"filter_type": "or_filter", 
             "value": [
              {"filter_type": "attribute_filter",  "name": "/what/source", "operation": "=", "value_type": "string", "value": ["WMO:02606"]},
              {"filter_type": "attribute_filter",  "name": "/what/date", "operation": "=", "value_type": "string", "value": ["20260102"]},
              {"filter_type": "attribute_filter",  "name": "/what/time", "operation": "=", "value_type": "string", "value": ["130500"]}
             ]
            }

        ifilter = self._manager.from_value(v)

        self.assertEqual(True, self._matcher.match(meta, ifilter.to_xpr()))

    def test_or_4_values(self):
        meta = Metadata();
        meta.add_node("/", Group("what"))
        meta.add_node("/what", Attribute("source", "WMO:02606"))
        meta.add_node("/what", Attribute("date", datetime.date(2000, 1, 2)))
        meta.add_node("/what", Attribute("time", datetime.time(12, 5)))
        meta.add_node("/what", Attribute("object", "pvol"))

        v = {"filter_type": "or_filter", 
             "value": [
              {"filter_type": "attribute_filter",  "name": "/what/source", "operation": "=", "value_type": "string", "value": ["WMO:02606"]},
              {"filter_type": "attribute_filter",  "name": "/what/date", "operation": "=", "value_type": "string", "value": ["20000102"]},
              {"filter_type": "attribute_filter",  "name": "/what/time", "operation": "=", "value_type": "string", "value": ["120500"]},
              {"filter_type": "attribute_filter",  "name": "/what/object", "operation": "=", "value_type": "string", "value": ["pvol"]}
             ]
            }

        ifilter = self._manager.from_value(v)

        self.assertEqual(True, self._matcher.match(meta, ifilter.to_xpr()))

    def test_or_4_values_threeFalse(self):
        meta = Metadata();
        meta.add_node("/", Group("what"))
        meta.add_node("/what", Attribute("source", "WMO:02606"))
        meta.add_node("/what", Attribute("date", datetime.date(2000, 1, 2)))
        meta.add_node("/what", Attribute("time", datetime.time(12, 5)))
        meta.add_node("/what", Attribute("object", "pvol"))

        v = {"filter_type": "or_filter", 
             "value": [
              {"filter_type": "attribute_filter",  "name": "/what/source", "operation": "=", "value_type": "string", "value": ["WMO:02606"]},
              {"filter_type": "attribute_filter",  "name": "/what/date", "operation": "=", "value_type": "string", "value": ["20260102"]},
              {"filter_type": "attribute_filter",  "name": "/what/time", "operation": "=", "value_type": "string", "value": ["130500"]},
              {"filter_type": "attribute_filter",  "name": "/what/object", "operation": "=", "value_type": "string", "value": ["scan"]}
             ]
            }

        ifilter = self._manager.from_value(v)

        self.assertEqual(True, self._matcher.match(meta, ifilter.to_xpr()))

    def test_or_4_values_allFalse(self):
        meta = Metadata();
        meta.add_node("/", Group("what"))
        meta.add_node("/what", Attribute("source", "WMO:02606"))
        meta.add_node("/what", Attribute("date", datetime.date(2000, 1, 2)))
        meta.add_node("/what", Attribute("time", datetime.time(12, 5)))
        meta.add_node("/what", Attribute("object", "pvol"))

        v = {"filter_type": "and_filter", 
             "value": [
              {"filter_type": "attribute_filter",  "name": "/what/source", "operation": "=", "value_type": "string", "value": ["WMO:02607"]},
              {"filter_type": "attribute_filter",  "name": "/what/date", "operation": "=", "value_type": "string", "value": ["20260102"]},
              {"filter_type": "attribute_filter",  "name": "/what/time", "operation": "=", "value_type": "string", "value": ["130500"]},
              {"filter_type": "attribute_filter",  "name": "/what/object", "operation": "=", "value_type": "string", "value": ["scan"]}
             ]
            }

        ifilter = self._manager.from_value(v)

        self.assertEqual(False, self._matcher.match(meta, ifilter.to_xpr()))

    def test_notfilter(self):
        meta = Metadata();
        meta.add_node("/", Group("what"))

        v = {"filter_type": "not_filter",
             "value": {
               "filter_type": "attribute_filter", 
               "name": "_bdb/source_name", 
               "operation": "like", 
               "value_type": "string", 
               "value": "se*"
              }
            }
        ifilter = self._manager.from_value(v)

        meta.bdb_source_name = "fipet"
        self.assertEqual(True, self._matcher.match(meta, ifilter.to_xpr()))

        meta.bdb_source_name = "skpet"
        self.assertEqual(True, self._matcher.match(meta, ifilter.to_xpr()))

        meta.bdb_source_name = "s"
        self.assertEqual(True, self._matcher.match(meta, ifilter.to_xpr()))

        meta.bdb_source_name = "sebaa"
        self.assertEqual(False, self._matcher.match(meta, ifilter.to_xpr()))

        meta.bdb_source_name = "sekaa"
        self.assertEqual(False, self._matcher.match(meta, ifilter.to_xpr()))

    def test_bdb_age(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        meta = Metadata();
        meta.add_node("/", Group("what"))
        meta.add_node("/what", Attribute("source", "WMO:02606"))
        meta.add_node("/what", Attribute("date", datetime.date(now.year, now.month, now.day)))
        meta.add_node("/what", Attribute("time", datetime.time(now.hour, now.minute, now.second)))
        meta.add_node("/what", Attribute("object", "pvol"))

        v = {"filter_type": "attribute_filter", "name":"_exchange/what_age", "operation":"<", "value_type":"int","value":10}

        ifilter = self._manager.from_value(v)

        self.assertEqual(True, self._matcher.match(meta, ifilter.to_xpr()))

    def test_bdb_age_too_old(self):
        now = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=30)
        meta = Metadata();
        meta.add_node("/", Group("what"))
        meta.add_node("/what", Attribute("source", "WMO:02606"))
        meta.add_node("/what", Attribute("date", datetime.date(now.year, now.month, now.day)))
        meta.add_node("/what", Attribute("time", datetime.time(now.hour, now.minute, now.second)))
        meta.add_node("/what", Attribute("object", "pvol"))

        v = {"filter_type": "attribute_filter", "name":"_exchange/what_age", "operation":"<", "value_type":"int","value":10}

        ifilter = self._manager.from_value(v)

        self.assertEqual(False, self._matcher.match(meta, ifilter.to_xpr()))