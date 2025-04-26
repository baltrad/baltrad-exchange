# Copyright (C) 2023- Swedish Meteorological and Hydrological Institute (SMHI)
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

## Tests bexchange.db

## @file
## @author Anders Henja, SMHI
## @date 2023-12-04
from __future__ import absolute_import

import unittest
from unittest.mock import MagicMock, ANY
import datetime, json, logging
from tempfile import NamedTemporaryFile
from bexchange.statistics import statistics

from baltrad.bdbcommon.oh5.meta import Metadata
from baltrad.bdbcommon.oh5.node import Attribute, Group

logger = logging.getLogger("test_statistics")

class test_statistics(unittest.TestCase):
    def setUp(self):
        self._sqldatabase = MagicMock()
        self._statistics_mgr = statistics.statistics_manager(self._sqldatabase)
        logging.getLogger("bexchange.statistics.statistics").disabled = True

    def tearDown(self):
        self._statistics_mgr = None
        self._sqldatabase = None
        logging.getLogger("bexchange.statistics.statistics").disabled = False

    def test_list_statistic_ids(self):
        self._sqldatabase.list_statistic_ids = MagicMock(return_value=["id_1","id_2"])
        self._sqldatabase.list_statentry_ids = MagicMock(return_value=["id_3","id_4"])

        result = json.loads(self._statistics_mgr.list_statistic_ids("abc"))
        self.assertEqual(4, len(result))
        self.assertEqual("id_1", result[0]["spid"])
        self.assertEqual(True, result[0]["totals"])        
        self.assertEqual("id_2", result[1]["spid"])
        self.assertEqual(True, result[1]["totals"])        
        self.assertEqual("id_3", result[2]["spid"])
        self.assertEqual(False, result[2]["totals"])        
        self.assertEqual("id_4", result[3]["spid"])
        self.assertEqual(False, result[3]["totals"])        

    def test_parse_filter_1(self):
        result = self._statistics_mgr.parse_filter('datetime<202301011000')
        self.assertEqual(1, len(result))
        self.assertEqual("datetime", result[0][0])
        self.assertEqual("<", result[0][1])
        self.assertEqual(datetime.datetime(2023,1,1,10,0), result[0][2])

        result = self._statistics_mgr.parse_filter('datetime<=202301011000')
        self.assertEqual(1, len(result))
        self.assertEqual("datetime", result[0][0])
        self.assertEqual("<=", result[0][1])
        self.assertEqual(datetime.datetime(2023,1,1,10,0), result[0][2])

        result = self._statistics_mgr.parse_filter('  datetime  <=  202301011000  ')
        self.assertEqual(1, len(result))
        self.assertEqual("datetime", result[0][0])
        self.assertEqual("<=", result[0][1])
        self.assertEqual(datetime.datetime(2023,1,1,10,0), result[0][2])

    def test_parse_filter_combination(self):
        result = self._statistics_mgr.parse_filter('datetime>=202301011000&&datetime<202301011000')
        self.assertEqual(2, len(result))
        self.assertEqual("datetime", result[0][0])
        self.assertEqual(">=", result[0][1])
        self.assertEqual(datetime.datetime(2023,1,1,10,0), result[0][2])

        self.assertEqual("datetime", result[1][0])
        self.assertEqual("<", result[1][1])
        self.assertEqual(datetime.datetime(2023,1,1,10,0), result[1][2])

        result = self._statistics_mgr.parse_filter('datetime>202301011000&&datetime<=202301011000')
        self.assertEqual(2, len(result))
        self.assertEqual("datetime", result[0][0])
        self.assertEqual(">", result[0][1])
        self.assertEqual(datetime.datetime(2023,1,1,10,0), result[0][2])

        self.assertEqual("datetime", result[1][0])
        self.assertEqual("<=", result[1][1])
        self.assertEqual(datetime.datetime(2023,1,1,10,0), result[1][2])

        result = self._statistics_mgr.parse_filter('  datetime >= 202301011000 && datetime < 202301011000  ')
        self.assertEqual(2, len(result))
        self.assertEqual("datetime", result[0][0])
        self.assertEqual(">=", result[0][1])
        self.assertEqual(datetime.datetime(2023,1,1,10,0), result[0][2])

        self.assertEqual("datetime", result[1][0])
        self.assertEqual("<", result[1][1])
        self.assertEqual(datetime.datetime(2023,1,1,10,0), result[1][2])

    def create_meta(self, what_object="PVOL", nod="senod", d=datetime.date(2000, 1, 2), t=datetime.time(12, 5), mdhash="123"):
        meta = Metadata();
        meta.bdb_source_name=nod
        meta.bdb_metadata_hash=mdhash
        meta.add_node("/", Group("what"))
        meta.add_node("/what", Attribute("source", "NOD:%s"%nod))
        meta.add_node("/what", Attribute("date", d))
        meta.add_node("/what", Attribute("time", t))
        meta.add_node("/what", Attribute("object", what_object))
        return meta        

    def test_increment_noop(self):
        spid = "test-id"
        origin = "origin"
        meta = self.create_meta("PVOL", "senod")

        self._statistics_mgr.increment(spid, origin, meta, save_post=False, increment_counter=False, optime=0, optime_info=None)

        assert not self._sqldatabase.increment_statistics.called
        assert not self._sqldatabase.add.called

    def test_increment_increment_ctr(self):
        spid = "test-id"
        origin = "origin"
        meta = self.create_meta("PVOL", "senod")

        self._statistics_mgr.increment(spid, origin, meta, save_post=False, increment_counter=True, optime=0, optime_info=None)

        self._sqldatabase.increment_statistics.assert_called_with(spid, origin, "senod")

    def test_increment_increment_ctr_exception(self):
        spid = "test-id"
        origin = "origin"
        meta = self.create_meta("PVOL", "senod")

        self._sqldatabase.increment_statistics = MagicMock(side_effect=Exception("an error"))

        self._statistics_mgr.increment(spid, origin, meta, save_post=False, increment_counter=True, optime=0, optime_info=None)

    def test_increment_save_post(self):
        spid = "test-id"
        origin = "origin"
        op_time = 5
        optime_info = None
        dt = datetime.datetime(2024,4,10,10,0,0, tzinfo=datetime.timezone.utc)
        meta = self.create_meta("PVOL", "senod", dt.date(), dt.time(), "123")

        self._statistics_mgr.increment(spid, origin, meta, save_post=True, increment_counter=False, optime=op_time, optime_info=optime_info)

        assert self._sqldatabase.add.called
        statentry = self._sqldatabase.method_calls[0].args[0]
        self.assertEqual(spid, statentry.spid)
        self.assertEqual(origin, statentry.origin)
        self.assertEqual("123", statentry.hashid)
        self.assertTrue(isinstance(statentry.entrytime, datetime.datetime))
        self.assertEqual(op_time, statentry.optime)
        self.assertEqual("PVOL", statentry.object_type)
        self.assertEqual(None, statentry.elevation_angle)

    def test_increment_save_post_exception(self):
        spid = "test-id"
        origin = "origin"
        op_time = 5
        optime_info = None
        dt = datetime.datetime(2024,4,10,10,0,0, tzinfo=datetime.timezone.utc)
        meta = self.create_meta("PVOL", "senod", dt.date(), dt.time(), "123")

        self._sqldatabase.add = MagicMock(side_effect=Exception("an error"))

        self._statistics_mgr.increment(spid, origin, meta, save_post=True, increment_counter=False, optime=op_time, optime_info=optime_info)

        assert self._sqldatabase.add.called