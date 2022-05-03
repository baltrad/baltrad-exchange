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

from tink import signature
from tink import core
from tink import cleartext_keyset_handle
import tink
from baltrad.exchange.auth import coreauth
import os
import base64
import json

import logging

logger = logging.getLogger("baltard.exchange.auth")

class TinkAuth(coreauth.Auth):
    """Provide authentication through Tink

        registered as *tink* in *baltrad.bdbserver.web.auth* entry-point
    """
    def __init__(self, tink_root):
        """
        :param keystore_root: default path to search keys from
        """
        if not os.path.isabs(tink_root):
            raise ValueError("tink_root must be an absolute path")
        self._tink_root = tink_root
        self._private_key = None
        self._verifiers = {}
    
    def add_key_config(self, conf):
        handle = cleartext_keyset_handle.read(tink.JsonKeysetReader(json.dumps(conf["key"])))
        verifier = handle.primitive(signature.PublicKeyVerify)
        self._verifiers[conf["name"]] = verifier
    
    def add_key(self, name, path):
        """
        :param name: the name to associate the key with for lookups
        :param path: an absolute or relative path to the key.

        :raise: :class:`tink.TinkError` if the key can not be read

        creates a :class:`public key verifier` from the key located at
        *path*
        """
        if not os.path.isabs(path):
            path = os.path.join(self._tink_root, path)
            
        logger.info("adding key %s from %s", name, path)
        
        with open(path, "rt") as kf:
            handle = cleartext_keyset_handle.read(tink.JsonKeysetReader(kf.read()))

        verifier = handle.primitive(signature.PublicKeyVerify)
        self._verifiers[name] = verifier
    
    def authenticate(self, req, credentials):
        try:
            keyname, sig = credentials.rsplit(":")
        except ValueError:
            raise coreauth.AuthError("invalid credentials: %s" % credentials)
        try:
            verifier = self._verifiers[keyname]
        except tink.TinkError:
            raise coreauth.AuthError("no verifier for key: %s" % keyname)
        
        signable = self.create_signable_string(req)
        signable = bytes(signable, "utf-8")
        
        try:
            result = verifier.verify(base64.b64decode(sig), signable)
            return True
        except tink.TinkError as e:
            logger.exception("unhandled TinkError %s", e.__str__())
            return False

    def create_signable_string(self, req):
        """construct a signable string from a :class:`~.util.Request`

        See :ref:`doc-rest-authentication` for details.
        """
        fragments = [req.method, req.path]
        for key in ("content-md5", "content-type", "date"):
            if key in req.headers:
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
        signature.register()
        conf = conf.filter("baltrad.exchange.auth.tink.")
        
        result = TinkAuth(conf.get("root"))
        keyconf = conf.filter("keys.")
        for key in keyconf.get_keys():
            result.add_key(key, keyconf.get(key))
            
        result._private_key = conf.get("private.key")

        return result
