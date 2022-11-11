REST interface
==============

Authentication
--------------

Authentication is done through standard HTTP *Authorization* header containing
a provider name and provider-specific credentials.

Generic format of the exchange authorization header is::

  Authorization: exchange-PROVIDER CREDENTIALS

Provider *noauth* can be used to specify that no authentication is to be done
and is equivalent to omitting the *Authorization* header.

Crypto authentication provider
'''''''''''''''''''''''''''''''

**crypto** provider can be used to sign and verify HTTP messages using the stock/default
crypto library provided by for example Cryptodome or any other DSA/RSA-compatible API.

To sign a message using this method, first a signable string is created
from the HTTP request. This is the concatenation of the method,
and values of *Content-MD5*, *Content-Type* and *Date*, *Message-Id* headers, separated
by a newline (*\\n*). The headers are sorted alphabetically, so the value of
*Content-Type* appears before the value of *Date*. The Message-Id is mandatory and should
be unique.

Given a sample request::

  POST /file/ HTTP/1.1
  Host: example.com
  Content-Type: application/x-hdf5
  Content-MD5: f919609e57df334754cdb410c7847058
  Content-Length: nnn
  Date: Tue, 10 Jan 2012 19:03:34 GMT
  Message-Id: 9620924f-6198-470b-b3d1-6b26042fd7b9

  <h5-file>

The created signable string would be::

  POST
  f919609e57df334754cdb410c7847058
  application/x-hdf5
  Tue, 10 Jan 2012 19:03:34 GMT
  9620924f-6198-470b-b3d1-6b26042fd7b9

The format of of the authorization header is::

  Authorization: exchange-keyczar KEYNAME:SIGNATURE

where *KEYNAME* is the name of the key the server will use to look up a key
for verifying the signature and *SIGNATURE* is the base64-encoded signature
that was created.

On unsuccesful authentication, a *401 Unauthorized* response will be sent,
with available authentication providers in *WWW-Authenticate* header, one
provider per header::

  WWW-Authenticate: exchange-crypto

Creating signatures
-------------------

If you are using a different language than python and want to create messages then you will have to implement your own signature handling.
The implementation in baltrad-exchange are using PyCryptodome and is straight forward without any extra meta-information in the data to be signed
and should be quite easy to implement in a different language.

.. code:: python

   from Cryptodome.PublicKey import DSA, RSA
   from Cryptodome.Signature import DSS, pkcs1_15
   from Cryptodome.Hash import SHA256  
   import base64
   
   key = DSA.importKey(open("mydsakey.private").read())
   msg = "This is a message to sign"
   
   hashed = SHA256.new(bytes(msg, "UTF-8"))
   signer = DSS.new(key, 'fips-186-3')
   signature = signer.sign(hashed)
   result = base64.urlsafe_b64encode(signature).decode("ascii")

   print("Signature: %s"%result)
   

When running the above code the signature will be printed and can look something like

.. code:: none

   Signature: CKQHaXw1FuLPjjNt8Y2zX3qCdxaTNfCEya1nQ6UhvrFewvYfmWEpc1NEms8FbhvdK4W0YH50S8k= 
   

Keyczar authentication provider (*Legacy*)
'''''''''''''''''''''''''''''''
**keyczar** provider can be used to sign and verify HTTP messages using
`Keyczar <https://github.com/google/keyczar/>`_. Keyczar has been deprecated and is
no longer supported. Since baltrad-dex and baltrad-db is still using it
we have provided a simple implementation providing the necessary parts to continue
communicating with these systems. 

The behaviour when signing messages using Keyczar is similar to **Crypto**. 
First a signable string is created from the HTTP request. This is the concatenation of the 
method, query path and values of *Content-MD5*, *Content-Type* and *Date* headers, separated
by a newline (*\\n*). The headers are sorted alphabetically, so the value of
*Content-Type* appears before the value of *Date*.

Given a sample request::

  POST /source/ HTTP/1.1
  Host: example.com
  Content-Type: application/json
  Content-MD5: f919609e57df334754cdb410c7847058
  Content-Length: nnn
  Date: Tue, 10 Jan 2012 19:03:34 GMT

  {
    "source": {
      "name": "source_name",
      "values": {
          "key1": "value1",
          "key2": "value2",
      }
    }
  }

The created signable string would be::

  POST
  /source/
  f919609e57df334754cdb410c7847058
  application/json
  Tue, 10 Jan 2012 19:03:34 GMT

The format of of the authorization header is::

  Authorization: exchange-crypto KEYNAME:SIGNATURE

where *KEYNAME* is the name of the key the server will use to look up a key
for verifying the signature and *SIGNATURE* is the base64-encoded signature
from :meth:`keyczar.keyczar.Signer.Sign`.

On unsuccesful authentication, a *401 Unauthorized* response will be sent,
with available authentication providers in *WWW-Authenticate* header, one
provider per header::

  WWW-Authenticate: exchange-keyczar


Operations
----------

.. _doc-rest-post-file

Post file
''''''''''
**Request**
  :Synopsis: POST /file/
  :Headers: Content-Length, Content-Type, Date, Message-Id
  :Body: file content

  ::

    POST /file/ HTTP/1.1
    Host: example.com
    Content-Length: nnn
    Content-Type: application/x-hdf5
    Date: 2022-11-11 10:00:00 UTC
    Message-Id: 9620924f-6198-470b-b3d1-6b26042fd7b9

    [nnn bytes of file data]

**Response**
  :Headers: Content-Length, Content-Type, Location
  :Status:
    * **200 OK** - file has been handled
  ::

    HTTP/1.1 200 OK

    