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

## Commands provided by the baltrad-exchange-client

## @file
## @author Anders Henja, SMHI
## @date 2021-08-18
from __future__ import print_function        

from abc import abstractmethod, ABCMeta
import abc

import json
import os, sys
import socket
import urllib.parse as urlparse
import pkg_resources
import datetime,time,math
import subprocess
from tempfile import NamedTemporaryFile

from http import client as httplibclient

# This should always be available
from baltradcrypto import crypto
from baltradcrypto.crypto import keyczarcrypto

class ExecutionError(RuntimeError):
    pass

class Command(object):
    """command-line client command interface
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def update_optionparser(self, parser):
        raise NotImplementedError()
    
    @abstractmethod
    def execute(self, database, opts, args):
        """execute this command

        :param database: a database instance to operate on
        :param opts: options passed from command line
        :param args: arguments passed from command line
        """
        raise NotImplementedError()

    def __call__(self, database, opts, args):
        return self.execute(database, opts, args)

    @classmethod
    def get_implementation_by_name(cls, name):
        """get an implementing class by name

        the implementing class is looked up from 'baltrad.bdbclient.commands'
        entry point. 

        :raise: :class:`LookupError` if not found
        """
        try:
            return pkg_resources.load_entry_point(
                "bexchange",
                "bexchange.client.commands",
                name
            )
        except ImportError:
            raise LookupError(name)

    @classmethod
    def get_commands(cls):
        return pkg_resources.get_entry_map("bexchange")["bexchange.client.commands"].keys()

class StoreFile(Command):
    def update_optionparser(self, parser):
        usg = parser.get_usage().strip()

        description = """
        
Posts a sequence of files to the exchange server.
        """

        usage = usg + " FILE [ FILE]" + description

        parser.set_usage(usage)

    def execute(self, server, opts, args):
        for path in args: 
            try:
                with open(path, "rb") as data:
                    entry = server.store(data)
                print("%s stored"%(path))
            except Exception as e:
                print("Error occured when storing '%s': %s"%(path, e.__str__()))

class BatchTest(Command):
    SRC_MAPPING={
        "sekrn":"WMO:02032,RAD:SE40,PLC:Kiruna,CMT:sekrn,NOD:sekrn",
        "sella":"WMO:02092,RAD:SE41,PLC:Luleå,CMT:sella,NOD:sella",
        "seosd":"WMO:02200,RAD:SE42,PLC:Östersund,CMT:seosd,NOD:seosd",
        "seoer":"WMO:02262,RAD:SE43,PLC:Örnsköldsvik,CMT:seoer,NOD:seoer",
        "sehuv":"WMO:02334,RAD:SE44,PLC:Hudiksvall,CMT:sehuv,NOD:sehuv",
        "selek":"WMO:02430,RAD:SE45,PLC:Leksand,CMT:selek,NOD:selek",
        "sehem":"WMO:02588,RAD:SE47,PLC:Hemse,CMT:sehem,NOD:sehem",
        "seatv":"WMO:02570,RAD:SE48,PLC:Åtvidaberg,CMT:seatv,NOD:seatv",
        "sevax":"WMO:02600,RAD:SE49,PLC:Vara,CMT:sevax,NOD:sevax",
        "seang":"WMO:02606,RAD:SE50,PLC:Ängelholm,CMT:seang,NOD:seang",
        "sekaa":"WMO:02666,RAD:SE51,PLC:Karlskrona,CMT:sekaa,NOD:sekaa",
        "sebaa":"WMO:00000,RAD:SE52,PLC:Bålsta,CMT:sebaa,NOD:sebaa",
        }

    def update_optionparser(self, parser):
        usg = parser.get_usage().strip()

        description = """

