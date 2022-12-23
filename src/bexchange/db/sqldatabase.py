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

## The SQL functionality that is used by the server. As default it uses a sqlite database
## for miscellaneous operations and also made available to plugins

## @file
## @author Anders Henja, SMHI
## @date 2021-08-18
from __future__ import absolute_import

import contextlib
import datetime
import logging

from sqlalchemy import asc,desc,func
from sqlalchemy import engine, event, exc as sqlexc, sql
from sqlalchemy.orm import mapper, sessionmaker

from sqlalchemy.types import (
    Integer,
    BigInteger,
    Text,
    DateTime,
    TIMESTAMP
)

from sqlalchemy import (
    Column,
    ForeignKey,
    MetaData,
    PrimaryKeyConstraint,
    Table,
)

from bexchange.db import util as dbutil

logger = logging.getLogger("bexchange.db.sqldatabase")

dbmeta = MetaData()

##
# Used to ensure that the 
#The created table is in format | spid | origin | source | counter | update |
#
db_statistics = Table("exchange_statistics", dbmeta,
                Column("spid", Text, nullable=False),
                Column("origin", Text, nullable=False),
                Column("source", Text, nullable=True),
                Column("counter", BigInteger, nullable=False),
                Column("updated_at", DateTime, nullable=False),
                PrimaryKeyConstraint("spid","origin","source")
)

db_statentry = Table("exchange_statentry", dbmeta,
                Column("spid", Text, nullable=False),
                Column("origin", Text, nullable=False),
                Column("source", Text, nullable=True),
                Column("hashid", Text, nullable=True),
                Column("entrytime", TIMESTAMP, nullable=False),
                Column("optime", Integer, nullable=False),
                Column("optime_info", Text, nullable=True),

                PrimaryKeyConstraint("spid","origin","source", "entrytime")
)

class statistics(object):
    def __init__(self, spid, origin, source, counter, updated_at):
        """ Keeps the totals for a specified spid + origin + source
        :param spid: The statistics plugin id
        :param origin: Origin for this stat
        :param source: Source
        :param counter: Counter
        :param updated_at: When entry last was updated
        """
        self.spid = spid
        self.origin = origin
        self.source = source
        self.counter = counter
        self.updated_at = updated_at

    def json_repr(self):
        return {
            "spid":self.spid,
            "origin":self.origin,
            "source":self.source,
            "counter":self.counter,
            "updated_at":self.updated_at.isoformat()
        }

class statentry(object):
    def __init__(self, spid, origin, source, hashid, entrytime, optime=0, optime_info=None):
        """ Represents one increment entry. Used for creating averages and such information
        :param spid: The statistics plugin id
        :param origin: Origin for this stat
        :param source: Source
        :param hashid: The hash id
        :param entrytime: When this entry was created
        :param optime: Operation time entry in ms
        :param optime_info: Used to identify what was timed
        """
        self.spid = spid
        self.origin = origin
        self.source = source
        self.hashid = hashid
        self.entrytime = entrytime
        self.optime = optime
        self.optime_info = optime_info
        self.attributes = {}

    def json_repr(self):
        result = {
            "spid":self.spid,
            "origin":self.origin,
            "source":self.source,
            "hashid":self.hashid,
            "entrytime":self.entrytime.isoformat(),
            "optime":self.optime,
            "optime_info":self.optime_info
        }
        if self.attributes:
            for a in self.attributes:
                result[a] = self.attributes[a]

        return result

    def add_attribute(self, name, value):
        if not "attributes" in self.__dict__:
            self.attributes = {}
        self.attributes[name] = value

mapper(statistics, db_statistics)
mapper(statentry, db_statentry)

logger = logging.getLogger("bexchange.db.sqldatabase")

def force_sqlite_foreign_keys(dbapi_con, con_record):
    try:
        import sqlite3
    except ImportError:
        # built without sqlite support
        return
    if isinstance(dbapi_con, sqlite3.Connection):
        dbapi_con.execute("pragma foreign_keys=ON")

