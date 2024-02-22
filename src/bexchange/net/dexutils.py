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

## Provides some utilities for communicating with a dex instance

## @file
## @author Anders Henja, SMHI
## @date 2021-12-01
import zipfile, datetime, base64, io, ssl
import urllib.parse as urlparse
import http.client as httplib

from baltradcrypto.crypto import keyczarcrypto

class dexutils(object):
    def __init__(self, remoteuri, nodename):
        self._remoteuri = remoteuri
        self._nodename = nodename
  
    def _split_uri(self, uri):
        """Splits an uri to the individual parts.
        :param uri: The uri to be split
        :return: tuple of scheme, host and query
        """
        urlparts = urlparse.urlsplit(uri)
        scheme = urlparts[0]
        host = urlparts[1]
        query = urlparts[2]    
        return (scheme, host, query)
  
    def _post(self, scheme, host, query, data, headers):
        """Posts the message to the recipient.
        :param scheme: The scheme to use, https or http
        :param host: the host that should be connected to (including port)
        :param query: the query data
        :param data: the data to be added to message
        :param headers: the headers to add to message
        :return: a tuple of status, reason and any data
        """
        if scheme == "https":
            conn = httplib.HTTPSConnection(host, context = ssl._create_unverified_context())
        else:
            conn = httplib.HTTPConnection(host)

        try:
            conn.request("POST", query, data, headers)
            response = conn.getresponse()
        except Exception as e:
            raise Exception("Failed to post message to: %s"%self._nodename, e)
        finally:
            conn.close();
      
        return response.status, response.reason, response.read()
  
    def send_key(self, pubkeyfolder):
        """Sends the public key folder to the remote server using the dex protocol.
        :param pubkeyfolder: path to public folder that should be sent
        """
        verifier = keyczarcrypto.load_key(opts.pubkey)
        if not isinstance(verifier, keyczarcrypto.keyczar_verifier):
            raise Exception("You shouldn't provide the private key when sending a key to a remote server")

        uri = "%s/BaltradDex/post_key.htm"%self._remoteuri
        (scheme, host, query) = self._split_uri(uri)
 
        datestr = datetime.datetime.now().strftime("%a, %e %B %Y %H:%M:%S")

        headers = {"Node-Name": self._nodename, 
                   "Content-Type": "application/zip",
                   "DEX-Protocol-Version": "2.1",
                   "Date": datestr}

        iob = io.BytesIO()
        with zipfile.ZipFile(iob, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write("%s/meta"%pubkeyfolder, "meta")
            zipf.write("%s/1"%pubkeyfolder, "1")

        iob.seek(0)
        data = iob.read()

        headers["Content-MD5"] =  base64.b64encode(data)
        try:
            status, reason, msg = self._post(scheme, host, query, data, headers)
            if status == 200:
                print("Key sent to: %s"%self._remoteuri)
            else:
                print("Failed to send key. Status=%d, reason=%s"%(status, reason))
        finally:
            pass

    def send_file(self, privkeyfolder, hdf5file):
        """Sends the file to the dex server
        :param file: path to file that should be sent
        :param meta: the meta object for all metadata of file
        """
        signer = keyczarcrypto.load_key(privkeyfolder)
        if not isinstance(signer, keyczarcrypto.keyczar_signer):
            raise Exception("You need to use the private key when signing a message")

        uri = "%s/BaltradDex/post_file.htm"%self._remoteuri
        (scheme, host, query) = self._split_uri(uri)

        datestr = datetime.datetime.now().strftime("%a, %e %B %Y %H:%M:%S")
        contentMD5 = base64.b64encode(uri.encode("utf-8"))
        message = ("POST" + '\n' + uri + '\n' + "application/x-hdf5" + '\n' + str(contentMD5, "utf-8") + '\n' + datestr)
        signature = signer.sign(message)
        headers = {"Node-Name": self._nodename, 
                   "Content-Type": "application/x-hdf5",
                   "Content-MD5": contentMD5, 
                   "Date": datestr, 
                   "Authorization": self._nodename + ':' + signature}

        fp = open(hdf5file, 'rb')
    
        try:
            status, reason, msg = self._post(scheme, host, query, fp.read(), headers)
            if status == 200:
                print("Sent %s to %s"%(hdf5file, self._remoteuri))
            else:
                print("Failed to send file. Status=%d, reason=%s, msg=%s"%(status, reason, msg))
        finally:
            fp.close()      