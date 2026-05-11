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

## Different type of connections

## @file
## @author Anders Henja, SMHI
## @date 2021-12-01
from bexchange.net.senders import sender_manager
from bexchange import util
from queue import Full, Empty
from threading import Thread

import logging
import importlib
from tempfile import NamedTemporaryFile
import shutil

logger = logging.getLogger("bexchange.net.connections")

class publisher_connection(object):
    """publisher connections are used for publishing files in various ways without taking the protocol / sender into account.
    Each (or most) publisher_connection is associated with one or more senders.
    """
    def __init__(self, backend):
        """Constructor
        :param backend: The backend
        """
        self._backend = backend
    
    def publish(self, path, meta):
        """Publishes a file in some way using the underlying implementation
        :param path: The path to the file
        :param meta: The metadata of the file
        """
        raise Exception("Not implemented")
    
    def backend(self):
        """Returns the backend
        """
        return self._backend

    def stop(self):
        """Stops the connection
        """
        pass

class simple_connection(publisher_connection):
    """Simple connection, only parsing arguments according to. sender class + arguments. 
    """
    def __init__(self, backend, arguments):
        """Constructor
        :param backend: The backend
        :param arguments: A dictionary with relevant arguments. At least
        {"sender":...}
        """
        super(simple_connection, self).__init__(backend)
        if "sender" in arguments:
            self._sender = sender_manager.from_conf(backend, arguments["sender"])
        else:
            raise Exception("Requires 'sender' in arguments")
    
    def publish(self, path, meta):
        """Publishes the file using the sender
        :param path: The path to the file
        :param meta: The metadata of the file
        """
        self._sender.send(path, meta)

class failover_connection(publisher_connection):
    """Failover connection, expects a list of senders in arguments. Where they are tried in 
    order until one works. 
    """
    def __init__(self, backend, arguments):
        """Constructor
        :param backend: The backend
        :param arguments: A dictionary with relevant arguments. At least
        {"senders":[...]}
        """
        super(failover_connection, self).__init__(backend)
        self._senders = []
        if "senders" in arguments:
            for sender_conf in arguments["senders"]:
                self._senders.append(sender_manager.from_conf(backend, sender_conf))
        else:
            raise Exception("Requires 'senders' in arguments")
        
    def publish(self, path, meta):
        """Publishes the file using the senders. When first successful publishing has successfully
        been transmitted, the method returns. If on the other hand no senders are successfully used
        an exception will be thrown.
        :param path: The path to the file
        :param meta: The metadata of the file
        """
        successful = False
        for sender in self._senders:
            try:
                sender.send(path, meta)
                logger.info("failover_connection: Successfully sent file to %s, ID:'%s'"%(sender.id(), util.create_fileid_from_meta(meta)))
                successful = True
                break
            except:
                logger.exception("failover_connection: Failed to send file to %s, ID:'%s', trying next in list"%(sender.id(), util.create_fileid_from_meta(meta)))
        if not successful:
            raise Exception("Failed to publish using the failover connection")

class backup_connection(publisher_connection):
    """Backup connection, expects a list of senders in arguments. Where all senders are run. 
    """
    def __init__(self, backend, arguments):
        super(backup_connection, self).__init__(backend)
        self._senders = []
        if "senders" in arguments:
            for sender_conf in arguments["senders"]:
                self._senders.append(sender_manager.from_conf(backend, sender_conf))
        else:
            raise Exception("Requires 'senders' in arguments")
        
    def publish(self, path, meta):
        for sender in self._senders:
            try:
                sender.send(path, meta)
                logger.info("Successfully sent file to %s, ID:'%s'"%(sender.id(), util.create_fileid_from_meta(meta)))
            except Exception as e:
                logger.exception("Failed to send file to %s, ID:'%s'"%(sender.id(), util.create_fileid_from_meta(meta)))


class distributed_connection(publisher_connection):
    """Distributed connection, expects a list of senders in arguments. Where all senders are run. This is the same
    behavior as the backup connection but it's here for readability.
    """
    def __init__(self, backend, arguments):
        super(distributed_connection, self).__init__(backend)
        self._senders = []
        if "senders" in arguments:
            for sender_conf in arguments["senders"]:
                self._senders.append(sender_manager.from_conf(backend, sender_conf))
        else:
            raise Exception("Requires 'senders' in arguments")
        
    def publish(self, path, meta):
        for sender in self._senders:
            try:
                sender.send(path, meta)
                logger.info("Successfully sent file to %s, ID:'%s'"%(sender.id(), util.create_fileid_from_meta(meta)))
            except Exception as e:
                logger.exception("Failed to send file to %s, ID:'%s'"%(sender.id(), util.create_fileid_from_meta(meta)))


