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

## Authentication handling within baltrad-exchange

## @file
## @author Anders Henja, SMHI
## @date 2022-05-02

import os
import logging
from baltrad.exchange.auth import coreauth

from keyczar import (
    errors as kzerrors,
    keyczar,
)

logger = logging.getLogger("baltard.exchange.auth")


class KeyczarAuth(coreauth.Auth):
    """Provide authentication through Keyczar

    registered as *keyczar* in *baltrad.bdbserver.web.auth* entry-point
    """
    def __init__(self, keystore_root):
        """
        :param keystore_root: default path to search keys from
        """
        if not os.path.isabs(keystore_root):
            raise ValueError("keystore_root must be an absolute path")
        self._keystore_root = keystore_root
        self._private_key = None
        self._verifiers = {}
    
    def add_key(self, name, path):
        """
        :param name: the name to associate the key with for lookups
        :param path: an absolute or relative path to the key.

        :raise: :class:`keyczar.errors.KeyczarError` if the key can not be read

        creates a :class:`keyczar.keyczar.Verifier` from the key located at
        *path*
        """
        if not os.path.isabs(path):
            path = os.path.join(self._keystore_root, path)
        logger.info("adding key %s from %s", name, path)
        verifier = keyczar.Verifier.Read(path)
        self._verifiers[name] = verifier
    
    def add_key_config(self, conf):
        logger.info("KeyczarAuth does not implement add_key_config")
    
    def authenticate(self, req, credentials):
        try:
            keyname, signature = credentials.rsplit(":")
        except ValueError:
            raise coreauth.AuthError("invalid credentials: %s" % credentials)
        try:
            verifier = self._verifiers[keyname]
        except KeyError:
            raise coreauth.AuthError("no verifier for key: %s" % keyname)

        signed_str = self.create_signable_string(req)
        try:
            result = verifier.Verify(signed_str, signature)
            return result
        except kzerrors.KeyczarError as e:
            logger.exception("unhandled Keyczar error %s", e.__str__())
            return False

    def create_signable_string(self, req):
        """construct a signable string from a :class:`~.util.Request`

        See :ref:`doc-rest-authentication` for details.
        """
        fragments = [req.method, req.url]
        for key in ("content-type", "content-md5", "date"):
            if req.headers.has_key(key):
                value = req.headers[key].strip()
                if value:
                    fragments.append(value)
        return "\n".join(fragments)

    @classmethod
    def from_conf(cls, conf):
        """Create from configuration.

        :param conf: a :class:`~.config.Properties` instance
        :raise: :class:`LookupError` if a required configuration parameter
                is missing.

        All keys are accessed with prefix *baltrad.bdb.server.auth.keyczar.*.
        The value of `keystore_root` is passed to the constructor. All values
        under `keys` are passed to :meth:`add_key` where the configuration
        key is used as a name and the value is used as the path for the key
        lookup.
        """
        conf = conf.filter("baltrad.exchange.auth.keyczar.")
        
        result = KeyczarAuth(conf.get("keystore_root"))
        keyconf = conf.filter("keys.")
        for key in keyconf.get_keys():
            result.add_key(key, keyconf.get(key))
            
        result._private_key = conf.get("private.key")
            
        return result
