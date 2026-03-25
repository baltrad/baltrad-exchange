# Copyright (C) 2026- Swedish Meteorological and Hydrological Institute (SMHI)
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

## A wrapper around inotify to be able to use both watchdog and pyinotify depending
# on what is available on the system. The FileWatcherEventHandler is similar to FileSystemEventHandler
# with the exception that there is no on_moved.
# First atempt to import watchdog, if that fails try pyinotify. If both fail, raise an error.

## @file
## @author Anders Henja, SMHI
## @date 2026-03-25
import logging

logger = logging.getLogger("bexchange.file_watcher")

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    BACKEND = "watchdog"
except ImportError:
    try:
        import pyinotify
        BACKEND = "pyinotify"
    except ImportError:
        raise RuntimeError("No filesystem watching backend available. Install either 'watchdog' or 'pyinotify'.")


class FileWatcherEventHandler:
    def on_closed(self, event):
        pass

    def on_created(self, event):
        pass

    def on_deleted(self, event):
        pass

    def on_modified(self, event):
        pass
    
if BACKEND == "watchdog":
    try:
        logging.getLogger("watchdog.observers.inotify_buffer").setLevel(logging.INFO)
    except:
        pass

    class FileSystemEventHandlerWrapper(FileSystemEventHandler):
        def __init__(self, handler):
            if not isinstance(handler, FileWatcherEventHandler):
                raise Exception("Must provide a FileWatcherEventHandler")
            self._handler = handler

        def on_closed(self, event):
            try:
                self._handler.on_closed(event)
            except:
                logger.exception("Exception in on_closed")

        def on_created(self, event):
            try:
                self._handler.on_created(event)
            except:
                logger.exception("Exception in on_created")
        
        def on_deleted(self, event):
            try:
                self._handler.on_deleted(event)
            except:
                logger.exception("Exception in on_deleted")

        def on_modified(self, event):
            try:
                self._handler.on_modified(event)
            except:
                logger.exception("Exception in on_modified")

else:
    class _PyinotifyEvent:
        """Normalize pyinotify event to look like a watchdog event."""
        def __init__(self, event):
            self.src_path = event.pathname
            self.is_directory = event.dir
    
    class FileSystemEventHandlerWrapper(pyinotify.ProcessEvent):
        def __init__(self, handler):
            if not isinstance(handler, FileWatcherEventHandler):
                raise Exception("Must provide a FileWatcherEventHandler")
            self._handler = handler

        def process_IN_CLOSE_WRITE(self, event):
            try:
                self._handler.on_closed(_PyinotifyEvent(event))
            except:
                logger.exception("Exception in process_IN_CLOSE_WRITE")

        def process_IN_CREATE(self, event):
            try:
                self._handler.on_created(_PyinotifyEvent(event))
            except:
                logger.exception("Exception in process_IN_CREATE")

        def process_IN_DELETE(self, event):
            try:
                self._handler.on_deleted(_PyinotifyEvent(event))
            except:
                logger.exception("Exception in process_IN_DELETE")

        def process_IN_MODIFY(self, event):
            try:
                self._handler.on_modified(_PyinotifyEvent(event))
            except:
                logger.exception("Exception in process_IN_MODIFY")
            
        def process_IN_MOVED_TO(self, event):
            try:
                self._handler.on_created(_PyinotifyEvent(event))
            except:
                logger.exception("Exception in process_IN_MOVED_TO")

        def process_IN_MOVED_FROM(self, event):
            try:
                self._handler.on_deleted(_PyinotifyEvent(event))
            except:
                logger.exception("Exception in process_IN_MOVED_FROM")

class FileWatcher:
    def __init__(self, paths, handler, recursive=False):
        self.paths = paths
        self.handler = FileSystemEventHandlerWrapper(handler)
        self.recursive = recursive

    def start(self, daemonize=True):
        if BACKEND == "watchdog":
            self._observer = Observer()
            self._observer.daemon = daemonize
            for path in self.paths:
                logger.info(f"Watching path: {path} (recursive={self.recursive})")
                self._observer.schedule(self.handler, path, 
                                        recursive=self.recursive)
            self._observer.start()
        else:
            self._wm = pyinotify.WatchManager()
            mask = (pyinotify.IN_CLOSE_WRITE | 
                    pyinotify.IN_CREATE |
                    pyinotify.IN_DELETE |
                    pyinotify.IN_MODIFY | 
                    pyinotify.IN_MOVED_TO |
                    pyinotify.IN_MOVED_FROM)
            self._notifier = pyinotify.ThreadedNotifier(self._wm, self.handler)
            self._notifier.daemon = daemonize
            for path in self.paths:
                logger.info(f"Watching path: {path} (recursive={self.recursive})")
                self._wm.add_watch(path, mask, 
                                   rec=self.recursive, auto_add=self.recursive)
            self._notifier.start()

    def stop(self):
        if BACKEND == "watchdog":
            self._observer.stop()
            self._observer.join()
        else:
            self._notifier.stop()