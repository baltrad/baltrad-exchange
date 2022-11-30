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
                Column("entrytime", TIMESTAMP, nullable=False),
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

class statentry(object):
    def __init__(self, spid, origin, source, entrytime):
        """ Represents one increment entry. Used for creating averages and such information
        :param spid: The statistics plugin id
        :param origin: Origin for this stat
        :param source: Source
        :param entrytime: When this entry was created
        """
        self.spid = spid
        self.origin = origin
        self.source = source
        self.entrytime = entrytime


mapper(statistics, db_statistics)
mapper(statentry, db_statentry)

logger = logging.getLogger("baltrad.exchange.db.sqldatabase")

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
        self._engine = engine.create_engine(uri, echo=False)
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