The batchtest uses a basefile that either is a scan or a pvol and uses that as a template and
then updates the source and datetime before sending it to the exchange server. It is only the
information for the swedish radars sekrn, sella, seosd, seoer, sehuv, selek, sehem, seatv, sevax, 
seang, sekaa and sebaa that will be set in what/source. The soure set will be in the format
WMO:02666,RAD:SE51,PLC:Karlskrona,CMT:sekaa,NOD:sekaa.
        """

        usage = usg + " --basefile=FILENAME" + description

        parser.set_usage(usage)

        parser.add_option(
            "--basefile", dest="basefile",
            help="Basefile that should be modified and injected")
        
        parser.add_option(
            "--datetime", dest="datetime", default=datetime.datetime.now().strftime("%Y%m%d%H%M"),
            help="Datetime")

        parser.add_option(
            "--sources", dest="sources",
            default="sekrn,sella,seosd,seoer,sehuv,selek,sehem,seatv,sevax,seang,sekaa,sebaa",
            help="The sources")
    
        parser.add_option(
            "--periods", dest="periods", type="int",
            default=1,
            help="Number of periods")
        
        parser.add_option(
            "--interval", dest="interval", type="int",
            default=5,
            help="Minutes between each period")

        parser.add_option(
            "--elangles", dest="elangles",
            default=None,
            help="Comma separated list of elevation angles (only actual for scans)")


    def execute(self, server, opts, args):
        import _raveio, _polarvolume, _polarscan
        if not opts.basefile:
            print("No basefile provided\n")
            raise ExecutionError()
        
        dt = self.parse_datetime_str(opts.datetime, opts.interval)
        if not opts.datetime:
            dt = self.get_closest_time(opts.interval)

        elangles = None
        if opts.elangles:
            elangles=[]
            telangles = opts.elangles.split(",")
            for tel in telangles:
                elangles.append(float(tel))

        for pindex in range(opts.periods):
            tstr = (dt + datetime.timedelta(minutes = pindex*opts.interval)).strftime("%Y%m%d%H%M%S")
            o = _raveio.open(opts.basefile).object
            d = tstr[:8]
            t = tstr[8:]
            o.date = d
            o.time = t

            ispolarscan=False
            if _polarscan.isPolarScan(o):
                ispolarscan=True
                if elangles is None or len(elangles)==0:
                    elangles=[o.elangle * 180.0/math.pi]

            for src in opts.sources.split(","):
                o.source = self.SRC_MAPPING[src]
                rio = _raveio.new()
                rio.object = o
                if ispolarscan:
                    for e in elangles:
                        o.elangle = e * math.pi / 180.0
                        with NamedTemporaryFile() as f:
                            rio.save(f.name)
                            with open(f.name, "rb") as data:
                                entry = server.store(data)
                else:
                    with NamedTemporaryFile() as f:
                        rio.save(f.name)
                        with open(f.name, "rb") as data:
                            entry = server.store(data)                    

    def get_closest_time(self, interval):
        t = time.localtime()
        oz = t.tm_min%interval
        return datetime.datetime(t.tm_year,t.tm_mon,t.tm_mday,t.tm_hour,t.tm_min-oz,0)

    def parse_datetime_str(self, dtstr, interval):
        year = int(dtstr[:4])
        month = int(dtstr[4:6])
        mday = int(dtstr[6:8])
        hour = int(dtstr[8:10])
        minute = int(dtstr[10:12])
        minute = minute - minute%interval
        return datetime.datetime(year,month,mday,hour,minute,0)

class PostJsonMessage(Command):
    def update_optionparser(self, parser):
        usg = parser.get_usage().strip()

        description = """

Posts a json message to the exchange server. Can be used to trigger for example a runnable job.

Example: baltrad-exchange-client post_message '{"trigger":"trigger_4"}'
        """

        usage = usg + " MESSAGE" + description

        parser.set_usage(usage)

    def execute(self, server, opts, args):
        entry = server.post_json_message(args[0])

class GetStatistics(Command):
    def update_optionparser(self, parser):
        usg = parser.get_usage().strip()

        description = """

Queries the exchange server for various statistics information. The spid is used to identify what statistics
id that should be queried for. It is possible to query for all existing ids by executing the command
list_statistic_ids.

Example: baltrad-exchange-client get_statistics --spid=server-incomming --totals
        """

        usage = usg + " --spid=STAT_ID" + description

        parser.set_usage(usage)

        parser.add_option(
            "--spid", dest="spid",
            help="What plugin id that should be queried")

        parser.add_option(
            "--sources", dest="sources", default="",
            help="The sources that should be queried")

        parser.add_option(
            "--totals", dest="totals", default=False, action="store_true",
            help="Use this option if the total should be returned instead")

        parser.add_option(
            "--method", dest="method", default=None,
            help="If some sort of analysis should be performed. Currently only average"
        )

        parser.add_option(
            "--filter", dest="filter", default=None,
            help="If filtering should be performed on datetime. Must be specified datetime<operation><value>. If you want to specify a range you can use && between two filters like --dtfilter='datetime>=20201000000000 && datetime<=20201100000000'"
        )

        parser.add_option(
            "--object_type", dest="object_type", default=None,
            help="If filtering should be performed on object_type. E.g. --object_type=PVOL"
        )

        parser.add_option(
            "--origins", dest="origins", default=None,
            help="The origins that should be included in query"
        )


    def execute(self, server, opts, args):
        response = server.get_statistics(opts.spid, opts.sources, opts.totals, opts.method, opts.filter, opts.object_type, opts.origins)
        if response.status == httplibclient.OK:
            ldata = json.loads(response.read())
            for l in ldata:
                print(l)
            #print(ldata)
        else:
            raise Exception("Unhandled response code: %s"%response.status)

class ListStatisticIds(Command):
    def update_optionparser(self, parser):
        usg = parser.get_usage().strip()

        description = """

