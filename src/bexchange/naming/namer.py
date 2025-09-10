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
import logging
import importlib
import math
import json
import os
from io import StringIO
from datetime import datetime, timedelta
from bexchange import config
from baltrad.bdbcommon.oh5 import (
    Source,
)

logger = logging.getLogger("bexchange.naming.namer")

PATTERN = re.compile("\\$(?:" + "(\\$)|" +
                     "\\{([_/a-z][_:/a-z0-9 #@+\\-\\.%]*)\\}((.(tolower|toupper|substring|trim|rtrim|ltrim|interval_u|interval_l|replace)(\\((([0-9]+|'[^']*')(,([0-9]+|'[^']*'))?)?\\)))*)" +
                     ")", flags=re.IGNORECASE)

SUBOP_PATTERN = re.compile(".(tolower|toupper|substring|trim|rtrim|ltrim|interval_u|interval_l|replace)(\\((([0-9]+|'[^']*')(,([0-9]+|'[^']*'))?)?\\))", flags=re.IGNORECASE)

BALTRAD_DATETIME_PATTERN=re.compile("^_baltrad/datetime(:[A-Za-z0-9\\-/: _%]+)?$", flags=re.IGNORECASE)

BALTRAD_DATETIMEU_PATTERN=re.compile("^_baltrad/datetime_u:([0-9]{2})(:[A-Za-z0-9\\-/: _%]+)?$", flags=re.IGNORECASE)

BALTRAD_DATETIMEL_PATTERN=re.compile("^_baltrad/datetime_l:([0-9]{2})(:[A-Za-z0-9\\-/: _%]+)?$", flags=re.IGNORECASE)

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
        """ Changes to lower case between start and end position. If start and end is given, then 
        a subset is changed.
        :param start: Start position
        :param end: End position
        :return new value
        """
        if start is not None:
            if end is None:
                if start >= 0 and start < len(self.eval_value):
                    return self.eval_value[0:start] + self.eval_value[start].lower() + self.eval_value[start+1:]
            else:
                if start >= 0 and start < len(self.eval_value) and end >= 0 and end < len(self.eval_value) and end > start:
                    return self.eval_value[0:start] + self.eval_value[start:end+1].lower() + self.eval_value[end+1:]
        return self.value.lower()

    def toupper(self,start=None,end=None):
        """ Changes to upper case between start and end position. If start and end is given, then 
        a subset is changed.
        :param start: Start position
        :param end: End position
        :return new value
        """
        if start is not None:
            if end is None:
                if start >= 0 and start < len(self.eval_value):
                    return self.eval_value[0:start] + self.eval_value[start].upper() + self.eval_value[start+1:]
            else:
                if start >= 0 and start < len(self.eval_value) and end >= 0 and end < len(self.eval_value) and end > start:
                    return self.eval_value[0:start] + self.eval_value[start:end+1].upper() + self.eval_value[end+1:]
        return self.value.upper()

    def substring(self,start,end=None):
        """Returns a substring between start & end.
        :param start: The start position
        :param end: End position (if specified, otherwise rest of string)
        :return the substring 
        """
        if end is not None:
            return self.eval_value[start:end+1]
        return self.eval_value[start:]

    def replace(self, c1, c2):
        """Replace one string with a different one
        :param c1: string to replace
        :param c2: string to replace with
        :return the string that has been modified
        """
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
        """ Trims both ends of the eval-value from whitespaces
        :return the trimmed string
        """
        return self.eval_value.strip()

    def rtrim(self):
        """ Trims right side of the eval-value from whitespaces
        :return the trimmed string
        """
        return self.eval_value.rstrip()

    def ltrim(self):
        """ Trims left side of the eval-value from whitespaces
        :return the trimmed string
        """
        return self.eval_value.lstrip()

    def interval_u(self, interval, limit=60):
        """Assumes that the 2 last characters in eval value is a integer, (00, 01, 10...). Then
        this value is modified to upper part of that interval. For example assuming that it is
        minutes that are evaluated and interval = 15 and limit = 60. Then the following modification will be
        performed.
        00-14 => 15
        15-29 => 30
        30-44 => 45
        45-59 => 00. Since limit is 60, the value will be put back to 0
        :param interval: Interval
        :param limit: Limit for a wrap around
        """
        minute=int(self.eval_value[-2:])
        period = int(minute/interval)
        nminute = (period+1)*int(interval)
        if nminute >= limit:
            nminute = 0
        return self.eval_value[:-2] + "%02d"%nminute

    def interval_l(self, interval):
        """Assumes that the 2 last characters in eval value is a integer, (00, 01, 10...). Then
        this value is modified to lower part of that interval. For example assuming that it is
        minutes that are evaluated and interval = 15 and limit = 60. Then the following modification will be
        performed.
        00-14 => 00
        15-29 => 15
        30-44 => 30
        45-59 => 45.
        :param interval: Interval
        """
        minute=int(self.eval_value[-2:])
        period = int(minute/interval)
        nminute = period*int(interval)
        return self.eval_value[:-2] + "%02d"%nminute


