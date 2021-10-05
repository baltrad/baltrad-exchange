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

## Decorators are used for modifying, changing, or in other way alter an ODIM H5 file.

## @file
## @author Anders Henja, SMHI
## @date 2021-08-30
import importlib

class decorator(object):
    def __init__(self):
        pass
    
    def decorate(self, ino):
        raise Exception("Not implemented")

class example_filter(decorator):
    def __init__(self, arg1, arg2):
        super(example_filter, self).__init__()
        self.arg1=arg1
        self.arg2=arg2
    
    def decorate(self, inf):
        return inf
    
class decorator_manager:
    """The manager for creating decorators used within baltrad exchange. If a class extends the decorator
    class it can be created by invoking decorator_manager.create("module....class name", arguments as a list) 
    """
    def __init__(self):
        pass
    
    @classmethod
    def create(self, clz, arguments):
        """Creates an instance of clz with specified arguments
        :param clz: class name specified as <module>.<classname>
        :param arguments: a list of arguments that should be used to initialize the class       
        """
        if clz.find(".") > 0:
            lastdot = clz.rfind(".")
            module = importlib.import_module(clz[:lastdot])
            classname = clz[lastdot+1:]
            return getattr(module, classname)(*arguments)
        else:
            raise Exception("Must specify class as module.class")
