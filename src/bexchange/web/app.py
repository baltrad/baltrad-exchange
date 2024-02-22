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

## The actual app server dispatcher

## @file
## @author Anders Henja, SMHI
## @date 2021-08-18

from werkzeug import serving, exceptions as wzexc
import urllib.parse as urlparse

from bexchange import auth
from bexchange.web import routing
from bexchange.web import util as webutil
from bexchange.web import auth as webauth
from bexchange.server import backend

import logging
logger = logging.getLogger("baltard.exchange.app")

class Application(object):
    def __init__(self, backend):
        self.url_map = routing.URL_MAP
        self.backend = backend
    
    def dispatch_request(self, request, provider):
        adapter = self.url_map.bind_to_environ(request.environ)
        ctx = webutil.RequestContext(request, self.backend, provider)
        try:
            endpoint, values = adapter.match()
            handler = routing.get_handler(endpoint)
            return handler(ctx, **values)
        except wzexc.HTTPException as e:
            logger.warning("HTTPException occured: %s", e)
            return e
        except Exception as e:
            logger.exception("Unknown exception")
            raise

    def get_backend(self):
        return self.backend
    
    def __call__(self, env, start_response, provider):
        request = webutil.Request(env, self.backend.max_content_length, self.backend.max_content_length)
        response = self.dispatch_request(request, provider)
        return response(env, start_response)
    
    @classmethod
    def from_conf(cls, conf):
        """create instance from configuration.
        :param conf: a :class:`~.config.Properties` instance to configure
                     from
        """
        result = Application(backend.SimpleBackend.from_conf(conf))
        return result

def from_conf(conf):
    """create the entire WSGI application from conf
    this will wrap the application with necessary middleware
    """
    app = Application.from_conf(conf)
    authmw = webauth.AuthMiddleware(app, app.get_backend().get_auth_manager())
    return authmw
 
def serve(uri, app):
    """serve the application using werkzeug
    """

    uri = urlparse.urlparse(uri)
    host = uri.hostname
    port = uri.port or 80

    serving.run_simple(host, port, app) 