Queries the exchange server for the available statistics ids

Example: baltrad-exchange-client list_statistic_ids
        """

        usage = usg + description

        parser.set_usage(usage)

    def execute(self, server, opts, args):
        response = server.list_statistics()
        if response.status == httplibclient.OK:
            ldata = json.loads(response.read())
            for l in ldata:
                print(l)
        else:
            raise Exception("Unhandled response code: %s"%response.status)

class ServerInfo(Command):
    def update_optionparser(self, parser):
        usg = parser.get_usage().strip()

        description = """

Provides some useful information about the server. Currently the following things can be queried for.
  uptime    - How long the server has been running

  nodename  - The name this server is identifying itself when sending files

  publickey - The public key that can be used to identify myself as

Example: baltrad-exchange-client server_info uptime
        """

        usage = usg + description

        parser.set_usage(usage)

    def execute(self, server, opts, args):
        if len(args) == 1:
            if args[0] == "uptime" or args[0] == "nodename" or args[0] == "publickey":
                response = server.get_server_info(args[0])
                if response.status == httplibclient.OK:
                    if args[0] != "publickey":
                        ldata = json.loads(response.read())
                        print(ldata)
                    else:
                        ldata = response.read()
                        print(ldata.decode())
                else:
                    raise Exception("Unhandled response code: %s"%response.status)
            else:
                print("Only valid subcommands are uptime and nodename")

class FileArrival(Command):
    def update_optionparser(self, parser):
        usg = parser.get_usage().strip()

        description = """

Functionality for querying if a file from a specific source has arrived within a given time.

The returned data will be a json dictionary with status as name and either ERROR or OK in the value.

Example: baltrad-exchange-client file_arrival --source=sella --object_type=PVOL --limit=60
{"status: "OK"}
        """

        usage = usg + description

        parser.set_usage(usage)

        parser.add_option(
            "--sources", dest="source", default="",
            help="The source that should be queried")

        parser.add_option(
            "--object_type", dest="object_type", default=None,
            help="If filtering should be performed on object_type. E.g. --object_type=PVOL"
        )

        parser.add_option(
            "--limit", dest="limit", default=300, type="int",
            help="How many minutes back that should be taken into account. Default is 300 seconds."
        )

    def execute(self, server, opts, args):
        response = server.file_arrival(opts.source, opts.object_type, opts.limit)
        if response.status == httplibclient.OK:
            ldata = json.loads(response.read())
            print(ldata)
            return ldata["status"]
        else:
            return '{"status":"ERROR"}'

class Supervise(Command):
    def update_optionparser(self, parser):
        usg = parser.get_usage().strip()

        description = """

Functionality for supervising a node. Usually, the response will be a string that either says ERROR or OK.
 Other examples can be that a count is returned. It all depends on what type of information is required.

Example: baltrad-exchange-client supervise --type=filearrival --source=sella --object_type=PVOL --limit=300
OK
        """

        usage = usg + description

        parser.set_usage(usage)

        parser.add_option(
            "--infotype", dest="infotype", default="filearrival",
            help="The type of information required that should be queried")

        parser.add_option(
            "--sources", dest="source", default="",
            help="The source that should be queried (if applicable)")

        parser.add_option(
            "--origins", dest="origins", default="",
            help="The origin that should be checked.")

        parser.add_option(
            "--object_type", dest="object_type", default=None,
            help="If filtering should be performed on object_type. E.g. --object_type=PVOL"
        )

        parser.add_option(
            "--limit", dest="limit", default=300, type="int",
            help="How many seconds back that should be taken into account when checking for nominal datetime in file. Default is 300 seconds."
        )

        parser.add_option(
            "--entrylimit", dest="entrylimit", default=0, type="int",
            help="How many seconds back that should be taken into account when checking for file arrival. Default is disabled."
        )

        parser.add_option(
            "--delay", dest="delay", default=0, type="int",
            help="Checks difference between nominal time and entry time and if the delay is higher then it's an error. Default is to be disabled."
        )

        parser.add_option(
            "--count", dest="count", default=0, type="int",
            help="Counts matches and validates that there are at least count number of occurances."
        )

    def execute(self, server, opts, args):
        response = server.supervise(opts.infotype, opts.source, opts.origins, opts.object_type, opts.limit, opts.entrylimit, opts.delay, opts.count)
        if response.status == httplibclient.OK:
            ldata = json.loads(response.read())
            return ldata["status"]
        else:
            return '{"status":"ERROR"}'
