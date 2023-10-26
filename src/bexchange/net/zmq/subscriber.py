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
import logging, time
from tempfile import NamedTemporaryFile
from threading import Thread, Event
from bexchange.runner import runners

logger = logging.getLogger("bexchange.runner.zmq.subscriber")

class subscriber(runners.runner):
    """The zmq subscriber is used to receive messages from remote parties. It is run in a separate thread
    """
    
    def __init__(self, backend, active, **args):
        """Constructor
        :param backend: The backend
        :param active: If this runner is active or not. NOT USED
        :param **args: A number of arguments can be provided
        """
        super(subscriber, self).__init__(backend, active)
        self._name = "zmqsubscriber"
        self._address = args["address"]
        self._hmackey = args["hmac"].encode('ascii')
        if "name" in args:
            self._name = args["name"]

    def handle_file(self, filename):
        """Handles the file (by sending it to the backend using the name given to this runner
        :param filename: The filename to handle
        """
        self._backend.store_file(filename, self._name)

    def calculate_hmac(self, message):
        """Calculates the hmac for the message with the hmackey
        :param message: The message to generate hmac for
        """
        return hmac.new(self._hmackey, message, hashlib.sha1)

    def create_named_temporary_file(self):
        """Creates a named temporary file. This method only exists for unittest purpose
        :return: A NamedTemporaryFile
        """
        return NamedTemporaryFile()

    def process(self, message):
        """Processes a received message. The format is according to the data transporter
        :param message: The incomming data message
        """
        if len(message) < 276:
            logger.info("Dropping message since it's to short")
            return
        
        try:
            senderHmac = message[:20]
            fname = message[20:(20+256)].decode()
            calculatedHmac = self.calculate_hmac(message[20:])
            if senderHmac.hex() == calculatedHmac.digest().hex():
                with self.create_named_temporary_file() as tmp:
                    tmp.write(message[20+256:])
                    tmp.flush()
                    try:
                        self.handle_file(tmp.name)                
                    except:
                        logger.exception("Failed to process file %s"%fname)
            else:
                logger.debug("Dropping message from %s"%self._address)
        except:
            logger.exception("Could not process message")

    def run(self):
        """The runner for the thread. Ensures that the ZMQ socket is listening on the address and passes
        on the message to process.
        """
        while True:
            try:
                logger.info("Atempting to setup zmq listener on %s"%self._address)
                context = zmq.Context()
                socket = context.socket(zmq.SUB)        
                socket.connect(self._address)
                socket.setsockopt_string(zmq.SUBSCRIBE, "")
                while True:
                    b_message = socket.recv()
                    self.process(b_message)
            except:
                logger.exception("Failure during zmq processing. Waiting for 1 second before restart")
                time.sleep(1.0)
            

    def start(self):
        """Starts this runner by starting a daemonized thread.
        """
        self._thread = Thread(target=self.run)
        self._thread.daemon = True
        self._thread.start()