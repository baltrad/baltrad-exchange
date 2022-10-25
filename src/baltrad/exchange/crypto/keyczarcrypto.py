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

## This code has been reversed engineered from keyczar (deprecated) so that it is possible to
# keep backward compatibility in the protocol. Some functions has been taken directly from
# keyczar and others has been implemented to get same behaviour. It is only the DSA-keys that
# are supported.
#
# The compatibiltiy is achieved by using Cryptodome and some internal functions that we hope will be
# available for some time until it is possible to phase out the legacy keyczar signature handling used
# within BALTRAD.
#

# All credits to the original implementors of Keyczar. See https://github.com/google/keyczar and https://github.com/google/keyczar/blob/master/LICENSE
# for original license.

## @file
## @author Anders Henja, SMHI
## @date 2022-10-24
try:
    from Cryptodome.Signature import DSS
    from Cryptodome.PublicKey import DSA
    from Cryptodome.Math.Numbers import Integer
except:
    from Crypto.Signature import DSS
    from Crypto.Math.Numbers import Integer
    from Crypto.PublicKey import DSA
    
import hashlib, base64, json, os

from baltrad.exchange.crypto import keyczarutil
from baltrad.exchange.crypto.keyczarutil import TrimBytes, BigIntToBytes, PrefixHash, RawString, Base64WSDecode, Base64WSEncode, BytesToLong

def CreateKeyczarHash(key):
    fullhash = PrefixHash(TrimBytes(BigIntToBytes(key.p)),
                          TrimBytes(BigIntToBytes(key.q)),
                          TrimBytes(BigIntToBytes(key.g)),
                          TrimBytes(BigIntToBytes(key.y)))
    return RawString(base64.urlsafe_b64encode(fullhash[:4])).replace("=", "")

def CreateKeyczarSignHeader(k):
    return (bytes(bytearray([0]))
                      + Base64WSDecode(CreateKeyczarHash(k)))


class keyczar_signer(object):
    """Wrapper around Cryptodome that implements support for signing according to Keyczar implementation
    """
    def __init__(self, key):
        self._key = key

    def sign(self, message):
        """ Creates a signature from the provided message according to Keyczar algorithm.
        :param message: The message from which a signature should be created
        :return the signature according to keyczar algorithm
        """
        signer = DSS.new(self._key, 'fips-186-3')
        
        msgtohash = bytes(message + keyczarutil.ZERO_BYTE_STR, keyczarutil.ENCODING)
        hash_md = hashlib.sha1(msgtohash)
        nonce = signer._compute_nonce(hash_md)
        z = Integer.from_bytes(hash_md.digest()[:keyczarutil.ORDER_BYTE_LENGTH])
        r, s = signer._key._sign(z, nonce)
        dsasig = keyczarutil.MakeDsaSig(r, s)
        keyczarsig = CreateKeyczarSignHeader(self._key) + dsasig
        return Base64WSEncode(keyczarsig)

    @staticmethod
    def read(keypath):
        """Loads a keyczar signer key Note. This function only supports version 1, meaning the meta is in "meta" and keydata in "1".
        :param keypath: the folder where the meta and data can be found.
        :return the read key
        :throws Exception if key not could be loaded
        """
        readkey = load_key(keypath)
        if isinstance(readkey, keyczar_signer):
            return readkey
        raise Exception("Read key is not capable of signing")

    def export(self, foldername, nodename="unknown"):
        """Exports the keyczar signer key.  This function only supports version 1, meaning the meta is in "meta" and keydata in "1".
        :param foldername: where the key folder should be created
        :param nodename: the name that should be added inside the meta at "name" position
        """
        data = json.dumps({"publicKey": {"p": Base64WSEncode(BigIntToBytes(self._key.p)),
                                         "q": Base64WSEncode(BigIntToBytes(self._key.q)),
                                         "g": Base64WSEncode(BigIntToBytes(self._key.g)),
                                         "y": Base64WSEncode(BigIntToBytes(self._key.y)),
                                         "size": 1024},
                            "size":1024,
                            "x":Base64WSEncode(BigIntToBytes(self._key.x))})

        meta = json.dumps({"name":nodename,
                "purpose":"SIGN_AND_VERIFY",
                "type":"DSA_PRIV",
                "encrypted":"false",
                "versions":[{"versionNumber":1,"status":"PRIMARY","exportable":False}]})
        
        os.makedirs(foldername, exist_ok=True)
        
        with open("%s/1"%(foldername), "w") as fp:
            fp.write(data)
        with open("%s/meta"%(foldername), "w") as fp:
            fp.write(meta)


