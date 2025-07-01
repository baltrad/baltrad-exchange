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
from bexchange.naming.namer import metadata_namer, opera_filename_namer
from baltrad.bdbcommon import oh5
from baltrad.bdbcommon.oh5 import Source
from baltrad.bdbcommon.oh5.node import Attribute, Group

import datetime, os

THIS_DIR=os.path.dirname(__file__)

class test_namer(unittest.TestCase):
    NAMER_CONFIG_FILENAME=f"{THIS_DIR}/fixtures/namer_config.json"
    FIXTURE_NAMER_PROPERTY_FILE=f"{THIS_DIR}/fixtures/namer.properties"
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

        namer = metadata_namer("${_baltrad/datetime:%Y/%m/%d/%H/%M}.interval_u(15)/${_baltrad/source_name}_${/what/date}T${/what/time}.interval_l(15)Z_${/what/object}.tolower().toupper(0)_${/dataset1/data1/what/quantity}_${_baltrad/datetime:%Y%m%d%H%M}.interval_u(15).h5")
        assert("2000/01/01/12/15/setst_20000101T120000Z_Pvol_DBZH_200001011215.h5" == namer.name(meta))

    def test_complex_name_2(self):
        meta = oh5.Metadata()
        meta.add_node("/", Group("what"))
        meta.add_node("/what", Attribute("object", "PVOL"))
        meta.add_node("/what", Attribute("date", datetime.date(2000, 1, 1)))
        meta.add_node("/what", Attribute("time", datetime.time(12, 4)))
        meta.add_node("/", Group("dataset1"))
        meta.add_node("/dataset1", Group("data1"))
        meta.add_node("/dataset1/data1", Group("what"))
        meta.add_node("/dataset1/data1/what", Attribute("quantity", "DBZH"))
        meta.bdb_source = "NOD:setst,WMO:12345,RAD:SE52,WIGOS:12345"
        meta.what_source = "NOD:setst,WMO:12345,RAD:SE52"
        meta.bdb_source_name = "setst"

        namer = metadata_namer("${_baltrad/datetime:%Y/%m/%d/%H/%M}.interval_l(15)/${_baltrad/source_name}_${/what/date}T${/what/time}.interval_l(15)Z_${/what/object}.tolower().toupper(0)_${/dataset1/data1/what/quantity}_${_baltrad/datetime:%Y%m%d%H%M}.interval_l(15).h5")

        assert("2000/01/01/12/00/setst_20000101T120400Z_Pvol_DBZH_200001011200.h5" == namer.name(meta))

    def test_complex_name_baltrad_source_NOD(self):
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

        namer = metadata_namer("${_baltrad/datetime_u:15:%Y/%m/%d/%H/%M}/${_baltrad/source:NOD}_${/what/date}T${/what/time}.interval_l(15)Z_${/what/object}.tolower().toupper(0)_${/dataset1/data1/what/quantity}_${_baltrad/datetime_u:15:%Y%m%d%H%M}.h5")

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
    
    def create_metadata(self, year, month, day, hour, minute):
        meta = oh5.Metadata()
        meta.add_node("/", Group("what"))
        meta.add_node("/what", Attribute("object", "PVOL"))
        meta.add_node("/what", Attribute("date", datetime.date(year, month, day)))
        meta.add_node("/what", Attribute("time", datetime.time(hour, minute)))
        meta.add_node("/", Group("dataset1"))
        meta.add_node("/dataset1", Group("data1"))
        meta.add_node("/dataset1/data1", Group("what"))
        meta.add_node("/dataset1/data1/what", Attribute("quantity", "DBZH"))
        meta.bdb_source = "NOD:setst,WMO:12345,RAD:SE52,WIGOS:12345"
        meta.what_source = "NOD:setst,WMO:12345,RAD:SE52"
        meta.bdb_source_name = "setst"
        return meta

    def create_scan_metadata(self, year, month, day, hour, minute, elangle):
        meta = oh5.Metadata()
        meta.add_node("/", Group("what"))
        meta.add_node("/what", Attribute("object", "SCAN"))
        meta.add_node("/what", Attribute("date", datetime.date(year, month, day)))
        meta.add_node("/what", Attribute("time", datetime.time(hour, minute)))
        meta.add_node("/", Group("dataset1"))
        meta.add_node("/dataset1", Group("where"))
        meta.add_node("/dataset1/where", Attribute("elangle", elangle))
        meta.bdb_source = "NOD:setst,WMO:12345,RAD:SE52,WIGOS:12345"
        meta.what_source = "NOD:setst,WMO:12345,RAD:SE52"
        meta.bdb_source_name = "setst"
        return meta

    def test_baltrad_datetime_u(self):
        namer = metadata_namer("${_baltrad/datetime_u:15:%Y%m%d%H%M}")

        for i in range(60):
            meta = self.create_metadata(2000, 1, 1, 12, i)
            name = namer.name(meta)
            if i >= 0 and i < 15:
                self.assertEqual("200001011215", name)
            elif i >= 15 and i < 30:
                self.assertEqual("200001011230", name)
            elif i >= 30 and i < 45:
                self.assertEqual("200001011245", name)
            elif i >= 45 and i < 60:
                self.assertEqual("200001011300", name)
        
    def test_baltrad_datetime_l(self):
        namer = metadata_namer("${_baltrad/datetime_l:15:%Y%m%d%H%M}")

        for i in range(60):
            meta = self.create_metadata(2000, 1, 1, 12, i)
            name = namer.name(meta)
            if i >= 0 and i < 15:
                self.assertEqual("200001011200", name)
            elif i >= 15 and i < 30:
                self.assertEqual("200001011215", name)
            elif i >= 30 and i < 45:
                self.assertEqual("200001011230", name)
            elif i >= 45 and i < 60:
                self.assertEqual("200001011245", name)

    def create_opera_metadata(self, year, month, day, hour, minute, source, sourcename, source_parent, otype, quantities=["DBZH"], elangles=[0.5]):
        meta = oh5.Metadata()
        meta.source_parent = source_parent
        meta.add_node("/", Group("what"))
        meta.add_node("/what", Attribute("object", otype))
        meta.add_node("/what", Attribute("date", datetime.date(year, month, day)))
        meta.add_node("/what", Attribute("time", datetime.time(hour, minute)))
        ectr = 1
        for elangle in elangles:
            meta.add_node("/", Group(f"dataset{ectr}"))
            meta.add_node(f"/dataset{ectr}", Group("where"))
            meta.add_node(f"/dataset{ectr}/where", Attribute("elangle", elangle))
            qctr = 1
            for quantity in quantities:
                meta.add_node(f"/dataset{ectr}", Group(f"data{qctr}"))
                meta.add_node(f"/dataset{ectr}/data{qctr}", Group("what"))
                meta.add_node(f"/dataset{ectr}/data{qctr}/what", Attribute("quantity", quantity))
                qctr = qctr + 1
            ectr = ectr + 1
        meta.bdb_source = source
        meta.what_source = source
        meta.bdb_source_name = sourcename
        return meta

    def test_baltrad_opera_filename_PVOL_DBZH_A_angle(self):
        namer = metadata_namer("${_baltrad/opera_filename}")
        ofn = opera_filename_namer("_baltrad/opera_filename", None, {"namer_config":{"sella":{"elevation_angles":[0.5, 1.0, 1.5, 2.0, 2.5, 4.0, 8.0, 14.0, 24.0, 40.0, 1.25]}}})

        namer.register_operation("_baltrad/opera_filename", ofn)

        meta = self.create_opera_metadata(2000, 1, 1, 12, 0, "NOD:sella,RAD:SE41", "sella", Source("se", {"CCCC":"ESWI"}),"PVOL", ["DBZH"], [0.5])
        self.assertEqual("T_PAGA41_C_ESWI_20000101120000", namer.name(meta))


    def test_baltrad_opera_filename_PVOL_DBZH_B_angle(self):
        namer = metadata_namer("${_baltrad/opera_filename}")
        ofn = opera_filename_namer("_baltrad/opera_filename", None, {"namer_config":{"sella":{"elevation_angles":[0.5, 1.0, 1.5, 2.0, 2.5, 4.0, 8.0, 14.0, 24.0, 40.0, 1.25]}}})

        namer.register_operation("_baltrad/opera_filename", ofn)

        meta = self.create_opera_metadata(2000, 1, 1, 12, 0, "NOD:sella,RAD:SE41", "sella", Source("se", {"CCCC":"ESWI"}),"PVOL", ["DBZH"], [1.0])
        self.assertEqual("T_PAGB41_C_ESWI_20000101120000", namer.name(meta))

    def test_baltrad_opera_filename_PVOL_DBZH_multiple_angles(self):
        namer = metadata_namer("${_baltrad/opera_filename}")
        ofn = opera_filename_namer("_baltrad/opera_filename", None, {"namer_config":{"sella":{"elevation_angles":[0.5, 1.0, 1.5, 2.0, 2.5, 4.0, 8.0, 14.0, 24.0, 40.0, 1.25]}}})

        namer.register_operation("_baltrad/opera_filename", ofn)

        meta = self.create_opera_metadata(2000, 1, 1, 12, 0, "NOD:sella,RAD:SE41", "sella", Source("se", {"CCCC":"ESWI"}),"PVOL", ["DBZH"], [0.5, 1.0])
        self.assertEqual("T_PAGZ41_C_ESWI_20000101120000", namer.name(meta))

    def test_baltrad_opera_filename_PVOL_TH_A_angle(self):
        namer = metadata_namer("${_baltrad/opera_filename}")
        ofn = opera_filename_namer("_baltrad/opera_filename", None, {"namer_config":{"sella":{"elevation_angles":[0.5, 1.0, 1.5, 2.0, 2.5, 4.0, 8.0, 14.0, 24.0, 40.0, 1.25]}}})

        namer.register_operation("_baltrad/opera_filename", ofn)

        meta = self.create_opera_metadata(2000, 1, 1, 12, 0, "NOD:sella,RAD:SE41", "sella", Source("se", {"CCCC":"ESWI"}),"PVOL", ["TH"], [0.5])
        self.assertEqual("T_PAJA41_C_ESWI_20000101120000", namer.name(meta))


    def test_baltrad_opera_filename_PVOL_DBZH_TH_A_angle(self):
        namer = metadata_namer("${_baltrad/opera_filename}")
        ofn = opera_filename_namer("_baltrad/opera_filename", None, {"namer_config":{"sella":{"elevation_angles":[0.5, 1.0, 1.5, 2.0, 2.5, 4.0, 8.0, 14.0, 24.0, 40.0, 1.25]}}})

        namer.register_operation("_baltrad/opera_filename", ofn)

        meta = self.create_opera_metadata(2000, 1, 1, 12, 0, "NOD:sella,RAD:SE41", "sella", Source("se", {"CCCC":"ESWI"}),"PVOL", ["DBZH", "TH"], [0.5])
        self.assertEqual("T_PAGA41_C_ESWI_20000101120000", namer.name(meta))

    def test_baltrad_opera_filename_SCAN_DBZH_A_angle(self):
        namer = metadata_namer("${_baltrad/opera_filename}")
        ofn = opera_filename_namer("_baltrad/opera_filename", None, {"namer_config":{"sella":{"elevation_angles":[0.5, 1.0, 1.5, 2.0, 2.5, 4.0, 8.0, 14.0, 24.0, 40.0, 1.25]}}})

        namer.register_operation("_baltrad/opera_filename", ofn)

        meta = self.create_opera_metadata(2000, 1, 1, 12, 0, "NOD:sella,RAD:SE41", "sella", Source("se", {"CCCC":"ESWI"}),"SCAN", ["DBZH"], [0.5])
        self.assertEqual("T_PAGA41_C_ESWI_20000101120000", namer.name(meta))

    def test_baltrad_opera_filename_VP(self):
        namer = metadata_namer("${_baltrad/opera_filename}")
        ofn = opera_filename_namer("_baltrad/opera_filename", None, {"namer_config":{"sella":{"elevation_angles":[0.5, 1.0, 1.5, 2.0, 2.5, 4.0, 8.0, 14.0, 24.0, 40.0, 1.25]}}})

        namer.register_operation("_baltrad/opera_filename", ofn)

        meta = self.create_opera_metadata(2000, 1, 1, 12, 0, "NOD:sella,RAD:SE41", "sella", Source("se", {"CCCC":"ESWI"}),"VP", ["DBZH"], [0.5])
        self.assertEqual("sella_vp_20000101T120000Z", namer.name(meta))

    def test_baltrad_opera_filename_fileconfig(self):
        namer = metadata_namer("${_baltrad/opera_filename}")
        ofn = opera_filename_namer("_baltrad/opera_filename", None, {"filename":self.NAMER_CONFIG_FILENAME})

        namer.register_operation("_baltrad/opera_filename", ofn)

        meta = self.create_opera_metadata(2000, 1, 1, 12, 0, "NOD:sella,RAD:SE41", "sella", Source("se", {"CCCC":"ESWI"}),"VP", ["DBZH"], [0.5])
        self.assertEqual("sella_vp_20000101T120000Z", namer.name(meta))

    def test_properties_dict(self):
        namer = metadata_namer("${_property:se.this.property.1}_${_property:se.this.property.2}_${/what/date}_${/what/time}")
        namer.set_properties({"se.this.property.1":"yes","se.this.property.2":123})

        meta = self.create_metadata(2000, 1, 1, 12, 0)
        self.assertEqual("yes_123_20000101_120000", namer.name(meta))

    def test_properties_file(self):
        namer = metadata_namer("${_property:se.this.property.1}_${_property:se.this.property.2}_${/what/date}_${/what/time}")
        namer.set_properties(self.FIXTURE_NAMER_PROPERTY_FILE)

        meta = self.create_metadata(2000, 1, 1, 12, 0)
        self.assertEqual("yes_123_20000101_120000", namer.name(meta))

    def test_properties_file_property_not_found(self):
        namer = metadata_namer("${_property:se.this.property.1}_${_property:se.this.property.2}_${_property:se.this.property.3}_${/what/date}_${/what/time}")
        namer.set_properties(self.FIXTURE_NAMER_PROPERTY_FILE)

        meta = self.create_metadata(2000, 1, 1, 12, 0)
        self.assertEqual("yes_123__20000101_120000", namer.name(meta))

