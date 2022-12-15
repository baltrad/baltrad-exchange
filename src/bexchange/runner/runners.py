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
from threading import Thread, Event

from bexchange.naming import namer
from bexchange.util import message_aware
from bexchange.net.fetchers import fetcher_manager

logger = logging.getLogger("bexchange.runner.runners")

class runner(object):
    """Base class for any runner
    """
    def __init__(self, backend, active):
        """Constructor
        :param backend: The backend
        :param active: If this runner should be active or not
        """
        super(runner,self).__init__()
        self._backend = backend
        self._active = active

    def backend(self):
        """
        :return the backend
        """
        return self._backend

    def active(self):
        """
        :return if this runner is active or not
        """
        return self._active
    
    def setactive(self, active):
        """
        :param active: If this runner should be active or not
        """
        self._active = active

    def start(self):
        """Abstract start method. Will start the runner. Typically by setting up some event listening or starting a thread.
        """
        raise Exception("Not implemented")

class inotify_runner_event_handler(pyinotify.ProcessEvent):
    def __init__(self, inotify_runner):
        """Constructor
        :param inotify_runner: The inotify runner that will be called
        """
        self._runner = inotify_runner
    
    def process_IN_CLOSE_WRITE(self, event):
        """Will be called by the inotify notifier when file event occurs.
        :param event: The file event
        """
        logger.debug("IN_CLOSE_WRITE: %s"%event.pathname)
        if not self._runner.is_ignored(event.pathname):  # avoid temporary file
            self._runner.handle_file(event.pathname)

    def process_IN_MOVED_TO(self, event):
        """Will be called by the inotify notifier when file event occurs.
        :param event: The file event
        """
        logger.debug("IN_MOVED_WRITE: %s"%event.pathname)
        if not self._runner.is_ignored(event.pathname):  # avoid temporary file
            self._runner.handle_file(event.pathname)

class inotify_runner(runner):
    """The inotify runner is used to monitor folders and trigger "store" events. It is run in a separate thread instead of 
    beeing created as a daemon-thread since all initiation is performed in the main thread before server is started.
    """
    MASK = pyinotify.IN_CLOSE_WRITE | pyinotify.IN_MOVED_TO
    
    def __init__(self, backend, active, **args):
        """Constructor
        :param backend: The backend
        :param active: If this runner is active or not. NOT USED
        :param **args: A number of arguments can be provided
          folders        - a list of folder names to monitor
          ignore-pattern - If files matching the provided pattern should be ignored or not
          pattern        - The pattern to check for files to ignore
          name           - The name this inotify runner should be using
        """
        super(inotify_runner, self).__init__(backend, active)
        self._name = "inotify-runner"
        self._folders = args["folders"]
        self._ignore_pattern = True
        self._pattern = ""
        if "ignore-pattern" in args:
            self._ignore_pattern = args["ignore-pattern"]
        if "pattern" in args:
            self._pattern = args["pattern"]
        if "name" in args:
            self._name = args["name"]
        self._wm = pyinotify.WatchManager()
        self._notifier = pyinotify.Notifier(self._wm, inotify_runner_event_handler(self))

    def is_ignored(self, filename):
        """Checks if the specified file should be ignored or not, for example when a tmpfile is written.
        the check is performed on basename.
        :param filename: The filename to be checked
        :return True if file should be ignored otherwise False
        """
        if self._ignore_pattern:
            return False
        bname = os.path.basename(filename)
        return re.match(self._pattern, bname) != None
    
    def handle_file(self, filename):
        """Handles the file (by sending it to the backend using the name given to this runner
        :param filename: The filename to handle
        """
        self._backend.store_file(filename, self._name)

    def run(self):
        """The runner for the thread. Starts the inotify notifier loop
        """
        self._notifier.loop()

    def start(self):
        """Starts this runner by adding the watched folders and then starting a daemonized thread.
        """
        for folder in self._folders:
            logger.info("inotify_runner(%s) watching '%s'"%(self._name, folder))
            self._wm.add_watch(folder, self.MASK)

        self._thread = Thread(target=self.run)
        self._thread.daemon = True
        self._thread.start()

