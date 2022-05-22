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
        if conf["auth"] in self._providers:
            self.get_provider(conf["auth"]).add_key_config(conf["conf"])

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
    def add_json_config(self, json):
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