class metadata_namer_operation(object):
    """ Provides possibility to add custom namer operations
    """
    def __init__(self, tag, backend, arguments={}):
        self._tag = tag
        self._backend = backend
        self._arguments = arguments

    def tag(self):
        return self._tag

    def backend(self):
        return self._backend

    def arguments(self):
        return self._arguments

    def create(self, placeholder, meta):
        """ Whenever a registered place holder is found, this method will be called with the current metadata.
        If it is possible to create the place holder string it is returned, otherwise the placeholder is returned.
        :param placeholder: the string that was found
        :param meta: the metadata
        :return: the string that the placeholder should be replaced with
        """
        raise RuntimeError("Subclass must implement create")

##
# Used to create file names from metadata associated with a ODIM h5 file.
class metadata_namer:
    """ Creates names from metadata
    """
    def __init__(self, tmpl):
        """ Constructor
        :param tmpl: the template string that should be used to generate a name
        """
        self.tmpl = tmpl
        self.tagoperations={}
        self._properties = {}
    
    def register_operation(self, tag, operation):
        """Registers a namer operation
        :param tag: the identifier used in the name template
        :param operation: a metadata_namer_operation instance
        """
        self.tagoperations[tag] = operation

    def set_properties(self, properties):
        """Sets properties in the namer. Can either provide a property file name or else a dictionary.
        :param properties: Either a filename (string) to a property file or a dictionary with the properties
        """
        if isinstance(properties, dict):
            self._properties = properties
        elif isinstance(properties, str):
            if os.path.exists(properties):
                self._properties = config.Properties.load(properties).dictionary()

    def get_property(self, name):
        """Returns the property with specified name.
        :param name: the name of the property
        :return the property if found, otherwise an empty string
        """
        if name in self._properties:
            return self._properties[name]
        return ""

    def template(self):
        """
        :return: the template string
        """
        return self.tmpl

    def name(self, meta):
        """
        :param meta: the metadata to create the name from
        :return: the created string
        """
        buffer = StringIO()
        
        parsed_tmpl = self.tmpl
        m = re.search(PATTERN, parsed_tmpl)
        while m:
            span = m.span() # Keeps track on where in file this pattern is matching
            placeholder = m.group(2);
            suboperation = m.group(3);
            
            # This is the beginning of the name until the first match
            buffer.write(parsed_tmpl[0:span[0]])
            if placeholder.startswith("_baltrad/source:"):
                replacement_value = self.get_source_item(placeholder[16:], Source.from_string(meta.bdb_source))
            elif placeholder.startswith("_baltrad/source_name"):
                replacement_value = meta.bdb_source_name
            elif placeholder.startswith("what/source:"):
                replacement_value = self.get_source_item(placeholder[12:], Source.from_string(meta.what_source))
            elif placeholder.startswith("/what/source:"):
                replacement_value = self.get_source_item(placeholder[13:], Source.from_string(meta.what_source))
            elif placeholder.startswith("_property:"):
                replacement_value = self.get_property(placeholder[10:])
            elif placeholder in self.tagoperations:
                replacement_value = self.tagoperations[placeholder].create(placeholder, meta)
            elif BALTRAD_DATETIME_PATTERN.search(placeholder):
                m = BALTRAD_DATETIME_PATTERN.match(placeholder)
                t = m.group(1)
                if t and t.find(":") >= 0:
                    t = t[t.find(":")+1:]
                if not t:
                    t = "%Y%m%d%H%M%S"
                dt = datetime(meta.what_date.year, meta.what_date.month, meta.what_date.day, meta.what_time.hour, meta.what_time.minute, meta.what_time.second, 0)
                replacement_value = dt.strftime(t)
            elif BALTRAD_DATETIMEU_PATTERN.search(placeholder):
                m = BALTRAD_DATETIMEU_PATTERN.match(placeholder)
                i = int(m.group(1))
                t = m.group(2)
                if t and t.find(":") >= 0:
                    t = t[t.find(":")+1:]
                if not t:
                    t = "%Y%m%d%H%M%S"
                    
                dt = datetime(meta.what_date.year, meta.what_date.month, meta.what_date.day, meta.what_time.hour, meta.what_time.minute, meta.what_time.second, 0)
                period = int(meta.what_time.minute/i)
                nminute = (period+1)*int(i)
                dt = dt + timedelta(minutes=nminute - meta.what_time.minute)
                    
                replacement_value = dt.strftime(t)
            elif BALTRAD_DATETIMEL_PATTERN.search(placeholder):
                m = BALTRAD_DATETIMEL_PATTERN.match(placeholder)
                i = int(m.group(1))
                t = m.group(2)
                if t and t.find(":") >= 0:
                    t = t[t.find(":")+1:]
                if not t:
                    t = "%Y%m%d%H%M%S"
                    
                dt = datetime(meta.what_date.year, meta.what_date.month, meta.what_date.day, meta.what_time.hour, meta.what_time.minute, meta.what_time.second, 0)
                nminute = meta.what_time.minute%int(i)
                dt = dt - timedelta(minutes=nminute)
                    
                replacement_value = dt.strftime(t)
            else:
                replacement_value = self.get_attribute_value(placeholder, meta)

            if replacement_value is not None:
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
        """
        :param name: the name of the attribute
        :param meta: the meta data
        :return: the value if possible
        :throws LookupError: if name not could be found
        """
        try:
            return meta.node(name).value
        except LookupError:
            return None

    def get_source_item(self, key, source):
        if key in source:
            return source[key]
        return "undefined"