class triggered_fetch_runner(runner, message_aware):
    """A triggered runner. This runner implements 'message_aware' so that a json-message
    can be handled. This runner is actually triggered from the WSGI-process and as such
    is using the WSGI-servers thread pool. @todo: Implement this as a producer/consumer
    thread to avoid any possibility to starve the WSGI-thread pool. 
    """
    def __init__(self, backend, active, **args):
        """Constructor
        :param backend: The backend
        :param active: If this runner is active or not. NOT USED
        :param **args: A number of arguments can be provided
        """
        super(triggered_fetch_runner, self).__init__(backend, active)
        if not "fetcher" in args:
            raise Exception("Expected an fetcher in config")
        if "invoker_names" not in args or len(args["invoker_names"]) == 0:
            raise Exception("Expected invoker_names in config")
        if "trigger_names" not in args:
            raise Exception("Expected trigger_names in config")
        self._fetcher = fetcher_manager.from_conf(backend, args["fetcher"])
        self._invoker_names = args["invoker_names"]
        self._trigger_names = args["trigger_names"]
 
    def start(self):
        """Not used
        """
        pass
    
    def handle_message(self, json_message, nodename):
        """Handles the message if the json message contains a trigger that matches trigger names and
        that the nodename is allowed within the invoker_names by invoking the fetch method in fetcher
        using "arguments" in the json-message.
        """
        if nodename in self._invoker_names and \
           (len(self._trigger_names)==0 or json_message["trigger"] in self._trigger_names):
            kwargs = {}
            if "arguments" in json_message:
                if isinstance(json_message["arguments"], dict):
                    kwargs = json_message["arguments"]
            self._fetcher.fetch(**kwargs)

class statistics_cleanup_runner(runner):
    """Cleans the statistics database
    """
    def __init__(self, backend, active, **args):
        super(statistics_cleanup_runner, self).__init__(backend, active)
        self._name = "statistics_cleanup_runner"
        self._interval = 60 # minutes
        self._age = 48      # hours
        self._manager = self.backend().get_statistics_manager()
        self._event = Event()
        self._running = False

        if "name" in args:
            self._name = args["name"]
        
        if "interval" in args:
            self._interval = args["interval"]
            if not isinstance(self._interval, int):
                raise AttributeError("interval should be an integer")

        if "age" in args:
            self._age = args["age"]
            if not isinstance(self._age, int):
                raise AttributeError("age should be an integer")

    def run(self):
        """The runner for the thread. Will trigger a wait for
        """
        while self._running:
            self._manager.cleanup_statentry(self._age)
            self._event.wait(self._interval * 60)

    def start(self):
        """Starts this runner by starting a daemonized thread.
        """
        self._running = True
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
        """Starts all runners
        """
        for r in self._runners:
            r.start()

    def get_runners(self):
        """
        :return the runners
        """
        return self._runners

    @classmethod
    def create_runner(self, clz, backend, active, extra_arguments):
        """Creates an instance of clz with specified arguments
        :param clz: class name specified as <module>.<classname>
        :param arguments: a list of arguments that should be used to initialize the class       
        """
        if clz.find(".") > 0:
            logger.debug("Creating runner '%s'"%clz)
            lastdot = clz.rfind(".")
            module = importlib.import_module(clz[:lastdot])
            classname = clz[lastdot+1:]
            return getattr(module, classname)(backend, active, **extra_arguments)
        else:
            raise Exception("Must specify class as module.class")
    
    @classmethod
    def from_conf(self, config, backend):
        """Creates a runner from the specified configuration if it is possible
        :param config: A runner config pattern. Should at least contain the following
        {"class":"<packagename>.<classname>"
        "active":<true or false>
        "extra_arguments":{}"
        }
        """
        active = False
        extra_arguments = {}
        
        runner_clazz = config["class"]
        if "extra_arguments" in config:
            extra_arguments = config["extra_arguments"]

        if "active" in config:
            active = config["active"]
        
        p = self.create_runner(runner_clazz, backend, active, extra_arguments)
        
        return p
        