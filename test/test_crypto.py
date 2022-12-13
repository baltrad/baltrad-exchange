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

## Tests baltrad.exchange.naming.namer

## @file
## @author Anders Henja, SMHI
## @date 2022-10-18
from __future__ import absolute_import

import unittest
import os

from bexchange import crypto

FIXTURE_DIR="%s/fixtures"%os.path.dirname(os.path.abspath(__file__))

class test_internal_crypto(unittest.TestCase):
    PRIVATE_KEY = "%s/anders-silent/anders-silent.private"%FIXTURE_DIR
    PUBLIC_KEY = "%s/anders-silent/anders-silent.public"%FIXTURE_DIR
    PUBLIC_JSON_KEY = "%s/anders-silent/anders-silent_public.json"%FIXTURE_DIR

    PRIVATE_RSA_KEY = "%s/anders-silent-rsa/anders-silent.private"%FIXTURE_DIR
    PUBLIC_RSA_KEY = "%s/anders-silent-rsa/anders-silent.public"%FIXTURE_DIR
    PUBLIC_RSA_JSON_KEY = "%s/anders-silent-rsa/anders-silent_public.json"%FIXTURE_DIR
    
    def test_create_and_sign(self):
        privatekey = crypto.create_key()
        publickey = privatekey.publickey()
        msg = "This is the message to sign"
        signature = privatekey.sign(msg)
        othermsg = "This is another message that isnt signed"
        self.assertTrue(publickey.verify(msg, signature))
        self.assertFalse(publickey.verify(othermsg, signature))

    def test_load_sign_and_verify(self):
        publickey = crypto.load_key(self.PUBLIC_KEY)
        privatekey = crypto.load_key(self.PRIVATE_KEY)
        
        msg = "This is the message to sign"
        signature = privatekey.sign(msg)
        othermsg = "This is another message that isnt signed"
        self.assertTrue(publickey.verify(msg, signature))
        self.assertFalse(publickey.verify(othermsg, signature))

    def test_load_sign_and_verify_rsa(self):
        publickey = crypto.load_key(self.PUBLIC_RSA_KEY)
        privatekey = crypto.load_key(self.PRIVATE_RSA_KEY)
        
        msg = "This is the message to sign"
        signature = privatekey.sign(msg)
        othermsg = "This is another message that isnt signed"
        self.assertTrue(publickey.verify(msg, signature))
        self.assertFalse(publickey.verify(othermsg, signature))

    def test_load_public_key(self):
        publickey = crypto.load_key(self.PUBLIC_KEY)
        self.assertEqual("""-----BEGIN PUBLIC KEY-----
MIIDQjCCAjUGByqGSM44BAEwggIoAoIBAQC+VKVtGX0U6G6HPsbc6aPcdCObfSYt
820/CeO4jady1Y+m0WtLwXOelOXe1iT/VjnNQke7PvGQj6VDW4qOXY0puVs2XlAZ
q+fldJKwvyRqo1y9evvXy5l/Cue0aiEzPqF7hmiG3WtmqUR4+aQfBQcvgCdZ8gta
k5vcY0hudIdI8xLq5kvkzy3GnW7diHUWBp5XEBmDPsfgnAyhUKEOmoIyj/1vZZYJ
ryY+V9pRUUxC6DTFt1N7ze+CNPbIIE0+SwkyrK6TljieL2LJ3shpVbZAPwntTNPC
x+rGpQbq2oOkv/c0e3ial7Yc2ur3BWfDTdWdpuj3lboMVB3aaVhS7yxjAh0A74eq
sgXMYYD+MmCGNrfUY1osj4PSX+Cq7aoybQKCAQBaaNWplIlekAFvQZYX38ZYO6Z1
12qAH/N5fTOVfTaL+3XuEksa/aZ0Rx89Go0+rFFzIl7CaOE7Bzumns1PTcpYuZ46
vofoeVSOyfcz/K5fZxXRcSVSxsPfUw+7aS85RV8D7XZI3ToezIaCGaYqCLZt2D/Z
18VxvXrdcLL/q0wAkHlE+FgN3BdCfcFNHqMfaOMBWTWSg0tXeF+LD+Id4yHwI98e
oZ2+ijZ3OUWvrge5sD/42CjZFKo3xR6l+YP+5S3iSIxiGYPY9sSWZRautZVFbzPB
SYS7l+HAN8QlKgKns1115HhX97/V6S9qXINxJdd8Yg7o/0njpJij/7bIc+fjA4IB
BQACggEANr7HNasvzsr2e412a7R8MnftuOGBVtPDGTvpVZr02sd80mkNjIDvz3rI
ATevvT6gl/q5H/KAbcx/G5kcqGMa3cXib48Gxj3l4M8hshvK+r2qqVxVlJeU6bJH
jI5gVMIN4KcNA17nEzCzXUkBVgrixgK6FGFdUtc5C6zYe2/TE4xQ5Wb9yCmN0XEV
r+26CKMEGjKzJD88q7TbhZUrCJTh/q/UG0ESIaQ4DAZzP764LkLW4KKv6f156YrO
tKQuwBLu9o2jSKOuPOxczOQrQ676Zam68xwT0gHWXEpUcEYStoJ0v1blNg+Yk38L
wFuHVQu+aMlDOlOWLf4wuipGpj05JA==
-----END PUBLIC KEY-----""", publickey.PEM())
        self.assertTrue(isinstance(publickey, crypto.public_key))
        
    def test_load_json_public_key(self):
        publickey = crypto.load_key(self.PUBLIC_JSON_KEY)
        self.assertEqual("""-----BEGIN PUBLIC KEY-----
MIIDQjCCAjUGByqGSM44BAEwggIoAoIBAQC+VKVtGX0U6G6HPsbc6aPcdCObfSYt
820/CeO4jady1Y+m0WtLwXOelOXe1iT/VjnNQke7PvGQj6VDW4qOXY0puVs2XlAZ
q+fldJKwvyRqo1y9evvXy5l/Cue0aiEzPqF7hmiG3WtmqUR4+aQfBQcvgCdZ8gta
k5vcY0hudIdI8xLq5kvkzy3GnW7diHUWBp5XEBmDPsfgnAyhUKEOmoIyj/1vZZYJ
ryY+V9pRUUxC6DTFt1N7ze+CNPbIIE0+SwkyrK6TljieL2LJ3shpVbZAPwntTNPC
x+rGpQbq2oOkv/c0e3ial7Yc2ur3BWfDTdWdpuj3lboMVB3aaVhS7yxjAh0A74eq
sgXMYYD+MmCGNrfUY1osj4PSX+Cq7aoybQKCAQBaaNWplIlekAFvQZYX38ZYO6Z1
12qAH/N5fTOVfTaL+3XuEksa/aZ0Rx89Go0+rFFzIl7CaOE7Bzumns1PTcpYuZ46
vofoeVSOyfcz/K5fZxXRcSVSxsPfUw+7aS85RV8D7XZI3ToezIaCGaYqCLZt2D/Z
18VxvXrdcLL/q0wAkHlE+FgN3BdCfcFNHqMfaOMBWTWSg0tXeF+LD+Id4yHwI98e
oZ2+ijZ3OUWvrge5sD/42CjZFKo3xR6l+YP+5S3iSIxiGYPY9sSWZRautZVFbzPB
SYS7l+HAN8QlKgKns1115HhX97/V6S9qXINxJdd8Yg7o/0njpJij/7bIc+fjA4IB
BQACggEANr7HNasvzsr2e412a7R8MnftuOGBVtPDGTvpVZr02sd80mkNjIDvz3rI
ATevvT6gl/q5H/KAbcx/G5kcqGMa3cXib48Gxj3l4M8hshvK+r2qqVxVlJeU6bJH
jI5gVMIN4KcNA17nEzCzXUkBVgrixgK6FGFdUtc5C6zYe2/TE4xQ5Wb9yCmN0XEV
r+26CKMEGjKzJD88q7TbhZUrCJTh/q/UG0ESIaQ4DAZzP764LkLW4KKv6f156YrO
tKQuwBLu9o2jSKOuPOxczOQrQ676Zam68xwT0gHWXEpUcEYStoJ0v1blNg+Yk38L
wFuHVQu+aMlDOlOWLf4wuipGpj05JA==
-----END PUBLIC KEY-----""", publickey.PEM())
        self.assertTrue(isinstance(publickey, crypto.public_key))
        
    def test_load_private_key(self):
        privatekey = crypto.load_key(self.PRIVATE_KEY)
        self.assertEqual("""-----BEGIN PRIVATE KEY-----
MIICXAIBADCCAjUGByqGSM44BAEwggIoAoIBAQC+VKVtGX0U6G6HPsbc6aPcdCOb
fSYt820/CeO4jady1Y+m0WtLwXOelOXe1iT/VjnNQke7PvGQj6VDW4qOXY0puVs2
XlAZq+fldJKwvyRqo1y9evvXy5l/Cue0aiEzPqF7hmiG3WtmqUR4+aQfBQcvgCdZ
8gtak5vcY0hudIdI8xLq5kvkzy3GnW7diHUWBp5XEBmDPsfgnAyhUKEOmoIyj/1v
ZZYJryY+V9pRUUxC6DTFt1N7ze+CNPbIIE0+SwkyrK6TljieL2LJ3shpVbZAPwnt
TNPCx+rGpQbq2oOkv/c0e3ial7Yc2ur3BWfDTdWdpuj3lboMVB3aaVhS7yxjAh0A
74eqsgXMYYD+MmCGNrfUY1osj4PSX+Cq7aoybQKCAQBaaNWplIlekAFvQZYX38ZY
O6Z112qAH/N5fTOVfTaL+3XuEksa/aZ0Rx89Go0+rFFzIl7CaOE7Bzumns1PTcpY
uZ46vofoeVSOyfcz/K5fZxXRcSVSxsPfUw+7aS85RV8D7XZI3ToezIaCGaYqCLZt
2D/Z18VxvXrdcLL/q0wAkHlE+FgN3BdCfcFNHqMfaOMBWTWSg0tXeF+LD+Id4yHw
I98eoZ2+ijZ3OUWvrge5sD/42CjZFKo3xR6l+YP+5S3iSIxiGYPY9sSWZRautZVF
bzPBSYS7l+HAN8QlKgKns1115HhX97/V6S9qXINxJdd8Yg7o/0njpJij/7bIc+fj
BB4CHFutCAXuD0/htXEaCMB4ukVWqdxwxEjoboRPHBs=
-----END PRIVATE KEY-----""", privatekey.PEM())        
        self.assertTrue(isinstance(privatekey, crypto.private_key))