class parallel_connection_sender(object):
    """ Wraps a sender into an object that is handled by the parallel connection
    """
    def __init__(self, sender, queue_size):
        """ Constructor
        :param sender: the sender
        :param queue_size: the queue size this instance should allow before throwing new items
        """
        self._sender = sender
        self._queue = util.jobQueue(queue_size)
        self._thread = None
        self._running = False

    def send(self, path, meta):
        """ Puts a message into the message queue
        :param path: the path to the physical file
        :param meta: the meta information
        """
        tmpfile = NamedTemporaryFile(dir=self._sender.backend().get_tmp_folder())
        with open(path, "rb") as fp:
            shutil.copyfileobj(fp, tmpfile)
        tmpfile.flush()        

        try:
            self._queue.put((tmpfile, meta))
        except Full as e:
            logger.exception("Queue for sender '%s' is full, dropping message with ID:'%s'"%(self.id(), util.create_fileid_from_meta(meta)))
            try:
                tmpfile.close()
            except:
                pass

    def consumer(self):
        """ The consumer called by the thread. Will grab one entry from the queue and pass it on to the connections.
        """
        tmpfile = None
        logger.info("Entered consumer")
        while self._running:
            meta = None
            try:
                 # In 3.13 there will be support for shutdown. So we need to use nowait and instead use _event.wait for notification purposes
                tmpfile, meta = self._queue.get()
                self._sender.send(tmpfile, meta)

                self._queue.task_done()

                logger.info("Successfully sent file to %s using threaded sender, ID:'%s'"%(self._sender.id(), util.create_fileid_from_meta(meta)))
            except Exception:
                if meta:
                    logger.exception("Failed to send file to %s, ID:'%s'"%(self._sender.id(), util.create_fileid_from_meta(meta)))
                else:
                    logger.exception("Failed to send unknown item to %s" % self._sender.id())

                if not self._running:
                    break
            finally:
                if tmpfile:
                    try:
                        tmpfile.close()
                    except:
                        pass
        logger.info("Left consumer")

    def start(self):
        """ Starts all consumer threads as daemon threads
        """
        self._running = True        
        self._thread = Thread(target=self.consumer)
        self._thread.daemon = True
        self._thread.start() 

    def stop(self):
        """Joins the threads
        """
        logger.info("Stopping publisher")
        self._running = False
        self._queue.shutdown()
        self._thread.join()
        logger.info("Publisher stopped")

    def id(self):
        """Returns the senders id
        """
        return self._sender.id()

class parallel_connection(publisher_connection):
    """ This is similar to the distributed connection but it will create a thread for each added sender so that
    the messages are sent without affecting each other. If for example the first sender takes a long time to execute 
    it won't affect the other senders in this connection.
    The queue size for each sender is default 100 and it can be configured by using "queue_size" in arguments.
    """
    def __init__(self, backend, arguments):
        """ Constructor
        :param backend: the backend
        :param arguments: two attributes are supported in the arguments
          {"queue_size":100,
           "senders":[...]}
           and at least one sender is mandatory in the list of senders.
        """
        super(parallel_connection, self).__init__(backend)
        queue_size=100
        if "queue_size" in arguments:
            queue_size = arguments["queue_size"]

        self._senders = []
        if "senders" in arguments:
            for sender_conf in arguments["senders"]:
                sender = parallel_connection_sender(sender_manager.from_conf(backend, sender_conf), queue_size)
                sender.start()
                self._senders.append(sender)
        else:
            raise Exception("Requires 'senders' in arguments")
        
    def publish(self, path, meta):
        for sender in self._senders:
            try:
                sender.send(path, meta)
                logger.debug("Successfully passed file to threaded %s, ID:'%s'"%(sender.id(), util.create_fileid_from_meta(meta)))
            except Exception as e:
                logger.exception("Failed to pass file to threaded %s, ID:'%s'"%(sender.id(), util.create_fileid_from_meta(meta)))

    def stop(self):
        for sender in self._senders:
            try:
                sender.stop()
            except:
                pass    

class combined_connection(publisher_connection):
    """Combined connection is a way to combine different connection types into one so that you for example can
    have different connections in one. For example, assume that you always wants a file to be sent to a specific
    target and then that you want a sequence of fail over connections after that.
    """
    def __init__(self, backend, arguments):
        super(combined_connection, self).__init__(backend)
        self._connections = []
        if "connections" in arguments:
            for conncfg in arguments["connections"]:
                if "class" in conncfg:
                    args = []
                    if "arguments" in conncfg:
                        args = conncfg["arguments"]
                    self._connections.append(connection_manager.from_conf(backend, conncfg["class"], args))
        else:
            raise Exception("Requires 'connections' in arguments")
        
    def publish(self, path, meta):
        """ Publishes the file to all connections for this connection
        :param path: the file path
        :param meta: the metadata 
        """
        for connection in self._connections:
            try:
                connection.publish(path, meta)
            except Exception as e:
                logger.exception("Failed to publish file to %s, ID:'%s'"%(sender.id(), util.create_fileid_from_meta(meta)))


class connection_manager(object):
    """The connection manager is used for creating connection instances from the provided configuration
    """
    def __init__(self):
        """Constructor
        """
        pass
    
    @classmethod
    def from_conf(self, backend, clz, arguments):
        """Creates an instance of clz with specified arguments
        :param clz: class name specified as <module>.<classname>
        :param arguments: a list of arguments that should be used to initialize the class       
        """
        if clz.find(".") > 0:
            logger.info("Creating connection handler '%s'"%clz)
            lastdot = clz.rfind(".")
            module = importlib.import_module(clz[:lastdot])
            classname = clz[lastdot+1:]
            return getattr(module, classname)(backend, arguments)
        else:
            raise Exception("Must specify class as module.class")
