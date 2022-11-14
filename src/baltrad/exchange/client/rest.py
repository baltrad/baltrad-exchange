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
import base64
import uuid
from datetime import datetime
import hashlib

from http import client as httplibclient

from baltrad.exchange.crypto import keyczarcrypto

try:
    import tink
    from tink import cleartext_keyset_handle
    from tink import signature
except:
    pass

from baltrad.exchange import crypto

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
    
    def server_url(self):
        return self._server_url_str
    
    def store(self, data):
        """stores the data in the exchange server.
        :param data: The data
        """
        request = Request(
            "POST", "/file/", data.read(),
            headers={
                "content-type": "application/x-hdf5",
                "message-id": str(uuid.uuid4()),
                "date":datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
            }
        )

        response = self.execute_request(request)
        
        if response.status == httplibclient.OK:
            return True
        else:
            raise RuntimeError(
                "Unhandled response code: %s" % response.status
            )

    def post_json_message(self, json_message):
        """posts a json message to the exchange server. 
        :param data: The data
        """
        request = Request(
            "POST", "/json_message/", json_message,
            headers={
                "content-type": "application/json",
                "message-id": str(uuid.uuid4()),
                "date":datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
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
            basepath = "/"
            subpath = req.path
            if self._server_url.path:
                basepath = self._server_url.path
            if subpath.startswith("/"):
                subpath=subpath[1:]
            path = os.path.join(basepath, subpath)
            conn.request(req.method, path, req.data, req.headers)
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

class CryptoAuth(Auth):
    """authenicate by signing messages with internal crypto-functionality
    """
    def __init__(self, signer, nodename):
        if isinstance(signer, crypto.private_key):
            self._signer = signer
        elif isinstance(signer, str):
            self._signer = crypto.load_key(signer)
            if not isinstance(self._signer, crypto.private_key):
                raise Exception("Can't use key: %s for signing"%signer)
        else:
            raise Exception("Unknown signer format")
        self._nodename = nodename

    def add_credentials(self, req):
        signable = create_signable_string(req)
        signature = self._signer.sign(signable)
        auth = "exchange-crypto %s:%s" % (self._nodename, signature)
        req.headers["authorization"] = auth

class TinkAuth(Auth):
    """authenicate by signing messages with Tink
    """
    def __init__(self, key_path, key_name=None):
        signature.register()
        with open(key_path, "rt") as kf:
            handle = cleartext_keyset_handle.read(tink.JsonKeysetReader(kf.read()))
            self._signer = handle.primitive(signature.PublicKeySign)

        if key_name:
            self._key_name = key_name
        else:
            self._key_name = os.path.basename(os.path.dirname(key_path))

    def add_credentials(self, req):
        signable = create_signable_string(req)
        signature = self._signer.sign(bytes(signable, "utf-8"))
        signature = str(base64.b64encode(signature), "utf-8")
        auth = "exchange-tink %s:%s" % (self._key_name, signature)
        req.headers["authorization"] = auth

def create_signable_string(req):
    """construct a signable string from a :class:`.Request`

    See :ref:`doc-rest-authentication` for details.
    """
    fragments = [req.method]
    for key in ("content-md5", "content-type", "date", "message-id"):
        if key in req.headers:
            value = req.headers[key].strip()
            if value:
                fragments.append(value)

    return "\n".join(fragments)
