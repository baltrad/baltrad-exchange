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

## Functionality to generate specific names from metadata

## @file
## @author Anders Henja, SMHI
## @date 2021-08-18
import re
from io import StringIO
from datetime import datetime
from baltrad.bdbcommon.oh5 import (
    Source,
)
PATTERN = re.compile("\\$(?:" + "(\\$)|" +
                     "\\{([_/a-z][_:/a-z0-9 #@+\\-\\.%]*)\\}((.(tolower|toupper|substring|trim|rtrim|ltrim|interval_u|interval_l|replace)(\\((([0-9]+|'[^']*')(,([0-9]+|'[^']*'))?)?\\)))*)" +
                     ")", flags=re.IGNORECASE)

SUBOP_PATTERN = re.compile(".(tolower|toupper|substring|trim|rtrim|ltrim|interval_u|interval_l|replace)(\\((([0-9]+|'[^']*')(,([0-9]+|'[^']*'))?)?\\))", flags=re.IGNORECASE)

BALTRAD_DATETIME_PATTERN=re.compile("^_baltrad/datetime(:[A-Za-z0-9\\-/: _%]+)?$", flags=re.IGNORECASE)

class suboperation_helper:
    """Used to simplify suboperation execution in a name pattern. Each suboperation is implemented as a method in this function and called by eval upon execution
    """
    def __init__(self, value, suboperations):
        self.value = value
        self.eval_value = self.value
        self.suboperations = suboperations

    def eval(self):
        """Executes the suboperation(s) on the value in from left to right
        """
        self.eval_value = self.value
        m = re.search(SUBOP_PATTERN, self.suboperations)
        while m:
            span = m.span()
            self.suboperations = self.suboperations[span[1]:]
            self.eval_value = eval("self%s"%m.group(0))
            m = re.search(SUBOP_PATTERN, self.suboperations)
        return self.eval_value
    
    def tolower(self,start=None,end=None):
        if start is not None:
            if end is None:
                if start >= 0 and start < len(self.eval_value):
                    return self.eval_value[0:start] + self.eval_value[start].lower() + self.eval_value[start+1:]
            else:
                if start >= 0 and start < len(self.eval_value) and end >= 0 and end < len(self.eval_value) and end > start:
                    return self.eval_value[0:start] + self.eval_value[start:end+1].lower() + self.eval_value[end+1:]
        return self.value.lower()

    def toupper(self,start=None,end=None):
        if start is not None:
            if end is None:
                if start >= 0 and start < len(self.eval_value):
                    return self.eval_value[0:start] + self.eval_value[start].upper() + self.eval_value[start+1:]
            else:
                if start >= 0 and start < len(self.eval_value) and end >= 0 and end < len(self.eval_value) and end > start:
                    return self.eval_value[0:start] + self.eval_value[start:end+1].upper() + self.eval_value[end+1:]
        return self.value.upper()

    def substring(self,start,end=None):
        if end is not None:
            return self.eval_value[start:end+1]
        return self.eval_value[start:]

    def replace(self, c1, c2):
        if c1.startswith("'"):
            c1=c1[1:]
        if c1.endswith("'"):
            c1=c1[0:-1]
        if c2.startswith("'"):
            c2=c2[1:]
        if c2.endswith("'"):
            c2=c2[0:-1]
            
        x = self.eval_value
        if isinstance(x, float) or isinstance(x, int):
            x=str(x)
        return x.replace(c1, c2)

    def trim(self):
        return self.eval_value.strip()

    def rtrim(self):
        return self.eval_value.rstrip()

    def ltrim(self):
        return self.eval_value.lstrip()

    def interval_u(self, interval):
        minute=int(self.eval_value[-2:])
        period = minute/int(interval)
        nminute = (period+1)*int(interval)
        return self.eval_value[:-2] + "%02d"%nminute

    def interval_l(self, interval):
        minute=int(self.eval_value[-2:])
        period = minute/int(interval)
        nminute = (period)*int(interval)
        return self.eval_value[:-2] + "%02d"%nminute

