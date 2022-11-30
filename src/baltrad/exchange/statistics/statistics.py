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

## statistics-manager and some plugins

## @file
## @author Anders Henja, SMHI
## @date 2022-11-29
from abc import abstractmethod
import logging
import datetime
from threading import Thread
from baltrad.exchange.db.sqldatabase import statistics, statentry

logger = logging.getLogger("baltrad.exchange.statistics.statistics")

class simple_stat_plugin(object):
    """ Simple statistics plugin that will call the stat mgrs increment function
    """
    def __init__(self, spid, sptype, statmgr):
        """ Constructor
        :param spid: The statistics plugin id
        :param sptype: The type. Either add == only add entries to statentry, count == only update count or both == do both
        :param statmgr: The statistics manager keeping track of the dbinstance
        """
        self._spid = spid
        self._sptype = sptype
        self._statmgr = statmgr
        self._save_post = False
        self._increment_counter = True
        if sptype == "add":
            self._save_post = True
            self._increment_counter = False
        elif sptype == "both":
            self._save_post = True
            self._increment_counter = True

    def increment(self, origin, meta):
        """ Calls the statistics managers increment method
        :param origin: The origin
        :param meta: The metadata
        """
        self._statmgr.increment(self._spid, origin, meta, self._save_post, self._increment_counter)

class statistics_manager:
    """ The statistics manager. Will create and register the statistics plugin
    """
    def __init__(self, db):
        """Constructor
        """
        self._sqldatabase = db

    def sqldatabase(self):
        """
        :return the sqlalchemy database instance used
        """
        return self._sqldatabase

    def get_statistics(self, spid, origin, source_name):
        """Returns the statistics for the specified post, origin and source_name"""
        return {}

    def increment(self, spid, origin, meta, save_post=False, increment_counter=True):
        """ Increments a counter that is defined by:
        :param spid: The id used to identify this statistics post
        :param orgin: the origin (may be null, indicating unknown origin)
        :param meta: the metadata
        """
        source = meta.bdb_source_name
        if increment_counter:
            self._sqldatabase.increment_statistics(spid, origin, source)
        if save_post:
            self._sqldatabase.add(statentry(spid, origin, source, datetime.datetime.now()))

    @classmethod
    def plugin_from_conf(self, conf, statmgr):
        """Creates a stat plugin from the configuration
        :param conf: The config as a dictionary
        :param statmgr: The statistics manager to use
        :returns a stat plugin
        """
        spid = None
        sptype = "count"
        if "id" in conf:
            spid = conf["id"]
        else:
            raise Exception("Invalid configuration statistics: %s"%conf)

        if "type" in conf:
            sptype = conf["type"]
        return simple_stat_plugin(spid, sptype, statmgr)

    @classmethod
    def plugins_from_conf(self, conf, statmgr):
        """Creates a stat plugin from the configuration
        :param conf: The config as a dictionary
        :param statmgr: The statistics manager to use
        :returns a stat plugin
        """
        result = []
        if not isinstance(conf, list):
            conf = list(conf)
        for c in conf:
            result.append(self.plugin_from_conf(c, statmgr))
        return result

