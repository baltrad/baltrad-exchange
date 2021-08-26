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

## Authentication functionality

## @file
## @author Anders Henja, SMHI
## @date 2021-08-18
import abc
import logging
import pkg_resources
import os

from keyczar import (
    errors as kzerrors,
    keyczar,
)

from baltrad.exchange import util
from baltrad.exchange import config
from baltrad.exchange.web import util as webutil

logger = logging.getLogger("baltard.exchange.auth")

class AuthError(Exception):
    """expected authentication errors
    """
    pass

class AuthMiddleware(object):
    """WSGI middleware providing authentication. Actual authentication is
    delegated to an :class:`~.Auth` implementation registered as a *provider*
    here.
    
    The provider and credentials are extracted using :func:`get_credentials`.

    :param app: the WSGI application receiving the request if authentication
                is successful.
    """

    def __init__(self, app):
        self._providers = {}
        self.app = app
        
    def authenticate(self, req):
        """authenticate a :class:`~.util.Request`
        """
        try:
            provider_key, credentials = get_credentials(req)
        except AuthError as e:
            logger.error("failed to parse authorization credentials: %s" % e)
            return False

        try:
            provider = self._providers[provider_key]
        except LookupError:
            logger.error("auth provider not available: %s" % provider_key)
            return False
        
        logger.debug("authenticating with %s: %s", provider_key, credentials)
        try:
            return provider.authenticate(req, credentials)
        except AuthError as e:
            logger.warning("authentication failed: %s", e)
        except Exception as e:
            logger.exception("unhandled error while authenticating %s", e)
        return False
    
    def add_provider(self, name, provider):
        """add an authentication provider
        """
        self._providers[name] = provider
    
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
    
    def __call__(self, env, start_response):
        req = webutil.Request(env)
        if self.authenticate(req):
            logger.debug("Authenticated and invoking self.app with %s"%str(start_response))
            return self.app(env, start_response)
        else:
            challenge = ["exchange-" + key for key in self._providers]
            return webutil.HttpUnauthorized(challenge)(env, start_response)
    
    @classmethod
    def from_conf(cls, app, conf):
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
            logger.warning(
                "No authorization provider(s) supplied, defaulting to 'noauth'"
            )
            providers = ["noauth"]

        result = AuthMiddleware(app)
        for provider in providers:
            try:
                result.add_provider_from_conf(provider, conf)
            except LookupError:
                raise config.Error("could not create provider: %s" % provider)
                
        return result

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
            "baltrad.exchange.web.auth",
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

class KeyczarAuth(Auth):
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
    
    def authenticate(self, req, credentials):
        try:
            keyname, signature = credentials.rsplit(":")
        except ValueError:
            raise AuthError("invalid credentials: %s" % credentials)
        try:
            verifier = self._verifiers[keyname]
        except KeyError:
            raise AuthError("no verifier for key: %s" % keyname)
        signed_str = create_signable_string(req)
        try:
            result = verifier.Verify(signed_str, signature)
            return result
        except kzerrors.KeyczarError as e:
            logger.exception("unhandled Keyczar error %s", e.__str__())
            return False

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
        return result
    
def get_credentials(req):
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
        raise AuthError("invalid Authorization header: %s" % authstr)
    provider = provider.strip()
    if not provider.startswith("exchange-"):
        raise AuthError(
            "invalid auth provider in Authorization header: %s" % provider
        )
    else:
        provider = provider[9:]
    return provider, credentials.strip()

def create_signable_string(req):
    """construct a signable string from a :class:`~.util.Request`

    See :ref:`doc-rest-authentication` for details.
    """
    fragments = [req.method, req.path]
    for key in ("content-md5", "content-type", "date"):
        if req.headers.has_key(key):
            value = req.headers[key].strip()
            if value:
                fragments.append(value)

    return "\n".join(fragments)
