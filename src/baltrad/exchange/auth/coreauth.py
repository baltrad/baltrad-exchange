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

import abc
import logging
import pkg_resources
import os

from baltrad.exchange import util
from baltrad.exchange import config
from baltrad.exchange import crypto

logger = logging.getLogger("baltard.exchange.auth")

class AuthError(Exception):
    """expected authentication errors
    """
    pass

class auth_manager(object):
    def __init__(self):
        self._providers = {}

    def authenticate(self, req):
        """authenticate a :class:`~.util.Request`
        """
        try:
            provider_key, credentials = self.get_credentials(req)
        except AuthError as e:
            logger.error("failed to parse authorization credentials: %s" % e)
            return False, None

        logger.debug("provider_key=%s, credentials=%s"%(provider_key, credentials))
        try:
            provider = self._providers[provider_key]
        except LookupError:
            logger.error("auth provider not available: %s" % provider_key)
            return False, None

        logger.debug("authenticating with %s: %s", provider_key, credentials)
        try:
            return provider.authenticate(req, credentials), provider_key
        except AuthError as e:
            logger.warning("authentication failed: %s", e)
        except Exception as e:
            logger.exception("unhandled error while authenticating %s", e)
        return False, None
    
    def get_credentials(self, req):
        """get authorization credentials from a :class:`~.util.Request`

        :raise: :class:`~.AuthError` if the authorization header is illegally
                formed (for the purposes of Baltrad-BDB)
        :return: a 2-tuple of provider and credential strings extracted from the
                 header
        
        See :ref:`doc-rest-authentication` for details.
    
        Note that ("noauth", None) is returned if authorization header is missing.
        """
        try:
            authstr = req.headers["authorization"]
        except LookupError:
            return ("noauth", None)

        try:
            provider, credentials = authstr.split(" ")
        except ValueError:
            if "Node-Name" in req.headers and req.base_url.endswith("post_file.htm"):
                provider = "exchange-keyczar" # Backward compatibility
                credentials = authstr
            else: 
                raise AuthError("invalid Authorization header: %s" % authstr)
        
        provider = provider.strip()
        if not provider.startswith("exchange-"):
            raise AuthError(
                "invalid auth provider in Authorization header: %s" % provider
            )
        else:
            provider = provider[9:]
        return provider, credentials.strip()
    
    def get_nodename(self, req):
        """Returns the node name from the credentials / request
        :param req: The request
        :return the nodename if found, otherwise None
        """
        provider, credentials = self.get_credentials(req)
        # Currently we know that node name always exist in the credentials so take it from there
        if credentials and credentials.find(":") > 0:
            return credentials.split(":")[0]
        return None
        
    @classmethod
    def from_conf(cls, conf):
        """
        :param app: the WSGI application receiving the request if
                    authenication is successful.
        :param conf: a :class:`~.config.Properties` instance to configure
                       from
        """
        providers_key = "baltrad.exchange.auth.providers"
        try:
            providers = conf.get_list(providers_key, sep=",")
        except config.PropertyLookupError:
            logger.warning("No authorization provider(s) supplied, defaulting to 'noauth'")
            providers = ["noauth"]

        result = auth_manager()
        for provider in providers:
            try:
                result.add_provider_from_conf(provider, conf)
            except LookupError:
                raise config.Error("could not create provider: %s" % provider)
        #privatekey = conf.get("baltrad.exchange.key.private", default="/etc/baltrad/exchange/keys/%s.priv"%nodename)

        return result    

    def add_provider_from_conf(self, name, conf):
        """load an :class:`Auth` implementation and add it as a provider

        :param name: the name of the :class:`Auth` implementation to load
        :param conf: a :class:`~.config.Properties` instance to configure
                     from
        :raise: `LookupError` if an implementation with this name doesn't
                exist
        """
        provider_cls = Auth.get_impl(name)
        provider = provider_cls.from_conf(conf)
        self._providers[name] = provider
        logger.info("Added provider: %s as %s"%(provider, name))

    def add_key_config(self, conf):
        """Adds a key from key config
        :param conf: The key config
        :return the node name this key should be associated with
        """ 
        if conf["auth"] in self._providers:
            return self.get_provider(conf["auth"]).add_key_config(conf["conf"])
        return None

    def get_provider(self, name):
        return self._providers[name]

    def get_private_key(self, _type):
        return self._privatekeys[_type]

    def get_providers(self):
        return self._providers