class SqlAlchemyDatabase(object):
    def __init__(self, uri="sqlite:///tmp/baltrad-exchange.db", poolsize=10):
        """Constructor
        :param uri: The uri pointing to the database.
        :param poolsize: How many database connections we should use
        """
        self._engine = dbutil.create_engine_from_url(uri, poolsize)
        if self._engine.driver == "pysqlite":
            event.listen(self._engine, "connect", force_sqlite_foreign_keys)
        self.init_tables()
        dbmeta.bind = self._engine
        self.Session = sessionmaker(bind=self._engine)

    @property
    def driver(self):
        """database driver name
        """
        return self._engine.driver

    def init_tables(self):
        dbmeta.create_all(self._engine)
        logger.info("Initialized alchemy database")

    def get_connection(self):
        """get a context managed connection to the database
        """
        return contextlib.closing(self._engine.connect())

    def get_session(self):
        session = self.Session()
        return contextlib.closing(session)

    def get_statistics_entry(self, spid, origin, source):
        with self.get_session() as s:
            q = s.query(statistics).filter(statistics.spid == spid).filter(statistics.origin == origin).filter(statistics.source == source)
            return q.one_or_none()

    def list_statistic_ids(self):
        with self.get_session() as s:
            entries = s.query(statistics.spid).distinct(statistics.spid).all()
            result = [e[0] for e in entries]
            return result

    def list_statentry_ids(self):
        with self.get_session() as s:
            entries = s.query(statentry.spid).distinct(statentry.spid).all()
            result = [e[0] for e in entries]
            return result

    def find_statistics(self, spid, origin, sources):
        with self.get_session() as s:
            q = s.query(statistics).filter(statistics.spid == spid)
            if origin:
                q = q.filter(statistics.origin == origin)
            if sources and len(sources) > 0:
                q = q.filter(statistics.source.in_(sources))
            return q.all()

    def find_statentries(self, spid, origin, sources, hashid=None):
        with self.get_session() as s:
            q = s.query(statentry).filter(statentry.spid == spid)
            if origin:
                q = q.filter(statentry.origin == origin)
            if sources and len(sources) > 0:
                q = q.filter(statentry.source.in_(sources))
            if hashid:
                q = q.filter(statentry.hashid == hashid)
            q = q.order_by(asc(statentry.origin)) \
                .order_by(asc(statentry.source)) \
                .order_by(asc(statentry.entrytime))
            return q.all()

    def get_average_statentries(self, spid, origin, sources, hashid=None):
        with self.get_session() as s:
            print("Creating query")
            q = s.query(statentry, func.avg(statentry.optime)).filter(statentry.spid == spid)
            if origin:
                q = q.filter(statentry.origin == origin)
            if sources and len(sources) > 0:
                q = q.filter(statentry.source.in_(sources))

            q = q.group_by(statentry.spid, statentry.origin, statentry.source)
            q = q.order_by(asc(statentry.spid)) \
                .order_by(asc(statentry.origin)) \
                .order_by(asc(statentry.source)) \
                .order_by(asc(statentry.entrytime))

            qresult = q.all()
            result = []
            for e in qresult:
                e[0].add_attribute("average", e[1])
                print("Appending: %s"%e[0])
                result.append(e[0])
            return result


    def cleanup_statentries(self, maxagedt):
        logger.info("Cleanup of statentries older than %s"%maxagedt.strftime("%Y-%m-%d %H:%M"))
        q = db_statentry.delete().where(db_statentry.c.entrytime < maxagedt.strftime("%Y-%m-%d %H:%M"))
        logger.debug("Query: %s"%q)
        self._engine.execute(q)

    def increment_statistics(self, spid, origin, source):
        with self.get_session() as session:
            stats = session.query(statistics).filter(statistics.spid == spid).filter(statistics.origin == origin).filter(statistics.source == source).first()
            if not stats:
                stats = statistics(spid, origin, source, 0, datetime.datetime.now())
            stats.counter += 1
            stats.updated_at = datetime.datetime.now()
            try:
                session.merge(stats)
                session.commit()
            except:
                session.rollback()
                raise
            finally:
                session.close()

    def add(self, obj):
        session = self.Session()
        xlist = obj
        if not isinstance(obj, list):
            xlist = [obj]
        try:
            for x in xlist:
                nx = session.add(x)
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
        session = None

    def update(self, obj):
        session = self.Session()
        xlist = obj
        if not isinstance(obj, list):
            xlist = [obj]
        try:
            for x in xlist:
                nx = session.merge(x)
                session.add(nx)
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
        session = None