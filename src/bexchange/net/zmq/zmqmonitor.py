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

## Functionality for monitoring a zmq publication using the zmq api

## @file
## @author Anders Henja, SMHI
## @date 2024-01-12

import zmq, hmac, hashlib, shutil, os
import logging, time, re, datetime
from tempfile import NamedTemporaryFile

from sqlalchemy import asc,desc,func
from sqlalchemy import engine, event, exc as sqlexc, sql
from sqlalchemy.orm import mapper, sessionmaker

from bexchange.db import util as dbutil

from baltrad.bdbcommon import oh5, expr

from sqlalchemy.types import (
    Integer,
    Text,
    TIMESTAMP,
    DateTime,
    Float,
    Boolean
)

from sqlalchemy import (
    Column,
    ForeignKey,
    MetaData,
    PrimaryKeyConstraint,
    Table,
)

try:
    import _pyhl as pyhl
except ImportError as e:
    pyhl = None

try:
    import h5py
except ImportError as e:
    h5py = None


dbmeta = MetaData()

db_zmqmonitor_entry = Table("zmqmonitor_entry", dbmeta,
                Column('id', Integer, primary_key=True),
                Column('filename', Text, nullable=False),
                Column("entrytime", TIMESTAMP, nullable=False),
                Column('hmac_ok', Boolean, nullable=False),
                Column("file_valid", Boolean, nullable=False),
                Column("hmac", Text, nullable=True),
                Column("source", Text, nullable=True),
                Column("datetime", DateTime, nullable=True),
                Column("object_type", Text, nullable=True),
                Column("elangle", Float, nullable=True),
                Column("quantities", Text, nullable=True)
)

SOURCE_PATTERN = re.compile(".*NOD:([a-z]{5]).*")
SOURCE_FNAME_PATTERN = re.compile("([a-z]{5})_.*")

class zmqmonitor_entry(object):
    def __init__(self, filename, entrytime, hmac_ok, hmac=None, source=None, dt=None, object_type=None, elangle=None, file_valid=None, quantities=None):
        """ Represents one entry. 
        """
        self.filename = filename
        self.entrytime = entrytime
        self.hmac_ok = hmac_ok
        self.hmac = hmac
        self.source = source
        self.datetime = dt
        self.object_type = object_type
        self.elangle = elangle
        self.file_valid = file_valid
        self.quantities = quantities

mapper(zmqmonitor_entry, db_zmqmonitor_entry)

logger = logging.getLogger("bexchange.net.zmq.zmqmonitor")

def force_sqlite_foreign_keys(dbapi_con, con_record):
    try:
        import sqlite3
    except ImportError:
        # built without sqlite support
        return
    if isinstance(dbapi_con, sqlite3.Connection):
        dbapi_con.execute("pragma foreign_keys=ON")

class SqlZmqMonitorDBManager(object):
    """The DB manager providing handling of zmq monitor related information
    :param uri: The uri to database where sources are stored
    :param poolsize: the size of the db connection pool. In the case of sqlite, this will not be used
    """
    def __init__(self, uri="sqlite:///tmp/baltrad-zmq-monitor.db", poolsize=10):
        self._engine = dbutil.create_engine_from_url(uri, poolsize)
        if self._engine.driver == "pysqlite":
            event.listen(self._engine, "connect", force_sqlite_foreign_keys)
        self.init_tables()
        dbmeta.bind = self._engine
        self.Session = sessionmaker(bind=self._engine)        

    @property
    def driver(self):
        """
        :return: database driver name
        """
        return self._engine.driver
    
    def init_tables(self):
        """Initializes the database tables
        """
        dbmeta.create_all(self._engine)

    def get_connection(self):
        """get a context managed connection to the database
        """
        return contextlib.closing(self._engine.connect())

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

