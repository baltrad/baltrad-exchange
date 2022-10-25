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

## Tests baltrad.exchange.naming.namer

## @file
## @author Anders Henja, SMHI
## @date 2021-08-18
import unittest
from baltrad.exchange.naming.namer import metadata_namer
from baltrad.bdbcommon import oh5
from baltrad.bdbcommon.oh5.node import Attribute, Group

import datetime

class test_namer(unittest.TestCase):
    def test_replace_attribute(self):
        meta = oh5.Metadata()
        meta.add_node("/", Group("what"))
        meta.add_node("/what", Attribute("object", "PVOL"))

        namer = metadata_namer("${/what/object}")
        
        assert("PVOL" == namer.name(meta))

    def test_suboperation_lower(self):
        meta = oh5.Metadata()
        meta.add_node("/", Group("what"))
        meta.add_node("/what", Attribute("object", "PVOL"))

        namer = metadata_namer("${/what/object}.tolower()")
        
        assert("pvol" == namer.name(meta))

    def test_suboperation_upper(self):
        meta = oh5.Metadata()
        meta.add_node("/", Group("what"))
        meta.add_node("/what", Attribute("object", "pvol"))

        namer = metadata_namer("${/what/object}.toupper()")
        
        assert("PVOL" == namer.name(meta))

    def test_suboperation_substring(self):
        meta = oh5.Metadata()
        meta.add_node("/", Group("what"))
        meta.add_node("/what", Attribute("object", "PVOL"))

        namer = metadata_namer("${/what/object}.substring(1,2)")
        
        assert("VO" == namer.name(meta))
        
    def test_suboperation_trim(self):
        meta = oh5.Metadata()
        meta.add_node("/", Group("what"))
        meta.add_node("/what", Attribute("object", " PVOL "))

        namer = metadata_namer("${/what/object}.trim()")
        
        assert("PVOL" == namer.name(meta))

    def test_suboperation_rtrim(self):
        meta = oh5.Metadata()
        meta.add_node("/", Group("what"))
        meta.add_node("/what", Attribute("object", " PVOL "))

        namer = metadata_namer("${/what/object}.rtrim()")
        
        assert(" PVOL" == namer.name(meta))

    def test_suboperation_ltrim(self):
        meta = oh5.Metadata()
        meta.add_node("/", Group("what"))
        meta.add_node("/what", Attribute("object", " PVOL "))

        namer = metadata_namer("${/what/object}.ltrim()")
        
        assert("PVOL " == namer.name(meta))

    def test_suboperation_ltrim_rtrim(self):
        meta = oh5.Metadata()
        meta.add_node("/", Group("what"))
        meta.add_node("/what", Attribute("object", " PVOL "))

        namer = metadata_namer("${/what/object}.ltrim().rtrim()")
        
        assert("PVOL" == namer.name(meta))

    
    def test_complex_name(self):
        meta = oh5.Metadata()
        meta.add_node("/", Group("what"))
        meta.add_node("/what", Attribute("object", "PVOL"))
        meta.add_node("/what", Attribute("date", datetime.date(2000, 1, 1)))
        meta.add_node("/what", Attribute("time", datetime.time(12, 0)))
        meta.add_node("/", Group("dataset1"))
        meta.add_node("/dataset1", Group("data1"))
        meta.add_node("/dataset1/data1", Group("what"))
        meta.add_node("/dataset1/data1/what", Attribute("quantity", "DBZH"))
        meta.bdb_source = "NOD:setst,WMO:12345,RAD:SE52,WIGOS:12345"
        meta.what_source = "NOD:setst,WMO:12345,RAD:SE52"
        meta.bdb_source_name = "setst"

        namer = metadata_namer("${_baltrad/datetime:%Y/%m/%d/%H/%M}.interval_u(15)/${_bdb/source_name}_${/what/date}T${/what/time}.interval_l(15)Z_${/what/object}.tolower().toupper(0)_${/dataset1/data1/what/quantity}_${_baltrad/datetime:%Y%m%d%H%M}.interval_u(15).h5")
        
        assert("2000/01/01/12/15/setst_20000101T120000Z_Pvol_DBZH_200001011215.h5" == namer.name(meta))

    def test_complex_name_bdb_source_NOD(self):
        meta = oh5.Metadata()
        meta.add_node("/", Group("what"))
        meta.add_node("/what", Attribute("object", "PVOL"))
        meta.add_node("/what", Attribute("date", datetime.date(2000, 1, 1)))
        meta.add_node("/what", Attribute("time", datetime.time(12, 0)))
        meta.add_node("/", Group("dataset1"))
        meta.add_node("/dataset1", Group("data1"))
        meta.add_node("/dataset1/data1", Group("what"))
        meta.add_node("/dataset1/data1/what", Attribute("quantity", "DBZH"))
        meta.bdb_source = "NOD:setst,WMO:12345,RAD:SE52,WIGOS:12345"
        meta.what_source = "NOD:setst,WMO:12345,RAD:SE52"
        meta.bdb_source_name = "setst"

        namer = metadata_namer("${_baltrad/datetime:%Y/%m/%d/%H/%M}.interval_u(15)/${_bdb/source:NOD}_${/what/date}T${/what/time}.interval_l(15)Z_${/what/object}.tolower().toupper(0)_${/dataset1/data1/what/quantity}_${_baltrad/datetime:%Y%m%d%H%M}.interval_u(15).h5")
        
        assert("2000/01/01/12/15/setst_20000101T120000Z_Pvol_DBZH_200001011215.h5" == namer.name(meta))

    def test_complex_name_what_source_WIGOS(self):
        meta = oh5.Metadata()
        meta.add_node("/", Group("what"))
        meta.add_node("/what", Attribute("object", "PVOL"))
        meta.add_node("/what", Attribute("date", datetime.date(2000, 1, 1)))
        meta.add_node("/what", Attribute("time", datetime.time(12, 0)))
        meta.add_node("/", Group("dataset1"))
        meta.add_node("/dataset1", Group("data1"))
        meta.add_node("/dataset1/data1", Group("what"))
        meta.add_node("/dataset1/data1/what", Attribute("quantity", "DBZH"))
        meta.bdb_source = "NOD:setst,WMO:12345,RAD:SE52,WIGOS:12345"
        meta.what_source = "NOD:setst,WMO:12345,RAD:SE52"
        meta.bdb_source_name = "setst"

        namer = metadata_namer("${_baltrad/datetime:%Y/%m/%d/%H/%M}.interval_u(15)/${what/source:WIGOS}_${/what/date}T${/what/time}.interval_l(15)Z_${/what/object}.tolower().toupper(0)_${/dataset1/data1/what/quantity}_${_baltrad/datetime:%Y%m%d%H%M}.interval_u(15).h5")

        assert("2000/01/01/12/15/undefined_20000101T120000Z_Pvol_DBZH_200001011215.h5" == namer.name(meta))
  