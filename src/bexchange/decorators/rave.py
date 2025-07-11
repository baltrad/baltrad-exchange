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

## If rave is available it is possible to use these predefined decorators for processing
# scans and volumes.

## @file
## @author Anders Henja, SMHI
## @date 2025-06-12
from __future__ import absolute_import

from bexchange.decorators.decorator import decorator_manager
from bexchange.decorators.decorator import decorator as basedecorator

import _raveio, _rave, _polarvolume, _polarscan, _verticalprofile
from tempfile import NamedTemporaryFile
import shutil, logging, importlib, struct, math
from datetime import timedelta, datetime, timezone

logger = logging.getLogger("bexchange.decorators.rave")

RAVE_VERSION_UNDEFINED="UNDEFINED"
RAVE_VERSIONS={
   _raveio.RaveIO_ODIM_Version_2_0:"2.0",
   _raveio.RaveIO_ODIM_Version_2_1:"2.1",
   _raveio.RaveIO_ODIM_Version_2_2:"2.2",
   _raveio.RaveIO_ODIM_Version_2_3:"2.3",
   _raveio.RaveIO_ODIM_Version_2_4:"2.4",
   _raveio.RaveIO_ODIM_Version_UNDEFINED:RAVE_VERSION_UNDEFINED
}

class object_modifier(object):
    """A modifier is used for modifying a file in memory
    """
    def __init__(self, backend):
        self._backend = backend
    
    def backend(self):
        """
        :return: the backend
        """
        return self._backend

    def modify(self, obj, meta, **kw):
        """If this modifier can operate on the object it will be modified directly. It assumes that the object is a rave object of some type
        :param obj: A rave core object
        :returns: N/A
        """
        raise Exception("Not implemented")    

class coordinate_modifier(object_modifier):
    """ Modifies coordinates in objects like scans, volumes and vertical profiles
    """
    def __init__(self, backend, format="hex", coordinates={}):
        """ Constructor
        :param backend: the backend
        :param format: the format of the coordinates. Can be either hex, dex or rad. If hex, then a conversion from hex to float is performed (hex value should be radians or meters. rad and deg is float
        """
        super(coordinate_modifier, self).__init__(backend)
        self._coordinates=coordinates
        if format not in ["hex", "deg", "rad"]:
            raise Exception("Format must be either 'hex', 'rad' or 'deg'(rees)")
        self._format = format
    
    def double_to_hex(self, x):
        """ Convert a float to a hex representation
        :param x: the doble value to convert
        :return the hex string
        """
        return hex(struct.unpack('<Q', struct.pack('<d', x))[0])

    def hex_to_double(self, x):
        """ Convert a hex string into a float
        :param x: the hex string
        :return the float value
        """
        return struct.unpack('!d', bytes.fromhex(x.strip().replace("0x", "")))[0]    

    def modify(self, obj, meta, **kw):
        """ Modifies coordinates for polar scans, polar volumes and vertical profiles if coordinate entry is found in coordinates
        :param obj: the rave object
        :param meta: the metadata
        :return None
        """
        if _polarscan.isPolarScan(obj) or _verticalprofile.isVerticalProfile(obj) or _polarvolume.isPolarVolume(obj):
            if meta.bdb_source_name in self._coordinates:
                vlon = self._coordinates[meta.bdb_source_name]["longitude"]
                vlat = self._coordinates[meta.bdb_source_name]["latitude"]
                vheight = self._coordinates[meta.bdb_source_name]["height"]

                if self._format == "hex":
                    obj.longitude = self.hex_to_double(vlon)
                    obj.latitude = self.hex_to_double(vlat)
                    obj.height = self.hex_to_double(vheight)
                elif self._format == "rad":
                    obj.longitude = vlon
                    obj.latitude = vlat
                    obj.height = vheight
                elif self._format == "deg":
                    obj.longitude = vlon * math.pi / 180.0
                    obj.latitude = vlat * math.pi / 180.0
                    obj.height = vheight
                return

class scan_attribute_renamer(object_modifier):
    """ Modifies attribute names according to outgoing version.
    """
    def __init__(self, backend, version_mapping):
        """ Constructor
        :param backend: the backend
        :param version_mapping: the attribute version mapping
        """
        super(scan_attribute_renamer, self).__init__(backend)
        self._version_mapping=version_mapping

    def modify(self, obj, meta, **kw):
        """ Modifies top level attributes in scans 
        :param obj: the rave object
        :param meta: the metadata
        :return None
        """
        if _polarscan.isPolarScan(obj):
            if "wanted_version" in kw:
                wanted_version = kw["wanted_version"]
                if wanted_version in self._version_mapping:
                    translation_table = self._version_mapping[wanted_version]
                    for k in translation_table:
                        if obj.hasAttribute(k):
                            v = obj.getAttribute(k)
                            obj.removeAttribute(k)
                            if translation_table[k] is not None:
                                newname = translation_table[k]
                                obj.addAttribute(newname, v)