class zmqmonitor(object):
    def __init__(self, address, hmackey, dbfile="sqlite:////tmp/baltrad-zmq-monitor.db", tmpfolder=None, quantities=False):
        """Constructor
        Monitors a zmq publisher and stores information about all received files in a sqlite database that can be queried
        for statistics and information.
        """
        self._address = address
        self._hmackey = hmackey
        self._received_files = {}
        self._lastdt = None
        self._tmpfolder = tmpfolder
        self._dbfile = dbfile
        self._quantities = quantities
        self._dbmanager = SqlZmqMonitorDBManager(dbfile)
        self._dbmanager.init_tables()

    def read_bdb_sources(self, odim_source_file):
        """Reads and parses the odim sources
        :param odim_source_file: file containing the odim source definitions
        :returns a list of odim sources
        """
        with open(odim_source_file) as f:
            return oh5.Source.from_rave_xml(f.read())

    def create_named_temporary_file(self):
        """Creates a named temporary file. This method only exists for unittest purpose
        :return: A NamedTemporaryFile
        """
        return NamedTemporaryFile(dir = self._tmpfolder)

    def determine_source(self, source, original_name):
        """Determines the source by first verifying if there is a NOD entry in the source eitherwise
        it will look at the original file name and verify if the first part is the source. Otherwise
        it will return the full source-information.
        """
        result = source

        m = SOURCE_PATTERN.match(source)
        if m:
            result = m.group(1)
        else:
            m = SOURCE_FNAME_PATTERN.match(original_name)
            if m:
                result = m.group(1)

        return result


    def read_hlhdf(self, fname, original_name):
        f = pyhl.read_nodelist(fname)
        f.selectMetadata()
        f.fetch()
        values = {}

        nodenames = f.getNodeNames()

        source = self.determine_source(f.getNode("/what/source").data(), original_name)

        object_type = f.getNode("/what/object").data()
        datestr = f.getNode("/what/date").data()
        timestr = f.getNode("/what/time").data()

        values["source"] = source
        values["object_type"] = object_type
        values["datetime"] = datetime.datetime.strptime(datestr+timestr, "%Y%m%d%H%M%S")
        values["elangle"] = None
        values["quantities"] = None

        if object_type.upper() == "SCAN":
            values["elangle"] = f.getNode("/dataset1/where/elangle").data()

        if self._quantities:
            quantities = []
            nrsets = 1
            while "/dataset%d" in nodenames:
                nrsets = nrsets + 1
            for i in range(1, nrsets+1):
                dsetname = "/dataset%d"%i
                for j in range(1, 20):
                    quanname = "%s/data%d/what/quantity"%(dsetname, j)
                    if quanname not in nodenames:
                        break
                    qvalue = f.getNode(quanname).data()
                    if not qvalue in quantities:
                        quantities.append(qvalue)
            values["quantities"] = ",".join(quantities)

        return values

    def read_h5py(self, fname, original_name):
        f = h5py.File(fname)
        values = {}

        source = self.determine_source(f["/"]["what"].attrs["source"].decode('utf-8'), original_name)

        object_type = f["/"]["what"].attrs["object"].decode('utf-8')
        datestr = f["/"]["what"].attrs["date"].decode('utf-8')
        timestr = f["/"]["what"].attrs["time"].decode('utf-8')

        values["source"] = source
        values["object_type"] = object_type
        values["datetime"] = datetime.datetime.strptime(datestr+timestr, "%Y%m%d%H%M%S")
        values["elangle"] = None
        values["quantities"] = None

        if object_type.upper() == "SCAN":
            values["elangle"] = f["/"]["dataset1"]["where"].attrs["elangle"]

        if self._quantities:
            quantities = []
            nrsets = 1
            while "/dataset%d" in f:
                nrsets = nrsets + 1
            for i in range(1, nrsets+1):
                dsetname = "/dataset%d"%i
                for j in range(1, 20):
                    if "%s/data%d/what"%(dsetname, j) not in f:
                        break
                    if "quantity" not in f["%s/data%d/what"%(dsetname, j)].attrs:
                        break
                    qvalue = f["%s/data%d/what"%(dsetname, j)].attrs["quantity"].decode("utf-8")
                    if not qvalue in quantities:
                        quantities.append(qvalue)
            values["quantities"] = ",".join(quantities)

        return values

    def read_file_content(self, fname, original_name):
        if pyhl is not None:
            return self.read_hlhdf(fname, original_name)
        if h5py is not None:
            return self.read_h5py(fname, original_name)
        raise RuntimeError("Could neither use h5py or pyhl")


    def process(self, b_message):
        """Process one byte message according to the data transporter protocol which is
        byte 0-20    : is the hmac
        byte 20 - 276: is the filename
        byte > 276   : actual file content
        On success an entry is stored in the database, otherwise nothing will happen.
        """
        if len(b_message) < 276:
            logger.info("Not possible to handle message since its to short")
            return

        senderHmac = b_message[:20]
        fname = b_message[20:(20+256)].decode('utf-8').replace("\0", "")
        calcHmac = hmac.new(self._hmackey.encode('ascii'), b_message[20:], hashlib.sha1)
        hmacOk = senderHmac.hex() == calcHmac.digest().hex()
        
        hmacstr = "HMAC OK!"
        if not hmacOk:
            hmacstr = "HMAC NOT OK!"
        logger.info("File arrived: %s, %s"%(fname, hmacstr))

        file_valid = False
        if hmacOk:
            with self.create_named_temporary_file() as tmp:
                tmp.write(b_message[20+256:])
                tmp.flush()
                try:
                    values = self.read_file_content(tmp.name, fname)
                    file_valid = True
                except:
                    logger.exception("Could not read file content")

        entry = zmqmonitor_entry(fname, datetime.datetime.now(), hmacOk, senderHmac.hex(), values["source"], values["datetime"], values["object_type"], values["elangle"], file_valid, values["quantities"])
        self._dbmanager.add(entry)

    def run(self, nrfiles=0):
        """Connects to the zmq publisher and starts receiving files.
        :param nrfiles: A counter if subscriber only should receive a specific number of files before breaking. Otherwise the loop is infinite.
        """
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        logger.info("Connecting to publisher: %s"%self._address)
        socket.connect(self._address)
        socket.setsockopt_string(zmq.SUBSCRIBE, "")

        ctr = nrfiles
        while True:
            b_message = socket.recv()
            self.process(b_message)
            if nrfiles > 0 and ctr <= 0:
                break
            ctr = ctr - 1
