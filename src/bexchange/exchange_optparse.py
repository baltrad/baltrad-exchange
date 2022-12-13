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

## Provides functionality for parsing options

## @file
## @author Anders Henja, SMHI
## @date 2021-08-18
from __future__ import absolute_import

import copy
import datetime
import optparse
import os

def check_iso8601_datetime(option, opt, value):
    try:
        return datetime.datetime.strptime(value, "%Y%m%dT%H%M%SZ")
    except ValueError:
        raise optparse.OptionValueError(
            "invalid ISO8601 datetime in %s: %s" % (option, value)
        )

def check_list(option, opt, value):
    return value.split(",")

def check_path(option, opt, value):
    return os.path.abspath(value)

class Option(optparse.Option):
    TYPES = optparse.Option.TYPES + ("iso8601_datetime", "list", "path",)
    TYPE_CHECKER = copy.copy(optparse.Option.TYPE_CHECKER)
    TYPE_CHECKER["iso8601_datetime"] = check_iso8601_datetime
    TYPE_CHECKER["list"] = check_list
    TYPE_CHECKER["path"] = check_path

def create_parser(*args, **kw):
    """create an option parser with a custom option class that supports
    the following extra options types:

      * iso8601_datetime - an ISO 8601 datetime
      * list - a comma separated list of strings
      * path - an absolute paths (relative paths are converted to absolute)
    """
    kw["option_class"] = Option
    return optparse.OptionParser(*args, **kw)
