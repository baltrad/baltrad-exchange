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

import pytest
from bexchange.matching import filters
from bexchange.server import sqlbackend

from baltrad.bdbcommon import oh5, expr
from baltrad.bdbcommon.oh5.meta import Source
from baltrad.bdbcommon.oh5.node import Attribute, Group

import os

THIS_DIR=os.path.dirname(__file__)

class TestSourceManager:
    SOURCE_FIXTURE=f"{THIS_DIR}/fixtures/odim_source.xml"
    @pytest.fixture(autouse=True)
    def setup(self):
        self.sourcemanager = sqlbackend.SqlAlchemySourceManager("sqlite://")
    
        yield

        self.sourcemanager = None

    def add_fixture_sources(self):
        with open(self.SOURCE_FIXTURE) as f:
            self.sourcemanager.add_sources(oh5.Source.from_rave_xml(f.read()))

    def test_get_source_without_parent(self):
        self.add_fixture_sources()
        
        meta = oh5.Metadata()
        meta.add_node("/", Group("what"))
        meta.bdb_source = "NOD:sella"
        meta.what_source = "NOD:sella"
        meta.bdb_source_name = "sella"
        source = self.sourcemanager.get_source(meta)
        assert("sella"==source["NOD"])
        assert("SE41"==source["RAD"])
        assert("02092"==source["WMO"])
        assert("se"==source.parent)
        assert(source.parent_object is None)

    def test_get_source_with_parent(self):
        self.add_fixture_sources()
        
        meta = oh5.Metadata()
        meta.add_node("/", Group("what"))
        meta.bdb_source = "NOD:sella"
        meta.what_source = "NOD:sella"
        meta.bdb_source_name = "sella"

        source = self.sourcemanager.get_source(meta, True)
        assert("sella"==source["NOD"])
        assert("SE41"==source["RAD"])
        assert("02092"==source["WMO"])
        assert("se"==source.parent)
        assert("ESWI"==source.parent_object["CCCC"])
        assert("82"==source.parent_object["ORG"])

    def test_get_parent_source(self):
        self.add_fixture_sources()

        source = self.sourcemanager.get_parent_source("se")
        assert("se"==source.name)
        assert("ESWI"==source["CCCC"])
        assert("82"==source["ORG"])
