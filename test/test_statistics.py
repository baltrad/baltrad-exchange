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
from unittest.mock import MagicMock
import logging, os, json
from datetime import datetime
from tempfile import NamedTemporaryFile
from bexchange.statistics import statistics

logger = logging.getLogger("test_statistics")

class test_statistics(unittest.TestCase):
    def setUp(self):
        self._dbmgr = MagicMock()
        self._statistics_mgr = statistics.statistics_manager(self._dbmgr)
    
    def tearDown(self):
        self._statistics_mgr = None
        self._dbmgr = None

    def test_list_statistic_ids(self):
        self._dbmgr.list_statistic_ids = MagicMock(return_value=["id_1","id_2"])
        self._dbmgr.list_statentry_ids = MagicMock(return_value=["id_3","id_4"])

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
        self.assertEqual(datetime(2023,1,1,10,0), result[0][2])

        result = self._statistics_mgr.parse_filter('datetime<=202301011000')
        self.assertEqual(1, len(result))
        self.assertEqual("datetime", result[0][0])
        self.assertEqual("<=", result[0][1])
        self.assertEqual(datetime(2023,1,1,10,0), result[0][2])

        result = self._statistics_mgr.parse_filter('  datetime  <=  202301011000  ')
        self.assertEqual(1, len(result))
        self.assertEqual("datetime", result[0][0])
        self.assertEqual("<=", result[0][1])
        self.assertEqual(datetime(2023,1,1,10,0), result[0][2])

    def test_parse_filter_combination(self):
        result = self._statistics_mgr.parse_filter('datetime>=202301011000&&datetime<202301011000')
        self.assertEqual(2, len(result))
        self.assertEqual("datetime", result[0][0])
        self.assertEqual(">=", result[0][1])
        self.assertEqual(datetime(2023,1,1,10,0), result[0][2])

        self.assertEqual("datetime", result[1][0])
        self.assertEqual("<", result[1][1])
        self.assertEqual(datetime(2023,1,1,10,0), result[1][2])

        result = self._statistics_mgr.parse_filter('datetime>202301011000&&datetime<=202301011000')
        self.assertEqual(2, len(result))
        self.assertEqual("datetime", result[0][0])
        self.assertEqual(">", result[0][1])
        self.assertEqual(datetime(2023,1,1,10,0), result[0][2])

        self.assertEqual("datetime", result[1][0])
        self.assertEqual("<=", result[1][1])
        self.assertEqual(datetime(2023,1,1,10,0), result[1][2])

        result = self._statistics_mgr.parse_filter('  datetime >= 202301011000 && datetime < 202301011000  ')
        self.assertEqual(2, len(result))
        self.assertEqual("datetime", result[0][0])
        self.assertEqual(">=", result[0][1])
        self.assertEqual(datetime(2023,1,1,10,0), result[0][2])

        self.assertEqual("datetime", result[1][0])
        self.assertEqual("<", result[1][1])
        self.assertEqual(datetime(2023,1,1,10,0), result[1][2])
