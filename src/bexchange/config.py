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

## Provides functionality for reading the configuration

## @file
## @author Anders Henja, SMHI
## @date 2021-08-18
import radar_utils.jprops as jprops

_undefined = object()

class Error(Exception):
    """base configuration error"""

class PropertyLookupError(Error):
    """property not found
    """

class PropertyValueError(Error):
    """invalid property value
    """

class Properties(object):
    def __init__(self, values, prefix=""):
        """
        :param values: initial set of values
        :type values: :class:`dict`
        :prefix: the prefix to use for keys when getting values from this
                 instance
        :type prefix: :class:`str`
        """
        self._values = values
        self._prefix = prefix
    
    @property
    def prefix(self):
        return self._prefix
    
    def get(self, key, default=_undefined):
        """get the value associated with the key

        :param key: the key for which to look up the value
        :param default: default value if the key is not found
        :raise: :class:`PropertyLookupError` if the key is not found
                and no default value is provided.
        """
        try:
            return self[key]
        except PropertyLookupError:
            if default != _undefined:
                return default
            else:
                raise
    
    def get_int(self, key, default=_undefined):
        """get int value associated with the key

        :param key: the key for which to look up the value
        :param default: default value if the key is not found. This can be
                        any value, but when provided as a `str`, it is parsed
                        as if read from the configuration, otherwise it is
                        returned as it is.
        :param sep: value separator
        :raise: :class:`PropertyLookupError` if the key is not found
                and no default value is provided.
        """
        value = self.get(key, default)
        if not isinstance(value, str):
            return value
        
        try:
            return int(value)
        except ValueError:
            raise PropertyValueError("invalid int value: %s" % value)
    
    def get_list(self, key, default=_undefined, sep=" "):
        """get list of values associated with the key

        :param key: the key for which to look up the value
        :param default: default value if the key is not found. This can be
                        any value, but when provided as a `str`, it is parsed
                        as if read from the configuration, otherwise it is
                        returned as it is.
        :param sep: value separator
        :raise: :class:`PropertyLookupError` if the key is not found
                and no default value is provided.
        """
        value = self.get(key, default)
        if not isinstance(value, str):
            return value
        
        return [part.strip() for part in value.split(sep)]
    
    def get_boolean(self, key, default=_undefined):
        """get boolean value associated with the key

        :param key: the key for which to look up the value
        :param default: default value if the key is not found. This can be
                        any value, but when provided as a `str`, it is parsed
                        as if read from the configuration, otherwise it is
                        returned as it is.
        :raise: :class:`PropertyLookupError` if the key is not found
                and no default value is provided.
        """
        value = self.get(key, default)

        if not isinstance(value, str):
            return value

        if value in ("True", "true", "yes", "on", "1"):
            return True
        elif value in ("False", "false", "no", "off", "0"):
            return False
        else:
            raise PropertyValueError("can't parse boolean from: %s" % value)
    
    def __getitem__(self, key):
        """get the value associated with the key

        :param key: the key for which to look up the value
        :raise: :class:`PropertyLookupError` if the key is not found
                and no default value is provided.
        """
        full_key = self._prefix + key
        try:
            return self._values[full_key]
        except LookupError:
            raise PropertyLookupError(full_key)
    
    def filter(self, prefix):
        """apply a prefix to the key lookups

        :param prefix: the prefix to apply
        :return: a new :class:`Properties` instance with the specified prefix
        """
        return Properties(self._values, prefix=self._prefix + prefix)
    
    def get_keys(self):
        """get available keys

        :return: list of keys matching for current prefix
        """
        result = []
        for key in self._values:
            if key.startswith(self._prefix):
                result.append(key[len(self._prefix):])
        return result
            
    def get_full_key(self, key):
        """get a full key corresponding to this 'filtered' key
        """
        return self._prefix + key
    
    @classmethod
    def load(cls, path):
        """Loads a property file
        :param path: the property file to read
        :return: a new :class:`Properties` instance 
        """
        with open(path) as fp:
            return Properties(jprops.load_properties(fp))
