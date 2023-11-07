# Copyright (C) 2023- Swedish Meteorological and Hydrological Institute (SMHI)
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

## Functionality for publishing files using the zmq api

## @file
## @author Anders Henja, SMHI
## @date 2023-10-26
import zmq, hmac, hashlib
import logging
from tempfile import NamedTemporaryFile
from threading import Thread, Event
from bexchange.net import connections, publishers
from bexchange.naming.namer import metadata_namer

logger = logging.getLogger("bexchange.net.zmq.publisher")

class publisher(publishers.standard_publisher):
    """The zmq publisher is used to publish messages to remote parties. It is run in a separate thread
    """
    def __init__(self, backend, name, active, origin, ifilter, connections, decorators, extra_arguments):
        """Constructor
        :param backend: The backend
        :param active: If this runner is active or not. NOT USED
        :param origin: Can be used to identify allowed originators
        :param ifilter: Filter of what files that should be passed on
        :param connections: NOT USED
        :param decorators: If any decorator should be applied
        :param extra_arguments: The arguments allowed for this publisher
        """
        super(publisher, self).__init__(backend, name, active, origin, ifilter, [], decorators, extra_arguments)
        self._name = "zmqpublisher"
        self._address = extra_arguments["publisher_address"]
        self._hmackey = extra_arguments["hmac"].encode('ascii')
        self._namers={}

        if "name" in extra_arguments:
            self._name = extra_arguments["name"]
        
        if "namers" in extra_arguments:
            for item in extra_arguments["namers"]:
                objectName = "default"
                if "object" in item:
                    objectName = item["object"]
                self._namers[objectName]=metadata_namer(item["pattern"])
        else:
            self._namers["SCAN"] = metadata_namer("${_baltrad/source_name}_scan_${/dataset1/where/elangle}_${/what/date}T${/what/time}.h5")

        if "default" not in self._namers:
            self._namers["default"] = metadata_namer("${_baltrad/source_name}_${/what/object}.tolower()_${/what/date}T${/what/time}.h5")

        self._context = None
        self._socket = None

    def address(self):
        """Return the address
        :return: the address
        """
        return self._address

    def name(self):
        """Return the name
        :return: the name
        """
        return self._name

    def hmackey(self):
        """Return the hmackey
        :return: the hmac key
        """
        return self._hmackey

    def setup_connection(self):
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.PUB)
        self._socket.bind(self._address)

    def initialize(self):
        """Initializes the publisher before it is started.
        """
        super(publisher, self).initialize()
        self.setup_connection()

    def get_attribute_value(self, name, meta):
        """
        :param name: Name of attribute
        :param meta: Metadata from where value for name should be taken
        :return: the value for the name or None if not found
        """
        try:
            return meta.node(name).value
        except LookupError:
            return None

    def read_bytearray(self, tmpfile):
        """Reads a file and returns the content as a bytearray.
        :param tmpfile: The NamedTemporaryFile
        :return: a byte array
        """
        b_content = bytearray()
        with open(tmpfile.name, "rb") as fp:
            b_content = bytearray(fp.read())
        return b_content

    def create_hmac(self, b_payload):
        """Creates a hmac from the payload using the hmackey
        :param b_payload: The bytearray payload to generate a hmac from
        :return: the hmac
        """
        return hmac.new(self._hmackey, b_payload, hashlib.sha1).digest()

    def do_publish(self, tmpfile, meta):
        """Publishes files over the data transporter zero mq layer.
        :param tmpfile: The temporary file containing the data to be sent
        :param meta: The metadata describing the file content
        """
        b_content = self.read_bytearray(tmpfile)

        objectName = self.get_attribute_value("/what/object", meta)
        if objectName in self._namers:
            filename = self._namers[objectName].name(meta).ljust(256, '\0')
        else:
            filename = self._namers["default"].name(meta).ljust(256, '\0')

        b_payload = bytearray(filename.encode('latin1')) + b_content

        payload_hmac = self.create_hmac(b_payload)
        
        buffer_to_publish = bytearray(payload_hmac + b_payload)

        logger.info("Publishing file '%s' over zmq" % filename.strip())

        self._socket.send(buffer_to_publish)

        tmpfile.close()

class dmzpublisher(publisher):
    """The zmqdmz publisher is used to publish messages to a dmz proxy. It is run in a separate thread
    """
    def __init__(self, backend, name, active, origin, ifilter, connections, decorators, extra_arguments):
        """Constructor
        :param backend: The backend
        :param active: If this runner is active or not. NOT USED
        :param **args: A number of arguments can be provided
        """
        super(dmzpublisher, self).__init__(backend, name, active, origin, ifilter, [], decorators, extra_arguments)

    def setup_connection(self):
        """Connects to the remote publisher proxy
        """
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.PUB)
        self._socket.connect(self.address())