class keyczar_verifier(object):
    """Wrapper around Cryptodome that implements support for verifying according to Keyczar implementation
    """
    def __init__(self, key):
        """Constructor. Takes a DsaKey from Cryptodome
        """
        self._key = key

    def verify(self, message, signature):
        """Verify a message according to how Keyczar creates it's signature.
        :param message: The message to be verified
        :param signature: The signature generated according to keyczar algorithm
        :return True if verification successful, otherwise False
        """
        verifier = DSS.new(self._key, 'fips-186-3')
        decodedsig = Base64WSDecode(signature)
        keyczarsignheader = CreateKeyczarSignHeader(self._key)
        if decodedsig.startswith(keyczarsignheader): # First we validate header part
            msgtohash = bytes(message + keyczarutil.ZERO_BYTE_STR, keyczarutil.ENCODING)
            hash_md = hashlib.sha1(msgtohash)
            rawsignature = decodedsig[len(keyczarsignheader):]
            r, s = keyczarutil.ParseDsaSig(rawsignature)
            z = Integer.from_bytes(hash_md.digest()[:keyczarutil.ORDER_BYTE_LENGTH])
            return verifier._key._verify(z, (r, s))
        return False

    @staticmethod
    def read(keypath):
        """Loads a keyczar verifier key Note. This function only supports version 1, meaning the meta is in "meta" and keydata in "1".
        :param keypath: the folder where the meta and data can be found.
        :return the read key
        :throws Exception if key not could be loaded
        """
        readkey = load_key(keypath)
        if isinstance(readkey, keyczar_verifier):
            return readkey
        else:
            return keyczar_verifier(readkey._key)

    def export(self, foldername, nodename="unknown"):
        """Exports the keyczar verifier key.  This function only supports version 1, meaning the meta is in "meta" and keydata in "1".
        :param foldername: where the key folder should be created
        :param nodename: the name that should be added inside the meta at "name" position
        """
        data = json.dumps({"p": Base64WSEncode(BigIntToBytes(self._key.p)),
                           "q": Base64WSEncode(BigIntToBytes(self._key.q)),
                           "g": Base64WSEncode(BigIntToBytes(self._key.g)),
                           "y": Base64WSEncode(BigIntToBytes(self._key.y)),
                           "size": 1024})

        meta = json.dumps({"name":nodename,
                "purpose":"VERIFY",
                "type":"DSA_PUB",
                "encrypted":"false",
                "versions":[{"versionNumber":1,"status":"PRIMARY","exportable":False}]})
        
        os.makedirs(foldername, exist_ok=True)
        
        with open("%s/1"%(foldername), "w") as fp:
            fp.write(data)
        with open("%s/meta"%(foldername), "w") as fp:
            fp.write(meta)
            
def import_keyczar_key(keytype, keydata):
    """Create a DSA - key from keytype and keydata
    :param keytype: A keytype, can be either DSA_PUB or DSA_PRIV
    :param keydata: JSON-structure according to Keyczar '1' data
    :return a keyczar_signer or keyczar_verifier instance depending on key info
    """
    if keytype == "DSA_PUB":
        readkey = DSA.construct((BytesToLong(Base64WSDecode(keydata['y'])),
                                 BytesToLong(Base64WSDecode(keydata['g'])),
                                 BytesToLong(Base64WSDecode(keydata['p'])),
                                 BytesToLong(Base64WSDecode(keydata['q']))))
    elif keytype == "DSA_PRIV":
        publickey = keydata["publicKey"]
        readkey = DSA.construct((BytesToLong(Base64WSDecode(publickey['y'])),
                                 BytesToLong(Base64WSDecode(publickey['g'])),
                                 BytesToLong(Base64WSDecode(publickey['p'])),
                                 BytesToLong(Base64WSDecode(publickey['q'])),
                                 BytesToLong(Base64WSDecode(keydata['x']))))
    else:
        raise Exception("Unsupported keytype: %s"%keytype)

    if readkey.has_private():
        return keyczar_signer(readkey)

    return keyczar_verifier(readkey)

def load_key(keypath):
    """Loads a keyczar key according. It will load meta, extract type from meta and then pass content from <key>/1
    to import_keyczar_key.
    :param keypath: The path to where the keyczar key is located
    :return keyczar_signer or keyczar_verifier depending on key content
    """
    import json
    with open("%s/meta"%keypath) as fp:
        meta = json.load(fp)
    with open("%s/1"%keypath) as fp:
        keydata = json.load(fp)
    return import_keyczar_key(meta["type"], keydata)
    