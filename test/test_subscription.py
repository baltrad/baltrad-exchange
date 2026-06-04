# Copyright (C) 2026- Swedish Meteorological and Hydrological Institute (SMHI)
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

## Tests bexchange.server.subscription

## @file
## @author Anders Henja, SMHI
## @date 2026-05-04
from __future__ import absolute_import

import unittest
import pytest
from unittest.mock import MagicMock, patch, call
from bexchange.server import subscription
from baltrad.bdbcommon.oh5.meta import Metadata

import os

class TestSourceBarrier:
    def test_is_allowed_blocked_exists(self):
        classUnderTest = subscription.source_barrier("block", "dir", "/tmp/blocked")
        classUnderTest.exists = MagicMock(return_value=True)   # When blocked, then entry must not exist
        assert(False == classUnderTest.is_allowed("seabc"))

    def test_is_allowed_blocked_not_exists(self):
        classUnderTest = subscription.source_barrier("block", "dir", "/tmp/blocked")
        classUnderTest.exists = MagicMock(return_value=False)   # When blocked, then entry must not exist
        assert(True == classUnderTest.is_allowed("seabc"))

    def test_is_allowed_allowed_exists(self):
        classUnderTest = subscription.source_barrier("allow", "dir", "/tmp/blocked")
        classUnderTest.exists = MagicMock(return_value=True)   # When allowed, then entry must exist
        assert(True == classUnderTest.is_allowed("seabc"))

    def test_is_allowed_allowed_not_exists(self):
        classUnderTest = subscription.source_barrier("allow", "dir", "/tmp/blocked")
        classUnderTest.exists = MagicMock(return_value=False)   # When allowed, then entry must exist
        assert(False == classUnderTest.is_allowed("seabc"))

    def test_exists_list(self):
        classUnderTest = subscription.source_barrier("block", "list", ["sella","sekrn","seang"])
        assert(True == classUnderTest.exists("sella"))
        assert(True == classUnderTest.exists("sekrn"))
        assert(True == classUnderTest.exists("seang"))
        assert(False == classUnderTest.exists("seangx"))
        assert(False == classUnderTest.exists("sepel"))
        assert(False == classUnderTest.exists(None))

    def test_exists_dir(self):
        classUnderTest = subscription.source_barrier("block", "dir", "/tmp/blocked")
        with patch('os.path.exists') as mock_exists:
            mock_exists.side_effect = [True,True,True,False,False,False]
            assert(True == classUnderTest.exists("sella"))
            assert(True == classUnderTest.exists("sekrn"))
            assert(True == classUnderTest.exists("seang"))
            assert(False == classUnderTest.exists("seangx"))
            assert(False == classUnderTest.exists("sepel"))
            assert(False == classUnderTest.exists(None))

            mock_exists.assert_has_calls([
                call("/tmp/blocked/sella"),
                call("/tmp/blocked/sekrn"),
                call("/tmp/blocked/seang"),
                call("/tmp/blocked/seangx"),
                call("/tmp/blocked/sepel"),
                call("/tmp/blocked/None")
            ]) 