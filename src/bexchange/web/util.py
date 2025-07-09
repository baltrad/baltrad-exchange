# Copyright 2010-2011 Estonian Meteorological and Hydrological Institute
# 
# This file is part of baltrad-db.
# 
# baltrad-db is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# baltrad-db is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public License
# along with baltrad-db. If not, see <http://www.gnu.org/licenses/>.

import json
import sys

if sys.version_info < (3,):
    import httplib as httplibclient
    import urlparse
else:
    from http import client as httplibclient
    import urllib.parse as urlparse


from werkzeug.wrappers import Request as WerkzeugRequest
from werkzeug.wrappers import Response as WerkzeugResponse

from werkzeug.exceptions import HTTPException

class JsonRequestMixin(object):
    """Request mixin providing JSON-decoding of request body
    """
    
    def get_json_data(self):
        """try JSON decoding :attr:`self.data`

        :return: the decoded data
        :raise: :class:`HttpBadRequest` if decoding fails
        """
        try:
            jdata = self.data
            if isinstance(jdata, bytes):
                jdata = jdata.decode('utf-8')
            return json.loads(jdata)
        except ValueError:
            raise HttpBadRequest("invalid json: " + self.data)

class Request(WerkzeugRequest,
              JsonRequestMixin):
    def __init__(self, environ, max_content_length=None, max_form_memory_size=None):
        WerkzeugRequest.__init__(self, environ)
        self.max_content_length = max_content_length
        self.max_form_memory_size = max_form_memory_size


class RequestContext(object):
    def __init__(self, request, backend, provider):
        self.enable_remove_all_files = False
        self.request = request
        self.backend = backend
        self.provider = provider
    
    def is_anonymous(self):
        if self.provider != None and self.provider != "noauth":
            return False
        return True
    
    def make_url(self, path):
        return "/" + path

class Response(WerkzeugResponse):
    def __init__(self, response, content_type="text/plain", status=httplibclient.OK):
        WerkzeugResponse.__init__(
            self, response,
            content_type=content_type,
            status=status
        )

class NoContentResponse(WerkzeugResponse):
    def __init__(self):
        WerkzeugResponse.__init__(self, None, status=httplibclient.NO_CONTENT)

class TemporaryRedirectResponse(WerkzeugResponse):
    def __init__(self, newlocation):
        WerkzeugResponse.__init__(self, None, status=httplibclient.TEMPORARY_REDIRECT)
        self.location = newlocation

class PermanentRedirectResponse(WerkzeugResponse):
    def __init__(self, newlocation):
        WerkzeugResponse.__init__(self, None, status=httplibclient.PERMANENT_REDIRECT)
        self.location = newlocation

class JsonResponse(WerkzeugResponse):
    def __init__(self, response, status=httplibclient.OK):
        if not isinstance(response, str):
            response = json.dumps(response, allow_nan=False, sort_keys=True)
        
        WerkzeugResponse.__init__(
            self, response,
            content_type="application/json",
            status=status,
        )

class HttpBadRequest(HTTPException):
    code = httplibclient.BAD_REQUEST
    def __init__(self, description=None, response=None):
        HTTPException.__init__(self, description, response)

class HttpNotFound(HTTPException):
    code = httplibclient.NOT_FOUND
    def __init__(self, description=None, response=None):
        HTTPException.__init__(self, description, response)
    
class HttpConflict(HTTPException):
    code = httplibclient.CONFLICT
    def __init__(self, description=None, response=None):
        HTTPException.__init__(self, description, response)

class HttpNotAcceptable(HTTPException):
    code = httplibclient.NOT_ACCEPTABLE
    def __init__(self, description=None, response=None):
        HTTPException.__init__(self, description, response)

class HttpUnauthorized(HTTPException):
    """401 Unauthorized

    :param challenge: a string to reply in *www-authenticate* header. If given
                      as a sequence of strings, multiple *www-authenticate*
                      headers will be set in the response.
    """
    code = httplibclient.UNAUTHORIZED

    def __init__(self, challenge):
        HTTPException.__init__(self)
        if isinstance(challenge, str):
            challenge = [challenge]
        self._challenges = challenge
    
    def get_headers(self, environ, scope = None):
        headers = HTTPException.get_headers(self, environ)
        for challenge in self._challenges:
            headers.append(("www-authenticate", challenge))
        return headers

class HttpForbidden(HTTPException):
    code = httplibclient.FORBIDDEN
    def __init__(self, description=None, response=None):
        HTTPException.__init__(self, description, response)

