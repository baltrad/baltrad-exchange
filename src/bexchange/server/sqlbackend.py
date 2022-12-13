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
## for keeping track of sources and other miscellaneous information

## @file
## @author Anders Henja, SMHI
## @date 2021-08-18
from __future__ import absolute_import

import contextlib
import datetime
import logging
from baltrad.bdbcommon import oh5

from sqlalchemy import engine, event, exc as sqlexc, sql

from sqlalchemy.types import (
    Integer,
    Text
)

from sqlalchemy import (
    Column,
    ForeignKey,
    MetaData,
    PrimaryKeyConstraint,
    Table,
)

dbmeta = MetaData()

sources = Table("sources", dbmeta,
                Column("id", Integer, primary_key=True),
                Column("name", Text, unique=True, nullable=False),
                Column("parent", Text)
)

source_kvs = Table("source_kvs", dbmeta,
                   Column("source_id", Integer,
                          ForeignKey(sources.c.id, ondelete="CASCADE"),
                          nullable=False),
                   Column("key", Text, nullable=False),
                   Column("value", Text, nullable=False),
                   PrimaryKeyConstraint("source_id", "key"),
)


db_meta = MetaData()


logger = logging.getLogger("bexchange.server")

def force_sqlite_foreign_keys(dbapi_con, con_record):
    try:
        import sqlite3
    except ImportError:
        # built without sqlite support
        return
    if isinstance(dbapi_con, sqlite3.Connection):
        dbapi_con.execute("pragma foreign_keys=ON")

class SqlAlchemySourceManager(object):
    def __init__(self, uri="sqlite:///tmp/baltrad-exchange-source.db", poolsize=10):
        self._engine = engine.create_engine(uri, echo=False)
        if self._engine.driver == "pysqlite":
            event.listen(self._engine, "connect", force_sqlite_foreign_keys)
        self.init_tables()

    @property
    def driver(self):
        """database driver name
        """
        return self._engine.driver
    
    def init_tables(self):
        dbmeta.create_all(self._engine)

    def add_sources(self, srclist):
        with self.get_connection() as conn:
            count = conn.execute("select count(*) from sources").fetchone()["count(*)"]
            if count > 0:
                return True
            conn.execute("delete from source_kvs")
            conn.execute("delete from sources")
            for source in srclist:
                logger.info("SourceManager. adding: %s"%str(source))
                try:
                    source_id = conn.execute(
                        sources.insert(),
                        name=source.name,
                        parent=source.parent
                    ).inserted_primary_key[0]
                except sqlexc.IntegrityError:
                    raise RuntimeError("duplicate of source.name")
        
                self.insert_source_values(conn, source_id, source)
    
    def get_source(self, meta):
        with self.get_connection() as conn:
            if meta.what_source == None:
                raise LookupError("no source in metadata")
            source_id = get_source_id(conn, meta.source())
            if not source_id:
                raise LookupError("failed to look up source for " +
                                  meta.source().to_string())

        with self.get_connection() as conn:
            source = get_source_by_id(conn, source_id)
            
        # We must add file information to the metadata
        msources = meta.source()
        for k in msources.keys():
            if not source.has_key(k):
                source[k] = msources[k]
        
        return source
    
    ##
    # Insert Key-values from a source
    #
    def insert_source_values(self, conn, source_id, source):
        kvs = []
        for k, v in source.items():
            kvs.append({
                "source_id": source_id,
                "key": k,
                "value": v,
            })
    
        conn.execute(
             source_kvs.insert(),
             kvs
        )        
    
    def get_connection(self):
        """get a context managed connection to the database
        """
        return contextlib.closing(self._engine.connect())


##
# Copy-pasted from baltrad-db server functionality
def get_source_id(conn, source):
    where = sql.literal(False)
    keys = source.keys()
    ignoreORG=False
    if "ORG" in keys:
        if "WMO" in keys or "NOD" in keys or "RAD" in keys or "PLC" in keys or "WIGOS" in keys:
            ignoreORG=True
 
    for key, value in source.items():
        if ignoreORG and key == "ORG":
            continue
        #print("ADDING %s=%s"%(key,value))
        where = sql.or_(
            where,
            sql.and_(
                source_kvs.c.key==key,
                source_kvs.c.value==value
            )
        )
 
    qry = sql.select(
        [source_kvs.c.source_id, source_kvs.c.key, source_kvs.c.value],
        where,
        distinct=True
    )
     
    result = conn.execute(qry)
     
    source_id_matches = {}
    max_no_of_matches = 0
    best_match_id = None
    multiple_matches = False
    for row in result:
        source_id = row[source_kvs.c.source_id]
        if not source_id in source_id_matches:
            source_id_matches[source_id] = 0
        row_key = row[source_kvs.c.key]
        row_value = row[source_kvs.c.value]
        for key, value in source.items():
            if ignoreORG and key == "ORG":
                continue
            elif key == row_key and value == row_value:
                source_id_matches[source_id] += 1
                if source_id_matches[source_id] > max_no_of_matches:
                    max_no_of_matches = source_id_matches[source_id]
                    best_match_id = source_id
                    multiple_matches = False
                elif source_id_matches[source_id] == max_no_of_matches:
                    multiple_matches = True
     
    if multiple_matches:
        logger.debug("Could not determine source due to multiple equally matching sources found for %s." % (str(source)))
        best_match_id = None
 
    return best_match_id

def get_source_by_id(conn, source_id):
    name_qry = sql.select(
        [sources.c.name],
        sources.c.id==source_id
    )

    kv_qry = sql.select(
        [source_kvs],
        source_kvs.c.source_id==source_id
    )
    
    source = oh5.Source()

    source.name = conn.execute(name_qry).scalar()
    for row in conn.execute(kv_qry).fetchall():
        source[row["key"]] = row["value"]

    return source