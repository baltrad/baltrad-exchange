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

## runner-manager and some runners

## @file
## @author Anders Henja, SMHI
## @date 2022-10-28
import importlib
import logging
import pyinotify
import os, re
from threading import Thread

from baltrad.exchange.naming import namer

logger = logging.getLogger("baltrad.exchange.processor")
class runner(object):
    def __init__(self, backend, active):
        super(runner,self).__init__()
        self._backend = backend
        self._active = active
        
    def active(self):
        return self._active
    
    def setactive(self, active):
        self._active = active

    def start(self):
        raise Exception("Not implemented")

class inotify_runner_event_handler(pyinotify.ProcessEvent):
    def __init__(self, inotify_runner):
        self._runner = inotify_runner
    
    def process_IN_CLOSE_WRITE(self, event):
        logger.info("IN_CLOSE_WRITE: %s"%event.pathname)
        if not self._runner.is_ignored(event.pathname):  # avoid temporary file
            self._runner.handle_file(event.pathname)

    def process_IN_MOVED_TO(self, event):
        logger.info("IN_MOVED_WRITE: %s"%event.pathname)
        if not self._runner.is_ignored(event.pathname):  # avoid temporary file
            self._runner.handle_file(event.pathname)

class inotify_runner(runner):
    MASK = pyinotify.IN_CLOSE_WRITE | pyinotify.IN_MOVED_TO
    
    def __init__(self, backend, active, **args):
        super(inotify_runner, self).__init__(backend, active)
        self._name = "inotify-runner"
        self._folders = args["folders"]
        self._ignore_pattern = True
        self._pattern = ""
        logger.info("inotify_runner: ARGS=%s"%str(args))
        if "ignore-pattern" in args:
            self._ignore_pattern = args["ignore-pattern"]
        if "pattern" in args:
            self._pattern = args["pattern"]
        if "name" in args:
            self._name = args["name"]
        self._wm = pyinotify.WatchManager()
        self._notifier = pyinotify.Notifier(self._wm, inotify_runner_event_handler(self))

    def is_ignored(self, filename):
        logger.info("is_ignored %s"%filename)
        if self._ignore_pattern:
            return False
        bname = os.path.basename(filename)
        return re.match(self._pattern, bname) != None
    
    def handle_file(self, filename):
        logger.info("Storing file: %s"%filename)
        self._backend.store_file(filename, self._name)


    def run(self):
        self._notifier.loop()

    def start(self):
        for folder in self._folders:
            logger.info("inotify_runner(%s) watching '%s'"%(self._name, folder))
            self._wm.add_watch(folder, self.MASK)

        self._thread = Thread(target=self.run)
        self._thread.daemon = True
        self._thread.start()

class runner_manager:
    """ The runner manager. Will create and register the runner
    """
    def __init__(self):
        """Constructor
        """
        self._runners=[]

    def add_runner(self, runner):
        """Adds a runner to the manager
        :param runner: The runner that should be added
        """
        self._runners.append(runner)

    def start(self):
        for r in self._runners:
            r.start()

    @classmethod
    def create_runner(self, clz, backend, active, extra_arguments):
        """Creates an instance of clz with specified arguments
        :param clz: class name specified as <module>.<classname>
        :param arguments: a list of arguments that should be used to initialize the class       
        """
        if clz.find(".") > 0:
            logger.info("Creating runner '%s'"%clz)
            lastdot = clz.rfind(".")
            module = importlib.import_module(clz[:lastdot])
            classname = clz[lastdot+1:]
            return getattr(module, classname)(backend, active, **extra_arguments)
        else:
            raise Exception("Must specify class as module.class")
    
    @classmethod
    def from_conf(self, config, backend):
        active = False
        extra_arguments = {}
        
        runner_clazz = config["class"]
        if "extra_arguments" in config:
            extra_arguments = config["extra_arguments"]

        if "active" in config:
            active = config["active"]
        
        p = self.create_runner(runner_clazz, backend, active, extra_arguments)
        
        return p
        