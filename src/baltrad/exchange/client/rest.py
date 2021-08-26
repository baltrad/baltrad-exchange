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

## Rest client API

## @file
## @author Anders Henja, SMHI
## @date 2021-08-18
from abc import abstractmethod, ABCMeta
import abc
import json
import os
import socket
import urllib.parse as urlparse
import pkg_resources
import ssl

from http import client as httplibclient
from keyczar import keyczar

class Request(object):
    def __init__(self, method, path, data=None, headers={}):
        self.method = method
        self.path = path
        self.data = data
        self.headers = headers

class RestfulServer(object):
    """Access database over the RESTful interface
    """
    def __init__(self, server_url, auth):
        self._server_url_str = server_url
        self._server_url = urlparse.urlparse(server_url)
        self._auth = auth
    
    def store(self, data):
        """stores the data in the exchange server.
        :param data: The data
        """
        request = Request(
            "POST", "/file/", data.read(),
            headers={
                "content-type": "application/x-hdf5",
            }
        )

        response = self.execute_request(request)
        
        if response.status == httplibclient.OK:
            return True
        else:
            raise RuntimeError(
                "Unhandled response code: %s" % response.status
            )

    def execute_request(self, req):
        """Exececutes the actual rest request over http or https. Will also add credentials to the request
        :param req: The REST request
        """
        conn = None
        if self._server_url.scheme == "https":
            conn = httplibclient.HTTPSConnection(
                self._server_url.hostname,
                self._server_url.port,
                context = ssl._create_unverified_context()) # TO ignore problems related to certificate chains etc..
        else:
            conn = httplibclient.HTTPConnection(
                self._server_url.hostname,
                self._server_url.port)
        self._auth.add_credentials(req)
        try:
            conn.request(req.method, req.path, req.data, req.headers)
        except socket.error:
            raise RuntimeError(
                "Could not send request to %s" % self._server_url_str
            )
        return conn.getresponse()

class Auth(object):
    __meta__ = abc.ABCMeta

    @abc.abstractmethod
    def add_credentials(self, req):
        """add authorization credentials to the request

        :param req: a :class:`Request` to update
        """
        raise NotImplementedError()

class NoAuth(Auth):
    """no authentication
    """
    def add_credentials(self, req):
        pass

class KeyczarAuth(Auth):
    """authenicate by signing messages with Keyczar
    """
    def __init__(self, key_path, key_name=None):
        self._signer = keyczar.Signer.Read(key_path)
        if key_name:
            self._key_name = key_name
        else:
            self._key_name = os.path.basename(key_path)

    def add_credentials(self, req):
        signable = create_signable_string(req)
        signature = self._signer.Sign(signable)
        auth = "exchange-keyczar %s:%s" % (self._key_name, signature)
        req.headers["authorization"] = auth

def create_signable_string(req):
    """construct a signable string from a :class:`.Request`

    See :ref:`doc-rest-authentication` for details.
    """
    fragments = [req.method, req.path]
    for key in ("content-md5", "content-type", "date"):
        if key in req.headers:
            value = req.headers[key].strip()
            if value:
                fragments.append(value)

    return "\n".join(fragments)