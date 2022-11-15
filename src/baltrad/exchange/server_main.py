#!/usr/bin/env python3
# encoding: utf-8
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

## Client script for starting the baltrad-exchange server

## @file
## @author Anders Henja, SMHI
## @date 2021-08-18
import os
import logging
import logging.handlers
import os
import sys
import daemon
from daemon.pidfile import TimeoutPIDLockFile
import lockfile
from baltrad.exchange import config,exchange_optparse
from baltrad.exchange.web import app

#from cherrypy import wsgiserver

import urllib.parse as urlparse
    
logger = logging.getLogger("baltrad.exchange")

SYSLOG_ADDRESS = "/dev/log"
SYSLOG_FACILITY = "local3"

def excepthook(*exc_info):
    logger.error("unhandled exception", exc_info=exc_info)
    sys.exit(1)

def create_optparser():
    optparser = exchange_optparse.create_parser()
    optparser.set_usage(
        "%s [--conf=CONFFILE] [ARGS]" % (
            os.path.basename(sys.argv[0])
        )
    )
    optparser.add_option(
        "--conf", type="path", dest="conffile",
        help="configuration file",
    )
    return optparser

def read_config(conffile):
    if not conffile:
        raise SystemExit("configuration file not specified")
    try:
        return config.Properties.load(conffile)
    except IOError:
        raise SystemExit("failed to read configuration from " + conffile)

def get_logging_level(conf):
    v = conf.get("baltrad.exchange.log.level", "INFO")
    if v == "DEBUG":
        return logging.DEBUG
    elif v == "INFO":
        return logging.INFO
    elif v == "WARN":
        return logging.WARN
    elif v == "WARNING":
        return logging.WARNING
    elif v == "ERROR":
        return logging.ERROR
    else:
        return logging.INFO

def configure_logging(opts, logtype, logid, level=logging.INFO):
    logger = logging.getLogger()
    logger.setLevel(level)

    default_formatter = logging.Formatter('%(asctime)-15s %(levelname)-8s %(message)s')
    if opts.foreground or logtype == 'stdout':
        handler = logging.StreamHandler(sys.stdout)
        add_loghandler(logger, handler, default_formatter)
    if opts.logfile:
        handler = logging.handlers.WatchedFileHandler(opts.logfile)
        add_loghandler(logger, handler, default_formatter)
    if logtype == "syslog":
        handler = logging.handlers.SysLogHandler(SYSLOG_ADDRESS, facility=SYSLOG_FACILITY)
        formatter = logging.Formatter('python[' + logid + ']: %(name)s: %(message)s')
        add_loghandler(logger, handler, formatter)

    
def add_loghandler(logger, handler, formatter=None):   
    handler.setFormatter(formatter)
    logger.addHandler(handler)

## Checks if the process with provided pid is running
# by checking the /proc directory.
# @param pid - the pid to check for
# @return True if a process with provided pid is running, otherwise False
def isprocessrunning(pid):
    return os.path.exists("/proc/%d"%pid)

def run():
    optparser = create_optparser()
    optparser.add_option(
        "--foreground", action="store_true",
        default=False,
        help="don't detach the process"
    )
    optparser.add_option(
        "--logfile", type="path", action="store",
        help="location of the log file",
    )
    optparser.add_option(
        "--pidfile", type="path", action="store",
        default="/var/run/baltrad-exchange.pid",
        help="location of the pid file"
    )

    opts, args = optparser.parse_args()
    conf = read_config(opts.conffile)

    pidfile=TimeoutPIDLockFile(opts.pidfile, acquire_timeout=1.0)

    daemon_ctx = daemon.DaemonContext(
        working_directory="/",
        chroot_directory=None,
        stdout=sys.stdout if opts.foreground else None,
        stderr=sys.stderr if opts.foreground else None,
        detach_process=not opts.foreground,
        prevent_core=False,
        pidfile=pidfile
    )
    
    # try locking the pidfile to report possible errors to the user
    tryagain = False
    try:
        with pidfile:
            pass
    except lockfile.AlreadyLocked:
        tryagain = True
    except lockfile.LockFailed:
        tryagain = True
    except lockfile.LockTimeout:
        tryagain = True

    if tryagain:
        pid = lockfile.pidlockfile.read_pid_from_pidfile(opts.pidfile)
        if pid != None and not isprocessrunning(pid):
            try:
                message = "pidfile exists but it seems like process is not running, probably due to an uncontrolled shutdown. Resetting.\n"
                sys.stderr.write(message)
                os.remove(opts.pidfile)
            except:
                pass
    
        try:
            with pidfile:
                pass
        except lockfile.AlreadyLocked:
            raise SystemExit("pidfile already locked: %s" % opts.pidfile)
        except lockfile.LockFailed:
            raise SystemExit("failed to lock pidfile: %s" % opts.pidfile)
        except lockfile.LockTimeout:
            raise SystemExit("lock timeout on pidfile: %s" % opts.pidfile)

    server_uri = conf["baltrad.exchange.uri"]

    with daemon_ctx:
        try:
            from cheroot.wsgi import WSGIServer
        except:
            from cherrypy.wsgiserver import CherryPyWSGIServer as WSGIServer

        try:
            from cheroot.ssl.builtin import BuiltinSSLAdapter
        except:
            from cherrypy.wsgiserver.ssl_builtin import BuiltinSSLAdapter
            
        logtype = conf.get("baltrad.exchange.log.type", "logfile")
        logid = conf.get("baltrad.exchange.log.id", "baltrad.exchange")
        configure_logging(opts, logtype, logid, get_logging_level(conf))

        logging.getLogger("paramiko").setLevel(logging.WARNING) # Disable some paramiko loggings

        sys.excepthook = excepthook
        application = app.from_conf(conf)
        parsedurl = urlparse.urlsplit(server_uri)
        cherryconf = conf.filter("baltrad.exchange.")
        nthreads = cherryconf.get_int("threads", 10)
        nbacklog = cherryconf.get_int("backlog", 5)
        ntimeout = cherryconf.get_int("timeout", 10)

        server = WSGIServer((parsedurl.hostname, parsedurl.port), application,
            numthreads=nthreads, request_queue_size=nbacklog, timeout=ntimeout)
        if parsedurl.scheme == "https":
            # Generate test certificate / key by:
            # openssl req  -nodes -new -x509  -keyout server.key -out server.cert
            server.ssl_adapter=BuiltinSSLAdapter(cherryconf.get("server.certificate"),
                                                 cherryconf.get("server.key"))

        logger.info("REST server listening on port '%d' supporting scheme: %s"%(parsedurl.port, parsedurl.scheme))
        try:
            server.start()
        finally:
            server.stop()
