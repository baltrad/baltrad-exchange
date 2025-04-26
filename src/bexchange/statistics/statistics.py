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
import json, re
from bexchange.db.sqldatabase import statistics, statentry
from bexchange import util

RE_DTFILTER_PATTERN=re.compile(r"^\s*(datetime|entrytime|optime|delay)\s*([<>!=]+)\s*([0-9:\-T\.]+)\s*$")

logger = logging.getLogger("bexchange.statistics.statistics")

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

    def list_statistic_ids(self, nid):
        """
        :returns the list of available ids
        """
        result = []

        ids = self._sqldatabase.list_statistic_ids()
        for i in ids:
            result.append({"spid":i, "totals":True})

        ids = self._sqldatabase.list_statentry_ids()
        for i in ids:
            result.append({"spid":i, "totals":False})

        return json.dumps(result)

    def parse_filter(self, parsestr):
        result = []
        tokens = parsestr.split("&&")
        for dtstr in tokens:
            m = RE_DTFILTER_PATTERN.match(dtstr)
            if m:
                dt = None
                name=m.group(1)
                if name in ["datetime", "entrytime"]:
                    try:
                        tstr = m.group(3)
                        if len(tstr) == 12:
                            dt = datetime.datetime.strptime(tstr, '%Y%m%d%H%M')
                        else:
                            dt = datetime.datetime.strptime(tstr, '%Y%m%d%H%M%S')
                    except ValueError:
                        dt = datetime.datetime.strptime(m.group(3), '%Y%m%d%H%M%S')
                    criteria = [m.group(1), m.group(2), dt]
                    result.append(criteria)
                elif name in ["optime", "delay"]:
                    criteria = [m.group(1), m.group(2), int(m.group(3))]
                    result.append(criteria)
            else:
                raise Exception("Format of dtfilter must be name[OP]value where name is one of datetime, entrytime or optime")
        return result

    def get_statistics_entries(self, nid, querydata):
        """Returns the statistic entries for the specified post, origin and source_name"""
        spid = None
        origin = None
        totals = False
        hashid = None
        sources = []
        filters = None
        object_type = None
        origins = []
        logger.debug("querydata: %s"%querydata)
        if "spid" in querydata:
            spid = querydata["spid"]

        if "origins" in querydata:
            sorigins = querydata["origins"]
            if sorigins:
                origins = sorigins.split(",")

        if "sources" in querydata:
            ssources = querydata["sources"]
            if ssources:
                sources = ssources.split(",")

        if "hashid" in querydata:
            hashid = querydata["hashid"]

        if "totals" in querydata:
            totals = querydata["totals"]

        if "filter" in querydata and querydata["filter"]:
            opfilter = querydata["filter"].strip()
            filters = self.parse_filter(opfilter)

        if "object_type" in querydata:
            object_type = querydata["object_type"]

        qmethod=None
        if "method" in querydata:
            qmethod = querydata["method"]

        if totals:
            entries = self._sqldatabase.find_statistics(spid, origins, sources)
        else:
            if qmethod is None or qmethod != "average":
                entries = self._sqldatabase.find_statentries(spid, origins, sources, hashid=hashid, filters=filters, object_type=object_type)
            else:
                entries = self._sqldatabase.get_average_statentries(spid, origins, sources)
        
        return entries

    def get_statistics(self, nid, querydata):
        """Returns the statistics for the specified post, origin and source_name"""
        entries = self.get_statistics_entries(nid, querydata)
        jslist = [e.json_repr() for e in entries]
        return json.dumps(jslist)

    def cleanup_statentry(self, age):
        now = datetime.datetime.now()
        maxage = now - datetime.timedelta(hours=age)
        self._sqldatabase.cleanup_statentries(maxage)

    def increment(self, spid, origin, meta, save_post=False, increment_counter=True, optime=0, optime_info=None):
        """ Increments a counter that is defined by:
        :param spid: The id used to identify this statistics post
        :param orgin: the origin (may be null, indicating unknown origin)
        :param meta: the metadata
        """
        try:
            source = meta.bdb_source_name
            if increment_counter:
                self._sqldatabase.increment_statistics(spid, origin, source)
        except:
            logger.exception("An error occured when incrementing statistics for spid:%s, origin:%s, ID:%s"%(spid, origin, util.create_fileid_from_meta(meta)))

        if save_post:
            file_datetime = datetime.datetime(meta.what_date.year, meta.what_date.month, meta.what_date.day, meta.what_time.hour, meta.what_time.minute, meta.what_time.second, 0, tzinfo=datetime.timezone.utc)
            file_object = meta.what_object
            file_elangle = None
            if file_object == "SCAN":
                mn = meta.find_node("/dataset1/where/elangle")
                if not mn:
                    mn = meta.find_node("/where/elangle")
                if mn:
                    file_elangle = mn.value

            entrytime = datetime.datetime.now(datetime.timezone.utc)
            delay = (entrytime - file_datetime).seconds
            try:
                self._sqldatabase.add(statentry(spid, origin, source, meta.bdb_metadata_hash, datetime.datetime.now(datetime.timezone.utc), optime, optime_info, delay, file_datetime, file_object, file_elangle))
            except:
                logger.exception("An error occured when adding statentry for spid:%s, origin:%s, ID:%s"%(spid, origin, util.create_fileid_from_meta(meta)))


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