##
# Used to create file names from metadata associated with a ODIM h5 file.
class property_metadata_namer(metadata_namer):
    """ Creates names from metadata
    """
    def __init__(self, tmpl):
        """ Constructor
        :param tmpl: the template string that should be used to generate a name
        """
        super(property_metadata_namer, self).__init__(tmpl)

    def name(self, meta):
        """
        :param meta: the metadata to create the name from
        :return: the created string
        """
        buffer = StringIO()
        
        parsed_tmpl = self.tmpl
        m = re.search(PATTERN, parsed_tmpl)
        while m:
            span = m.span() # Keeps track on where in file this pattern is matching
            placeholder = m.group(2);
            suboperation = m.group(3);
            
            # This is the beginning of the name until the first match
            buffer.write(parsed_tmpl[0:span[0]])
            replacement_value=None
            if placeholder.startswith("_property:"):
                replacement_value = self.get_property(placeholder[10:])

            if replacement_value is not None:
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

class metadata_namer_manager:
    def __init__(self):
        """Constructor
        """
        pass

    @classmethod
    def create_operation(self, clz, tag, backend, extra_arguments):
        if clz.find(".") > 0:
            logger.info("Creating namer operation '%s' with tag='%s'"%(clz, tag))
            lastdot = clz.rfind(".")
            module = importlib.import_module(clz[:lastdot])
            classname = clz[lastdot+1:]
            return getattr(module, classname)(tag, backend, extra_arguments)
        else:
            raise Exception("Must specify class as module.class")       
 
    @classmethod
    def from_conf(self, config, backend):
        """Creates a naming operation from the specified configuration if it is possible

        :param config: A namer config pattern. Should at least contain the following

        { "class":"<packagename>.<classname>",
          "tag":<name of storage>,
          "arguments":{}"
        }

        """
        arguments = {}
        namer_clazz = config["class"]
        tag = config["tag"]

        if "arguments" in config:
            arguments = config["arguments"]
        
        p = self.create_operation(namer_clazz, tag, backend, arguments)     

        return p
   
