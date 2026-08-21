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
## @date 2023-11-27
from __future__ import absolute_import

import unittest
from unittest.mock import MagicMock, patch
import logging, os, sqlite3
from datetime import datetime
from tempfile import NamedTemporaryFile
from bexchange.db import sqldatabase

logger = logging.getLogger("test_sqldatabase")

class TestSqlDatabase(unittest.TestCase):
    def setUp(self):
        self._database = sqldatabase.SqlAlchemyDatabase("sqlite:///:memory:")
    
    def tearDown(self):
        self._database = None

    def test_find_statistics(self):
        self._database.add(sqldatabase.statistics("abc", "myorigin", "sekkr", 1, datetime.now()))
        self._database.add(sqldatabase.statistics("abcd", "myotherorigin", "sella", 2, datetime.now()))

        entries = self._database.find_statistics("abc", ["myorigin"], ["sekkr"])
        self.assertEqual(1, len(entries))
        self.assertEqual("abc", entries[0].spid)
        self.assertEqual("myorigin", entries[0].origin)
        self.assertEqual("sekkr", entries[0].source)

    def test_find_statistics_multipleSources(self):
        self._database.add(sqldatabase.statistics("abc", "myorigin", "sekkr", 1, datetime.now()))
        self._database.add(sqldatabase.statistics("abc", "myorigin", "sella", 1, datetime.now()))
        self._database.add(sqldatabase.statistics("abcd", "myotherorigin", "sella", 2, datetime.now()))

        entries = self._database.find_statistics("abc", ["myorigin"], ["sekkr", "sella"])
        self.assertEqual(2, len(entries))
        if entries[0].source == "sella":
            tmp = entries[0]
            entries[0] = entries[1]
            entries[1] = tmp
        self.assertEqual("abc", entries[0].spid)
        self.assertEqual("myorigin", entries[0].origin)
        self.assertEqual("sekkr", entries[0].source)
        self.assertEqual("abc", entries[1].spid)
        self.assertEqual("myorigin", entries[1].origin)
        self.assertEqual("sella", entries[1].source)

    def test_add_statentry(self):
        self._database.add(sqldatabase.statentry("abcd", "myorigin", "sella", '123123', datetime.now(), 10, None, 123, datetime(2023,11,27,1,15,0), 'SCAN', 0.5))
        self._database.add(sqldatabase.statentry("abcd", "myorigin", "sella", '123123', datetime.now(), 10, None, 123, datetime(2023,11,27,1,15,0), 'SCAN', 1.0))
        self._database.add(sqldatabase.statentry("abcd", "myorigin", "sella", '123123', datetime.now(), 10, None, 123, datetime(2023,11,27,1,15,0), 'PVOL', None))

        with self._database.get_session() as s:
            entries = s.query(sqldatabase.statentry).all()
            self.assertEqual(3, len(entries))
            self.assertEqual("abcd", entries[0].spid)
            self.assertEqual("myorigin", entries[0].origin)
            self.assertEqual("sella", entries[0].source)
            self.assertEqual("123123", entries[0].hashid)
            self.assertEqual(10, entries[0].optime)
            self.assertEqual(datetime(2023,11,27,1,15,0), entries[0].datetime)
            self.assertEqual("SCAN", entries[0].object_type)
            self.assertAlmostEqual(0.5, entries[0].elevation_angle)

            self.assertEqual("abcd", entries[1].spid)
            self.assertEqual("myorigin", entries[1].origin)
            self.assertEqual("sella", entries[1].source)
            self.assertEqual("123123", entries[1].hashid)
            self.assertEqual(10, entries[1].optime)
            self.assertEqual(datetime(2023,11,27,1,15,0), entries[1].datetime)
            self.assertEqual("SCAN", entries[1].object_type)
            self.assertAlmostEqual(1.0, entries[1].elevation_angle)

            self.assertEqual("abcd", entries[2].spid)
            self.assertEqual("myorigin", entries[2].origin)
            self.assertEqual("sella", entries[2].source)
            self.assertEqual("123123", entries[2].hashid)
            self.assertEqual(10, entries[2].optime)
            self.assertEqual(datetime(2023,11,27,1,15,0), entries[1].datetime)
            self.assertEqual("PVOL", entries[2].object_type)
            self.assertEqual(None, entries[2].elevation_angle)

    def test_find_statentries_filter_delay(self):
        self._database.add(sqldatabase.statentry("abcd", "myorigin", "sella", '123123', datetime(2023,11,27,1,15,31), 10, None, 31, datetime(2023,11,27,1,15,0), 'SCAN', 0.5))
        self._database.add(sqldatabase.statentry("abcd", "myorigin", "sella", '123124', datetime(2023,11,27,1,15,32), 10, None, 32, datetime(2023,11,27,1,15,0), 'SCAN', 1.0))

        entries = self._database.find_statentries("abcd", [], [], hashid=None, filters=[["delay",">", 31]], object_type=None)
        self.assertEqual(1, len(entries))

        entries = self._database.find_statentries("abcd", [], [], hashid=None, filters=[["delay",">", 32]], object_type=None)
        self.assertEqual(0, len(entries))

        entries = self._database.find_statentries("abcd", [], [], hashid=None, filters=[["delay","<=", 32]], object_type=None)
        self.assertEqual(2, len(entries))


    def test_find_statentries_filter_delay_and_datetime(self):
        self._database.add(sqldatabase.statentry("abcd", "myorigin", "sella", '123123', datetime(2023,11,27,1,15,31), 10, None, 31, datetime(2023,11,27,1,15,0), 'SCAN', 0.5))
        self._database.add(sqldatabase.statentry("abcd", "myorigin", "sella", '123124', datetime(2023,11,27,1,15,32), 10, None, 32, datetime(2023,11,27,1,15,0), 'SCAN', 1.0))
        self._database.add(sqldatabase.statentry("abcd", "myorigin", "sella", '123124', datetime(2023,11,27,1,20,2), 10, None, 2, datetime(2023,11,27,1,20,0), 'SCAN', 1.0))

        entries = self._database.find_statentries("abcd", [], [], hashid=None, filters=[["delay","<", 33], ["datetime",">", datetime(2023,11,27,1,15,0)]], object_type=None)
        self.assertEqual(1, len(entries))

        entries = self._database.find_statentries("abcd", [], [], hashid=None, filters=[["delay","<", 30], ["datetime",">", datetime(2023,11,27,1,15,0)]], object_type=None)
        self.assertEqual(1, len(entries))

        entries = self._database.find_statentries("abcd", [], [], hashid=None, filters=[["delay","<", 2], ["datetime",">", datetime(2023,11,27,1,15,0)]], object_type=None)
        self.assertEqual(0, len(entries))

    def test_force_sqlite_wal_sets_pragma(self):
        conn = sqlite3.connect(":memory:")
        con_record = MagicMock()

        sqldatabase.force_sqlite_wal(conn, con_record)

        conn.close()
        with NamedTemporaryFile(suffix=".db") as f:
            fileconn = sqlite3.connect(f.name)
            sqldatabase.force_sqlite_wal(fileconn, con_record)
            self.assertEqual("wal", fileconn.execute("pragma journal_mode").fetchone()[0])
            fileconn.close()

    def test_force_sqlite_wal_ignores_non_sqlite_connection(self):
        dbapi_con = MagicMock()
        con_record = MagicMock()

        sqldatabase.force_sqlite_wal(dbapi_con, con_record)

        dbapi_con.execute.assert_not_called()

    def test_force_sqlite_synchronous_normal_sets_pragma(self):
        conn = sqlite3.connect(":memory:")
        con_record = MagicMock()

        sqldatabase.force_sqlite_synchronous_normal(conn, con_record)

        self.assertEqual(1, conn.execute("pragma synchronous").fetchone()[0]) # 1 == NORMAL
        conn.close()

    def test_force_sqlite_synchronous_normal_ignores_non_sqlite_connection(self):
        dbapi_con = MagicMock()
        con_record = MagicMock()

        sqldatabase.force_sqlite_synchronous_normal(dbapi_con, con_record)

        dbapi_con.execute.assert_not_called()

    def test_sqlalchemydatabase_wires_up_sqlite_pragma_listeners(self):
        # Verifies that SqlAlchemyDatabase registers all three pragma listeners on the
        # sqlalchemy engine's "connect" event when running against sqlite.
        with patch("bexchange.db.sqldatabase.event.listen") as listen_mock:
            sqldatabase.SqlAlchemyDatabase("sqlite:///:memory:")

        registered_listeners = [call.args[2] for call in listen_mock.call_args_list]
        self.assertIn(sqldatabase.force_sqlite_foreign_keys, registered_listeners)
        self.assertIn(sqldatabase.force_sqlite_wal, registered_listeners)
        self.assertIn(sqldatabase.force_sqlite_synchronous_normal, registered_listeners)

    def test_database_connection_has_wal_synchronous_normal_and_foreign_keys(self):
        with self._database._engine.connect() as c:
            self.assertEqual(1, c.exec_driver_sql("pragma synchronous").scalar())
            self.assertEqual(1, c.exec_driver_sql("pragma foreign_keys").scalar())

