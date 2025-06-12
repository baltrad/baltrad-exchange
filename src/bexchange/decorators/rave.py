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

from bexchange.decorators.decorator import decorator_manager, decorator
import _raveio, _rave, _polarvolume, _polarscan
from tempfile import NamedTemporaryFile
import shutil, logging
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

class filter_quantities(decorator):
    """Removes all quantities in a volume or scan except the ones specified.
    """
    def __init__(self, backend, allow_discard, quantities, version_table={}):
        """Constructor
        :param backend: the backend
        :param allow_discard: if decorate returns None and allow_discard is = True, then the file is removed and not sent
        :param quantities: the quantities to keep in the file
        :param version_table: will write the outgoing file in the version according to the version table
        """
        super(filter_quantities, self).__init__(backend, allow_discard)
        logger.info(f"quantities={quantities}, version_table={version_table}")
        self._quantities = quantities
        self._version_table = version_table

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

    def decorate(self, inf, meta):
        """ Removes requested quantities from the infile and writes a new file that is returned
        :param inf: The name of the incomming file
        :param meta: Metadata of the infile
        :return: a decorated file if applicable
        """
        try:
            if meta.what_object == "SCAN" or meta.what_object == "PVOL":
                rin = _raveio.open(inf.name)
                a = rin.object
                a.removeParametersExcept(self._quantities)
                newf = NamedTemporaryFile(dir=self.backend().get_tmp_folder())
                rio = _raveio.new()
                rio.object = a
                if len(self._version_table) > 0:
                    rin_version = self.convert_from_odim_version(rin.read_version)
                    if rin_version != RAVE_VERSION_UNDEFINED:
                        if rin_version in self._version_table:
                            out_version = self._version_table[rin_version]
                        elif "default" in self._version_table:
                            out_version = self._version_table["default"]
                        else:
                            out_version = rin_version
                        rio.version = self.convert_to_odim_version(out_version)
                    else:
                        rio.version = rin.read_version
                rio.save(newf.name)
                newf.flush()
                return newf
        except:
            logger.exception("Failed to decorate file")
        return None