class opera_filename_namer(metadata_namer_operation):
    """ filename operation that implements support for the OPERA naming convention
    """
    def __init__(self, tag, backend, arguments={}):
        """Constructor
        :param cfg: the configuration necessary for mapping elevation angles to letters
        """
        super(opera_filename_namer, self).__init__(tag, backend, arguments)
        if "namer_config" in arguments:
            self._cfg = arguments["namer_config"]
        elif "filename" in arguments:
            self._cfg = self.read_config(arguments["filename"])
        else:
            raise Exception("Must provide namer_config in arguments")

    def read_config(self, filename):
        with open(filename, "r") as fp:
            cfg = json.load(fp)
            if not "namer_config" in cfg:
                raise Exception("Configuration read from file does not contain root namer_config")
            return cfg

    # pflag_productidentifier_oflag_originator_yyyyMMddhhmmss[_freeformat].type[.compression]
    # pflag = T
    # productidentifier = T1T2A1A2ii            T1T2 radar products = PA,    A1
    # För svep använder man A2=[A-W] och för volymer A2=[X-Z].
    # oflag = C
    # originator = CCCC
    # yyyyMMddhhmmss
    def create(self, placeholder, meta):
        """ Atempts to create a opera filename from the metadata. The created name will be in the format
        T_{T1}{T2}{A1}{A2}{ii}_C_{CCCC}_{yyyyMMddhhmmss}.h5
        Where
        {T1}{T2} = PA
        {A1} G-Z depending on content of file
        {A2} A-Z depending on content of file
        {ii} the last 2 digits in the RAD identifier.
        {CCCC} - the CCCC
        {yyyyMMddhhmmss} - the date time from the file.

        :param placeholder: the placeholder
        :param meta: the metadata
        :return the string to replace the placeholder with if possible
        """
        opera_name = placeholder
        if meta.what_object in ["PVOL", "SCAN"]:
            A1=None
            A2=None
            quantities = []
            elangles = []
            for setctr in range(1,30):
                setnode = meta.find_node(f"/dataset{setctr}")
                if setnode:
                    elangle = meta.find_node(f"/dataset1/where/elangle")
                    if not elangle:
                        break
                    elangles.append(elangle.value)
                    for paramctr in range(1,40):
                        paramnode = meta.find_node(f"/dataset{setctr}/data{paramctr}/what/quantity")
                        if not paramnode:
                            break
                        paramname = paramnode.value_str()
                        if paramname not in quantities:
                            quantities.append(paramname)

            if len(elangles) == 0 or len(quantities) == 0:
                logger.error("Could not identify any angles or quantities in file. Can't create a Opera conformant file without this information")
                return placeholder

            if len(quantities) > 1:
                A1="Z"
            elif "DBZH" in quantities:
                A1="G"
            elif "VRADH" in quantities or "VRADV" in quantities:
                A1="H"
            elif "WRADH" in quantities or "WRADV" in quantities:
                A1="I"
            elif "TH" in quantities and len(quantities) == 1:
                A1="J"
            elif "ZDR" in quantities:
                A1="K"
            elif "RHOHV" in quantities:
                A1="L"
            elif "PHIDP" in quantities:
                A1="Q"
            elif "KDP" in quantities:
                A1="R"

            if len(elangles) > 1:
                A2="Z"
            else:
                elname = "default"
                if meta.bdb_source_name in self._cfg and "elevation_angles" in self._cfg[meta.bdb_source_name]:
                    elname = meta.bdb_source_name
                if elname in self._cfg and "elevation_angles" in  self._cfg[elname]:
                    for e in self._cfg[elname]["elevation_angles"]:
                        if math.isclose(e, elangles[0]):
                            idx = self._cfg[elname]["elevation_angles"].index(e)
                            A2 = chr(ord('A') + idx)
                if A2 is None:
                    logger.error("Could not identify A2 information from elevation angles. Setting A2 = Y")
                    A2="Y"

            CCCC=meta.source_parent["CCCC"]
            ii = Source.from_string(meta.bdb_source)["RAD"][2:]
            
            dt = datetime(meta.what_date.year, meta.what_date.month, meta.what_date.day, meta.what_time.hour, meta.what_time.minute, meta.what_time.second, 0)
            yyyyMMddhhmmss = dt.strftime("%Y%m%d%H%M%S")
            opera_name=f"T_PA{A1}{A2}{ii}_C_{CCCC}_{yyyyMMddhhmmss}"
        elif meta.what_object in ["VP"]:
            source_name = meta.bdb_source_name
            dt = datetime(meta.what_date.year, meta.what_date.month, meta.what_date.day, meta.what_time.hour, meta.what_time.minute, meta.what_time.second, 0)
            yyyyMMddhhmmss = dt.strftime("%Y%m%dT%H%M%SZ")
            opera_name=f"{source_name}_vp_{yyyyMMddhhmmss}"
        else:
            logger.error("Can't handle object of type: %s"%meta.what_object)
        return opera_name

if __name__=="__main__":
    from baltrad.bdbcommon import oh5
    #meta = oh5.Metadata.from_file("sehem_scan_20200414T160000Z.h5")
    meta = oh5.Metadata.from_file("/projects/baltrad/baltrad-exchange/perf_test/scans/Z_SCAN_C_ESWI_20101016080000_sease_000000.h5")
    #namer = metadata_namer("${_baltrad/datetime:%Y/%m/%d/%H/%M}.interval_u(15)/scan_${what/source:NOD}_${/what/date}T${/what/time}.interval_l(15)Z_${/what/object}.tolower().toupper(0)_${/dataset1/data1/what/quantity}_${_baltrad/datetime:%Y%m%d%H%M}.interval_u(15).h5")
    namer = metadata_namer("${_baltrad/datetime:%Y/%m/%d/%H/%M}.interval_u(15)/scan_${_bdb/source_name}_${/what/date}T${/what/time}.interval_l(15)Z_${/what/object}.tolower().toupper(0)_${/dataset1/data1/what/quantity}_${_baltrad/datetime:%Y%m%d%H%M}.interval_u(15).h5")
    
    print(namer.name(meta))