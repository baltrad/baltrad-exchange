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

from bexchange import util
from bexchange import config
from bexchange import auth
from bexchange.web import util as webutil

logger = logging.getLogger("baltard.exchange.web.auth")

class AuthMiddleware(object):
    """WSGI middleware providing authentication. Actual authentication is
    delegated to an :class:`~.coreauth.Auth` implementation registered as a *provider*
    here.
     
    The provider and credentials are extracted using :func:`get_credentials`.
 
    :param app: the WSGI application receiving the request if authentication
                is successful.
    """
 
    def __init__(self, app, authmgr):
        self.authmgr = authmgr
        self.app = app
    
    def authenticate(self, req):
        """authenticate a :class:`~.util.Request`
        """
        return self.authmgr.authenticate(req)

    def __call__(self, env, start_response):
        req = webutil.Request(env)
        authenticated, provider = self.authenticate(req) 
        if authenticated and provider is not None:
            return self.app(env, start_response, provider)
        else:
            challenge = ["exchange-" + key for key in self.authmgr.get_providers()]
            return webutil.HttpUnauthorized(challenge)(env, start_response)
