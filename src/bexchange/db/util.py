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

## Some utility functions when working with sqlalchemy & db operations

## @file
## @author Anders Henja, SMHI
## @date 2022-12-23
from __future__ import absolute_import

import logging
from sqlalchemy import engine
from sqlalchemy.pool import QueuePool

from urllib.parse import urlparse

logger = logging.getLogger("bexchange.db.util")

def create_engine_from_url(url, poolsize=10):
    """Creates a sqlalchemy engine from the specified url. If the scheme is sqlite, the poolsize will not be used.
    :param url: The uri
    :param poolsize: The number of connections in pool
    :return: the engine
    """
    result = None
    try:
        parsed = urlparse(url)
        if parsed.scheme == "sqlite":
            result = engine.create_engine(url, echo=False)
        else:
            result = engine.create_engine(url, echo=False, pool_size=poolsize)
    except:
        result = engine.create_engine(url, echo=False)

    return result