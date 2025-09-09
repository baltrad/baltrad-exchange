# Copyright (C) 2025- Swedish Meteorological and Hydrological Institute (SMHI)
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

## Tests bexchange.net.senders

## @file
## @author Anders Henja, SMHI
## @date 2025-09-09
import unittest
from unittest import mock
from unittest.mock import patch
from bexchange.naming.namer import metadata_namer, opera_filename_namer
from bexchange.net import senders
import bexchange.net.sftpclient
from baltrad.bdbcommon import oh5
from baltrad.bdbcommon.oh5 import Source
from baltrad.bdbcommon.oh5.node import Attribute, Group

from unittest.mock import MagicMock

import datetime, os

THIS_DIR=os.path.dirname(__file__)

class test_senders(unittest.TestCase):
    def create_meta(self):
        meta = oh5.Metadata()
        meta.source_parent = Source("se", {"CCCC":"ESWI"})
        meta.bdb_source = "NOD:sella,RAD:SE41" 
        meta.what_source = "NOD:sella,RAD:SE41"
        meta.bdb_source_name = "sella"
        meta.add_node("/", Group("what"))
        meta.add_node("/what", Attribute("date", datetime.date(2025, 9, 9)))
        meta.add_node("/what", Attribute("time", datetime.time(12, 0)))
        return meta

    def test_sftp_sender_invalid_temppattern_1(self):
        backend = MagicMock()
        meta = self.create_meta()
        arguments = {
            "confirm_upload":False,
            "uri":"sftp://username:password@localhost:1234/data/${_baltrad/source:NOD}.h5",
            "tmppattern":["^"]
        }
        try:
            sender = senders.sftp_sender(backend, "aid", arguments)
            self.fail("Expected ValueError")
        except ValueError:
            pass

    def test_sftp_sender_invalid_temppattern_3(self):
        backend = MagicMock()
        meta = self.create_meta()
        arguments = {
            "confirm_upload":False,
            "uri":"sftp://username:password@localhost:1234/data/${_baltrad/source:NOD}.h5",
            "tmppattern":["^", ".", ".h5$"]
        }
        try:
            sender = senders.sftp_sender(backend, "aid", arguments)
            self.fail("Expected ValueError")
        except ValueError:
            pass

    def test_sftp_sender_tmppattern(self):
        backend = MagicMock()
        meta = self.create_meta()
        arguments = {
            "confirm_upload":False,
            "uri":"sftp://username:password@localhost:1234/data/${_baltrad/source:NOD}.h5",
            "tmppattern":["^","."]
        }
        sender = senders.sftp_sender(backend, "aid", arguments)
        sftpobj = MagicMock()
        sender.client = MagicMock(return_value=sftpobj)

        # Run test
        sender.send("thisfile.h5", meta)

        # Verify
        sftpobj.makedirs.assert_called()
        sftpobj.chdir.assert_called_with("data")
        sftpobj.put.assert_called_with("thisfile.h5", ".sella.h5", confirm=False)
        sftpobj.rename.assert_called_with(".sella.h5", "sella.h5")

    def test_sftp_sender_tmppattern_two_sets(self):
        backend = MagicMock()
        meta = self.create_meta()
        arguments = {
            "confirm_upload":False,
            "uri":"sftp://username:password@localhost:1234/data/${_baltrad/source:NOD}.h5",
            "tmppattern":["^",".", ".h5$", ".tmp"]
        }
        sender = senders.sftp_sender(backend, "aid", arguments)
        sftpobj = MagicMock()
        sender.client = MagicMock(return_value=sftpobj)

        # Run test
        sender.send("thisfile.h5", meta)

        # Verify
        sftpobj.makedirs.assert_called()
        sftpobj.chdir.assert_called_with("data")
        sftpobj.put.assert_called_with("thisfile.h5", ".sella.tmp", confirm=False)
        sftpobj.rename.assert_called_with(".sella.tmp", "sella.h5")

    def test_sftp_sender_no_tmppattern(self):
        backend = MagicMock()
        meta = self.create_meta()
        arguments = {
            "confirm_upload":False,
            "uri":"sftp://username:password@localhost:1234/data/${_baltrad/source:NOD}.h5"
        }
        sender = senders.sftp_sender(backend, "aid", arguments)
        sftpobj = MagicMock()
        sender.client = MagicMock(return_value=sftpobj)

        # Run test
        sender.send("thisfile.h5", meta)

        # Verify
        sftpobj.makedirs.assert_called()
        sftpobj.chdir.assert_called_with("data")
        sftpobj.put.assert_called_with("thisfile.h5", "sella.h5", confirm=False)

    def test_sftp_sender_no_makedirs(self):
        backend = MagicMock()
        meta = self.create_meta()
        arguments = {
            "create_missing_directories":False,
            "confirm_upload":False,
            "uri":"sftp://username:password@localhost:1234/data/${_baltrad/source:NOD}.h5"
        }
        sender = senders.sftp_sender(backend, "aid", arguments)
        sftpobj = MagicMock()
        sender.client = MagicMock(return_value=sftpobj)

        # Run test
        sender.send("thisfile.h5", meta)

        # Verify
        sftpobj.makedirs.assert_not_called()
        sftpobj.chdir.assert_called_with("data")
        sftpobj.put.assert_called_with("thisfile.h5", "sella.h5", confirm=False)