##
# Used to create file names from metadata associated with a ODIM h5 file.
class metadata_namer:
    def __init__(self, tmpl):
        self.tmpl = tmpl
        self.suboperations={}
        #self.suboperations["tolower"] = self.tolower
    
    def name(self, meta):
        buffer = StringIO()
        
        parsed_tmpl = self.tmpl
        m = re.search(PATTERN, parsed_tmpl)
        while m:
            span = m.span() # Keeps track on where in file this pattern is matching
            placeholder = m.group(2);
            suboperation = m.group(3);
            
            # This is the beginning of the name until the first match
            buffer.write(parsed_tmpl[0:span[0]])
            if placeholder.startswith("_bdb/source:"):
                replacement_value = self.get_source_item(placeholder[12:], Source.from_string(meta.bdb_source))
            elif placeholder.startswith("_bdb/source_name"):
                replacement_value = meta.bdb_source_name
            elif placeholder.startswith("what/source:"):
                replacement_value = self.get_source_item(placeholder[12:], Source.from_string(meta.what_source))
            elif placeholder.startswith("/what/source:"):
                replacement_value = self.get_source_item(placeholder[13:], Source.from_string(meta.what_source))
            elif BALTRAD_DATETIME_PATTERN.search(placeholder):
                m = BALTRAD_DATETIME_PATTERN.match(placeholder)
                t = m.group(1)
                if t and t.find(":") >= 0:
                    t = t[t.find(":")+1:]
                if not t:
                    t = "%Y%m%d%H%M%S"
                dt = datetime(meta.what_date.year, meta.what_date.month, meta.what_date.day, meta.what_time.hour, meta.what_time.minute, meta.what_time.second, 0)
                replacement_value = dt.strftime(t)
            else:
                replacement_value = self.get_attribute_value(placeholder, meta)

            if replacement_value:
                if suboperation:
                    replacement_value = suboperation_helper(replacement_value,suboperation).eval()
            else:
                replacement_value = parsed_tmpl[span[0]:span[1]]
            if isinstance(replacement_value,float):
                buffer.write("%g"%replacement_value)
            elif isinstance(replacement_value,int):
                buffer.write("%d"%replacement_value)
            else:
                buffer.write(replacement_value)
            parsed_tmpl = parsed_tmpl[span[1]:]
            m = re.search(PATTERN, parsed_tmpl)
        buffer.write(parsed_tmpl)   
        return buffer.getvalue()
    
    def get_attribute_value(self, name, meta):
        try:
            return meta.node(name).value
        except LookupError:
            return None

    def get_source_item(self, key, source):
        if key in source:
            return source[key]
        return "undefined"

if __name__=="__main__":
    from baltrad.bdbcommon import oh5
    #meta = oh5.Metadata.from_file("sehem_scan_20200414T160000Z.h5")
    meta = oh5.Metadata.from_file("/projects/baltrad/baltrad-exchange/perf_test/scans/Z_SCAN_C_ESWI_20101016080000_sease_000000.h5")
    #namer = metadata_namer("${_baltrad/datetime:%Y/%m/%d/%H/%M}.interval_u(15)/scan_${what/source:NOD}_${/what/date}T${/what/time}.interval_l(15)Z_${/what/object}.tolower().toupper(0)_${/dataset1/data1/what/quantity}_${_baltrad/datetime:%Y%m%d%H%M}.interval_u(15).h5")
    namer = metadata_namer("${_baltrad/datetime:%Y/%m/%d/%H/%M}.interval_u(15)/scan_${_bdb/source_name}_${/what/date}T${/what/time}.interval_l(15)Z_${/what/object}.tolower().toupper(0)_${/dataset1/data1/what/quantity}_${_baltrad/datetime:%Y%m%d%H%M}.interval_u(15).h5")
    
    print(namer.name(meta))