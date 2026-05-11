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

## A decorator indicating abstract classmethods

## @file
## @author Anders Henja, SMHI
## @date 2021-08-18
from abc import ABC, abstractmethod
from queue import Queue #, Full, Empty
from threading import Condition #Thread, 
import datetime

class abstractclassmethod(classmethod):
    """A decorator indicating abstract classmethods.

    Similar to abstractmethod.

    Usage:

        class C(metaclass=ABCMeta):
            @abstractclassmethod

            def my_abstract_classmethod(cls, ...):

                ...
    """

    __isabstractmethod__ = True

    def __init__(self, callable):
        callable.__isabstractmethod__ = True
        super(abstractclassmethod, self).__init__(callable)

class message_aware(ABC):
    @abstractmethod
    def handle_message(self, json_message, nodename):
        """Implement to handle the json message
        :param json_message: The json message
        """
        raise NotImplementedError("Not implemented handle_message")


def create_fileid_from_meta(meta):
    source = meta.bdb_source_name
    file_datetime = datetime.datetime(meta.what_date.year, meta.what_date.month, meta.what_date.day, meta.what_time.hour, meta.what_time.minute, meta.what_time.second, 0)
    file_object = meta.what_object
    file_elangle = None
    if file_object == "SCAN":
        mn = meta.find_node("/dataset1/where/elangle")
        if not mn:
            mn = meta.find_node("/where/elangle")
        if mn:
            file_elangle = mn.value
        return "nod:%s, object:%s, time:%s, elangle:%s, hash:%s"%(source, file_object, file_datetime.strftime("%Y-%m-%dT%H:%M:%SZ"), file_elangle, meta.bdb_metadata_hash)
    else:
        return "nod:%s, object:%s, time:%s, hash:%s"%(source, file_object, file_datetime.strftime("%Y-%m-%dT%H:%M:%SZ"), meta.bdb_metadata_hash)

class jobQueueShutdown(Exception):
    """thrown to indicate that an entry already exists
    """

class jobQueue:
    """Wrapper around queue.Queue to be able to shutdown. This will be supported in python 3.13 but for now
    this will be enough.
    """
    def __init__(self, qs):
        """Constructor
        :param qs: max queue size
        """
        self._queue = Queue(qs)
        self._shutdown = False
        self._condition = Condition()

    def put(self, item):
        """Puts an item into the queue without blocking.
        If queue is shutdown, the item will not be added to the queue and this will be done silently
        :param item: the item to add to the queue
        """
        with self._condition:
            try:
                if not self._shutdown:
                    self._queue.put(item, block=False)
            finally:
                self._condition.notify_all()
 
    def get(self, waittime=10):
        """Returns an item from the queue. The wait time is the time in seconds the
        thread should wait in the condition until checking for any new item in the queue.
        This condition will be notified whenever put or shutdown is called.
        :param waittime: The time to wait in seconds inside the condition
        :return: Will always return an item
        :throws: pubQueueShutdown
        """
        with self._condition:
            while not self._shutdown:
                try:
                    return self._queue.get_nowait()
                except:
                    if not self._shutdown:
                        self._condition.wait(waittime)
            raise jobQueueShutdown()

    def task_done(self):
        """Call this when task grabbed from queue is finished
        """
        self._queue.task_done()

    def shutdown(self):
        """Shuts down the queue.
        """
        with self._condition:
            self._shutdown = True
            self._condition.notify_all()