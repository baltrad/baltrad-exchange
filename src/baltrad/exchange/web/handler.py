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

## Handler that uses the backend for executing requests

## @file
## @author Anders Henja, SMHI
## @date 2021-08-18
import shutil
from tempfile import NamedTemporaryFile
import sys
from baltrad.exchange.web import auth
from baltrad.exchange.web import util as webutil

from http import client as httplibclient
import urllib.parse as urlparse

#from baltrad.bdbcommon import expr, filter
#from baltrad.bdbcommon.oh5 import Source

from .util import (
    HttpConflict,
    HttpForbidden,
    HttpNotFound,
    JsonResponse,
    NoContentResponse,
    Response,
)

# 
# from ..backend import (
#     AttributeQuery,
#     DuplicateEntry,
#     FileQuery,
#     IntegrityError,
# )

import logging
logger = logging.getLogger("baltrad.exchange.handler")

def post_file(ctx):
    """Receive a file from some party

    :param ctx: the request context
    :type ctx: :class:`~.util.RequestContext`
    :return: :class:`~.util.JsonResponse` with status
             *201 Created* and metadata in body
    :raise: :class:`~.util.HttpConflict` when file already
            stored

    See :ref:`doc-rest-op-store-file` for details
    """
    logger.debug("bdb.handler.post_file(ctx)")
    #logger.info("post_file credentials: %s"%str(auth.get_credentials(ctx.request)))
    with NamedTemporaryFile() as tmp:
        shutil.copyfileobj(ctx.request.stream, tmp)
        tmp.flush()
        metadata = ctx.backend.store_file(tmp.name, auth.get_credentials(ctx.request))

    return Response("", status=httplibclient.OK)
    #response.headers["Location"] = ctx.make_url("file/" + metadata.bdb_uuid)
    #return NoContentResponse()
