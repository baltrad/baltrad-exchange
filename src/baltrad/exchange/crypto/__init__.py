# Copyright (C) 2022- Swedish Meteorological and Hydrological Institute (SMHI)
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
## We wrap standard crypto-stuff to be used for default signature handling so that we can avoid the
# hassle when a crypto library is too old and to young. This means that unless otherwise specified the
# signature protocol used between nodes should always be DSA 2048

## @file
## @author Anders Henja, SMHI
## @date 2022-10-18
"""Internal default private/public key support for managing the signature handling in messages
"""
import logging
import binascii
import hashlib
import base64
import struct

try:
    from Cryptodome.PublicKey import DSA, RSA
    from Cryptodome.Signature import DSS, pkcs1_15
    from Cryptodome.Hash import SHA256
except:
    from Crypto.PublicKey import DSA, RSA
    from Crypto.Signature import DSS, PKCS1_v1_5
    from Crypto.Hash import SHA256

BIG_ENDIAN_INT_SPECIFIER = ">i"
BIG_ENDIAN_LONG_LONG_SPECIFIER = ">q"

logger = logging.getLogger("baltard.exchange.crypto")

class public_key(object):
    """Public Key
    """
    def __init__(self, key):
        """Constructor
        :param key: The crypto key
        """
        super(public_key, self).__init__()
        self._key = key

    def PEM(self):
        """Returns the public key as PEM-encoded string
        """
        return self._key.export_key("PEM").decode()

    def algorithm(self):
        if isinstance(self._key, RSA.RsaKey):
            return "rsa"
        elif isinstance(self._key, DSA.DsaKey):
            return "dsa"

        return "unknown"

    def exportPEM(self, filename):
        """Exports the public key to specified filename
        :param filename: The name of the file to be written
        """
        with open(filename, "w") as fp:
            fp.write(self.PEM())
    
    def exportJSON(self, filename, nodename):
        """Exports the public key to specified filename as a JSON entry
        :param filename: The name of the file to be written
        """
        import json
        keyType = "dsa"
        if isinstance(self._key, RSA.RsaKey):
            keyType = "rsa"

        with open(filename, "w") as fp:
            json.dump({"nodename":nodename, 
                       "creator":"baltrad.exchange.crypto",                       
                       "key":self.PEM(),
                       "keyType":keyType,
                       "type":"public"}, fp)

    def verify(self, msg, signature):
        if isinstance(self._key, RSA.RsaKey):
            verifier = pkcs1_15.new(self._key)
        else:
            verifier = DSS.new(self._key, 'fips-186-3')
        hashed = SHA256.new(bytes(msg, "UTF-8"))
        uncodedsignature = base64.urlsafe_b64decode(bytes(signature, "UTF-8"))
        try:
            verifier.verify(hashed, uncodedsignature)
            return True
        except:
            pass
        return False

    
class private_key(object):
    def __init__(self, key):
        """Constructor
        :param key: The crypto key
        """
        super(private_key, self).__init__()
        self._key = key
    
    def publickey(self):
        """Returns the public key
        """
        return public_key(self._key.publickey())

    def PEM(self):
        """Returns the private key as PEM-encoded string
        """
        return self._key.export_key("PEM").decode()

    def sign(self, msg):
        hashed = SHA256.new(bytes(msg, "UTF-8"))
        if isinstance(self._key, RSA.RsaKey):
            signer = pkcs1_15.new(self._key)
        else:
            signer = DSS.new(self._key, 'fips-186-3')
        signature = signer.sign(hashed)
        result = base64.urlsafe_b64encode(signature).decode("ascii")
        return result
    
    def algorithm(self):
        if isinstance(self._key, RSA.RsaKey):
            return "rsa"
        elif isinstance(self._key, DSA.DsaKey):
            return "dsa"

        return "unknown"

    def exportPEM(self, filename):
        """Exports the private key to specified filename
        :param filename: The name of the file to be written
        """
        with open(filename, "w") as fp:
            fp.write(self.PEM())

    def exportJSON(self, filename, nodename):
        import json
        """Exports the public key to specified filename as a JSON entry
        :param filename: The name of the file to be written
        """
        keyType = "dsa"
        if isinstance(self._key, RSA.RsaKey):
            keyType = "rsa"

        with open(filename, "w") as fp:
            json.dump({"nodename":nodename,
                       "creator":"baltrad.exchange.crypto", 
                       "key":self.PEM(),
                       "keyType":keyType,        
                       "type":"private"}, fp)


def create_key(encryption="dsa"):
    """Creates a DSA/RSA 2048 byte private/public key pair
    :param encryption: The encryption to use, either dsa or rsa currently
    :return the private key from which the public key can be extracted
    """
    key = None
    if encryption == "dsa":
        key = DSA.generate(2048)
    elif encryption == "rsa":
        key = RSA.generate(2048)
    else:
        raise Exception("Unsupported encryption method")
    return private_key(key)

def import_key(data):
    """Imports raw keydata and creates a private/public key
    :param data: The raw keydata
    :return the public/private key
    """
    key = None
    try:
        key = DSA.importKey(data)
    except:
        pass

    if not key:
        try:
            key = RSA.importKey(data)
        except:
            pass

    if not key:
        raise Exception("Could not import key")

    if key.has_private():
        return private_key(key)

    return public_key(key)

def load_key(filename):
    """Loads a key from specified file. Either the file should be PEM-formatted or else the internally used json file
    :param filename: The file to load
    :return the public/private key on success
    """
    with open(filename) as fp:
        data = fp.read()
        try:
            import json
            jsond = json.loads(data)
            if "creator" in jsond and jsond["creator"] == "baltrad.exchange.crypto":
                return import_key(jsond["key"])
        except:
            pass
        return import_key(data)
