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
    from Crypto.PublicKey import DSA
    from Crypto.Math.Numbers import Integer
    
import base64, hashlib, binascii, struct
from pyasn1.codec.der import decoder
from pyasn1.codec.der import encoder
from pyasn1.type import univ


BIG_ENDIAN_INT_SPECIFIER = ">i"
BIG_ENDIAN_LONG_LONG_SPECIFIER = ">q"

ZERO_BYTE = b'\x00'
ZERO_BYTE_STR = "\x00"
ENCODING="utf-8"
ORDER_BYTE_LENGTH=20

def ASN1Sequence(*vals):
    seq = univ.Sequence()
    for i in range(len(vals)):
        seq.setComponentByPosition(i, vals[i])
    return seq
  
def MakeDsaSig(r, s):
    """
    Given the raw parameters of a DSA signature, return a Base64 signature.

    @param r: parameter r of DSA signature
    @type r: long int

    @param s: parameter s of DSA signature
    @type s: long int

    @return: raw byte string formatted as an ASN.1 sequence of r and s
    @rtype: string
    """
    seq = ASN1Sequence(univ.Integer(r), univ.Integer(s))
    return encoder.encode(seq)

def ParseDsaSig(sig):
    """
    Given a raw byte string, return tuple of DSA signature parameters.

    @param sig: byte string of ASN.1 representation
    @type sig: string

    @return: parameters r, s as a tuple
    @rtype: tuple

    @raise KeyczarErrror: if the DSA signature format is invalid
    """
    seq = decoder.decode(sig)[0]
    if len(seq) != 2:
        raise Exception("Illegal DSA signature.")
    r = int(seq.getComponentByPosition(0))
    s = int(seq.getComponentByPosition(1))
    return (r, s)

def RawString(b):
    if isinstance(b, bytes):
        return b.decode(ENCODING)
    return b

def RawBytes(s):
    if isinstance(s, str):
        return bytes(s, ENCODING)
    return s
  
def BytesToLong(byte_string):
    l = len(byte_string)
    byte_array = bytearray(byte_string)
    return int(sum([byte_array[i] * 256**(l - 1 - i) for i in range(l)]))

def TrimBytes(byte_string):
    """Trim leading zero bytes."""
    trimmed = byte_string.lstrip(b'\x00')
    if len(trimmed) == 0:  # was a string of all zero byte_string
        return b'\x00'
    else:
        return trimmed

def IntToBytes(n):
    return struct.pack(BIG_ENDIAN_INT_SPECIFIER, n)

def BigIntToBytes(n):
    """Return a big-endian byte string representation of an arbitrary length n."""
    array = []
    while (n > 0):
        array.append(n % 256)
        n = n >> 8
    array.reverse()
    barray = bytearray(array)
    if barray[0] & 0x80:
        return b'\x00' + bytes(barray)
    return bytes(barray)

def PrefixHash(*inputs):
    """Return a SHA-1 hash over a variable number of inputs."""
    md = hashlib.sha1()
    for i in inputs:
        #print("I=%s"%i)
        md.update(IntToBytes(len(i)))
        md.update(i)
    return md.digest() 

def Base64WSDecode(s):
    s = RawString(s) # Base64W decode can only work with strings
    s = ''.join(s.splitlines())
    s = str(s.replace(" ", ""))  # kill whitespace, make string (not unicode)
    d = len(s) % 4
    if d == 1:
        raise binascii.Error()
    elif d == 2:
        s += "=="
    elif d == 3:
        s += "="
  
    s = RawBytes(s)
    try:
        return base64.urlsafe_b64decode(s)
    except TypeError:
        # Decoding raises TypeError if s contains invalid characters.
        raise binascii.Error

def Base64WSEncode(b):
    return RawString(base64.urlsafe_b64encode(b)).replace("=", "")