class scan_volume_parameter_remover(object_modifier):
    """ Modifies attribute names according to outgoing version.
    """
    def __init__(self, backend, quantities_to_keep):
        """ Constructor
        :param backend: the backend
        :param quantities_to_keep: the parameters to keep
        """
        super(scan_volume_parameter_remover, self).__init__(backend)
        self._quantities_to_keep = quantities_to_keep

    def modify(self, obj, meta, **kw):
        """ Modifies top level attributes in scans 
        :param obj: the rave object
        :param meta: the metadata
        :return None
        """
        if _polarscan.isPolarScan(obj) or _polarvolume.isPolarVolume(obj):
            obj.removeParametersExcept(self._quantities_to_keep)

class what_source_setter(object_modifier):
    """ Sets a specific what/source in a file
    """
    def __init__(self, backend, sources):
        """ Constructor
        :param backend: the backend
        :param sources: a mapping between source and a what/source string
        """
        super(what_source_setter, self).__init__(backend)
        self._sources = sources

    def modify(self, obj, meta, **kw):
        """ Modifies top level attributes in scans 
        :param obj: the rave object
        :param meta: the metadata
        :return None
        """
        if meta.bdb_source_name in self._sources or "default" in self._sources:
            src_to_set = None
            if meta.bdb_source_name in self._sources:
                src_to_set = self._sources[meta.bdb_source_name]
            else:
                src_to_set = self._sources["default"]
            try:
                if "source" in dir(obj):
                    obj.source = src_to_set
            except:
                pass

class rave_inmemory_manager:
    """The manager for creating inmemory_operations used within bexchange. 
    """
    def __init__(self):
        """Constructor
        """
        pass
    
    @classmethod
    def create(self, backend, clz, arguments):
        """Creates an instance of clz with specified arguments
        :param clz: class name specified as <module>.<classname>
        :param arguments: a list of arguments that should be used to initialize the class       
        """
        logger.info("Creating inmemory_modifier: %s"%clz)
        if clz.find(".") > 0:
            lastdot = clz.rfind(".")
            module = importlib.import_module(clz[:lastdot])
            classname = clz[lastdot+1:]
            return getattr(module, classname)(backend, **arguments)
        else:
            raise Exception("Must specify class as module.class")

class decorator(basedecorator):
    """Rave decorator utilizing the functionality in rave to perform inmemory operations
    """
    def __init__(self, backend, allow_discard, can_return_invalid_file_content, version_table={}, inmemory_modifiers=[]):
        """Constructor
        :param backend: the backend
        :param allow_discard: if decorate returns None and allow_discard is = True, then the file is removed and not sent
        :param version_table: will write the outgoing file in the version according to the version table
        :param inmemory_modifiers: operations that will take place in the file before it is written
        """
        super(decorator, self).__init__(backend, allow_discard, can_return_invalid_file_content)
        logger.info(f"version_table={version_table}")
        self._version_table = version_table
        self._inmemory_modifiers=[]
        if inmemory_modifiers:
            for im in inmemory_modifiers:
                if "modifier" in im:
                    arguments = {}
                    if "arguments" in im:
                        arguments = im["arguments"]
                    modifier = rave_inmemory_manager.create(backend, im["modifier"], arguments)
                    self._inmemory_modifiers.append(modifier)

    def convert_from_odim_version(self, read_version):
        """ Converts the _raveio read_version into a string representing the version
        :param read_version: the RaveIO_ODIM_Version
        :return: a string, e.g. "2.2", "2.3", ...
        """
        if read_version in RAVE_VERSIONS:
            return RAVE_VERSIONS[read_version]
        return RAVE_VERSION_UNDEFINED

    def convert_to_odim_version(self, out_version):
        """ Will convert a string version ("2.2", "2.3", ...) into a RaveIO_ODIM_Version
        :param out_version: The version string
        :return: the RaveIO_ODIM_Version
        """
        for k, v in RAVE_VERSIONS.items():
            if out_version == v:
                return k
        raise Exception(f"Can't identify out_version={out_version}")

    def get_wanted_version(self, read_version):
        """ Calculates wanted version from the read version
        :param read_version: the incomming file version
        :return: the wanted version
        """
        result = read_version
        if len(self._version_table) > 0:
            rin_version = self.convert_from_odim_version(read_version)
            if rin_version != RAVE_VERSION_UNDEFINED:
                if rin_version in self._version_table:
                    result = self._version_table[rin_version]
                elif "default" in self._version_table:
                    result = self._version_table["default"]
                else:
                    result = rin_version
        return result

    def decorate(self, inf, meta):
        """ Removes requested quantities from the infile and writes a new file that is returned
        :param inf: The name of the incomming file
        :param meta: Metadata of the infile
        :return: a decorated file if applicable
        """
        try:
            if meta.what_object == "SCAN" or meta.what_object == "PVOL" or meta.what_object == "VP":
                rin = _raveio.open(inf.name)

                wanted_version = self.get_wanted_version(rin.read_version)

                for im in self._inmemory_modifiers:
                    logger.debug("Running modifier: %s"%im)
                    im.modify(rin.object, meta, read_version=rin.read_version, wanted_version=wanted_version)

                newf = NamedTemporaryFile(dir=self.backend().get_tmp_folder())
                rio = _raveio.new()
                rio.object = rin.object
                rio.version =  self.convert_to_odim_version(wanted_version)
                rio.save(newf.name)
                newf.flush()
                return newf
        except:
            logger.exception("Failed to decorate file")
        return None