class Auth(object):
    """interface for authentication providers
    """
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def authenticate(self, req, credentials):
        """authenticate the request with provided crendentials

        :param req: the request to authenticate
        :type req: :class:`~.util.Request`
        :param credentials: implementation specific credential string
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def add_key_config(self, jsonstr):
        """Adds a key config to this provider
        :param jsonstr: THe key config
        :return the nodename this key should be associated with
        """
        raise NotImplementedError()

    @util.abstractclassmethod
    def from_conf(cls, conf):
        """construct an instance from configuration

        :param conf: a :class:`~.config.Properties` instance
        """
        raise NotImplementedError()
    
    @classmethod
    def get_impl(cls, name):
        return pkg_resources.load_entry_point(
            "baltrad.exchange",
            "baltrad.exchange.auth",
            name
        )
    
class NoAuth(Auth):
    """No authentication, allow everyone

    registered as *noauth* in *baltrad.bdbserver.web.auth* entry-point
    """
    def authenticate(self, req, credentials):
        return True
    
    @classmethod
    def from_conf(cls, conf):
        return NoAuth()

class CryptoAuth(Auth):
    """Provide authentication through the internal crypto

        registered as *exchange-crypto* in *baltrad.bdbserver.web.auth* entry-point
    """
    def __init__(self, key_root):
        """
        :param key_root: default path to search keys from
        """
        if not os.path.isabs(key_root):
            raise ValueError("key_root must be an absolute path")
        self._key_root = key_root
        self._private_key = None
        self._verifiers = {}
    
    def setPrivateKey(self, privkey, nodename=None):
        if privkey and not os.path.exists(privkey):
            raise Exception("If providing a private key it must point at a valid file")
        self._private_key = privkey
        if self._private_key and nodename:
            privkey = crypto.load_key(self._private_key)
            if nodename not in self._verifiers:
                logger.info("adding public key from private for %s", nodename)
                self._verifiers[nodename] = privkey.publickey()

    def getPublicKey(self, nodename):
        return self._verifiers[nodename]

    def add_key_config(self, conf):
        if "creator" in conf and conf["creator"] == "baltrad.exchange.crypto":
            if conf["type"] == "public":
                if "pubkey" in conf:
                    if not os.path.isabs(conf["pubkey"]):
                        key = crypto.load_key("%s/%s"%(self._key_root, conf["pubkey"]))
                    else:
                        key = crypto.load_key(conf["pubkey"])
                else:                    
                    key = crypto.import_key(conf["key"])

                if conf["nodename"] not in self._verifiers:
                    logger.info("adding key config %s", conf["nodename"])
                    self._verifiers[conf["nodename"]] = key

                return conf["nodename"]
            else:
                raise AuthError("Exchange auth expects public keys")
        else:
            raise AuthError("Could not handle config")
    
    def add_key(self, name, path):
        """
        :param name: the name to associate the key with for lookups
        :param path: an absolute or relative path to the key.

        :raise: :class:`Exception` if the key can not be read

        creates a :class:`public key verifier` from the key located at
        *path*
        """
        if not os.path.isabs(path):
            path = os.path.join(self._key_root, path)
            
        logger.info("adding key %s from %s", name, path)
        
        key = crypto.load_key(path)
        if not isinstance(key, crypto.public_key):
            raise AuthError("Exchange auth expects public keys")
        self._verifiers[name] = key
    
    def authenticate(self, req, credentials):
        logger.debug("CryptoAuth - authenticate: %s"%credentials)
        try:
            keyname, sig = credentials.rsplit(":")
        except ValueError:
            raise AuthError("invalid credentials: %s" % credentials)

        try:
            verifier = self._verifiers[keyname]
        except Exception:
            raise AuthError("no verifier for key: %s" % keyname)

        try:
            result = verifier.verify(self.create_signable_string(req), sig)
            return result
        except Exception as e:
            logger.exception("Failed to verify message")

        return False

    def create_signable_string(self, req):
        """construct a signable string from a :class:`~.util.Request`

        See :ref:`doc-rest-authentication` for details.
        """
        fragments = [req.method]
        for key in ("content-md5", "content-type", "date", "message-id"):
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
        cconf = conf.filter("baltrad.exchange.auth.crypto.")
        
        result = CryptoAuth(cconf.get("root"))
        keyconf = cconf.filter("keys.")
        for key in keyconf.get_keys():
            result.add_key(key, keyconf.get(key))
        
        result.setPrivateKey(cconf.get("private.key"), conf.get("baltrad.exchange.node.name"))

        return result