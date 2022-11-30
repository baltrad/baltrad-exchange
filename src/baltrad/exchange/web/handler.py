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
             *200 OK*

    See :ref:`doc-rest-op-post-file` for details
    """
    logger.debug("baltrad.exchange.handler.post_file(ctx)")
    if ctx.is_anonymous(): # We don't want unauthorized messages in here unless it has been explicitly allowed
        logger.info("post_file: anonymous calls are not allowed")
        return Response("", status=httplibclient.UNAUTHORIZED)

    with NamedTemporaryFile() as tmp:
        shutil.copyfileobj(ctx.request.stream, tmp)
        tmp.flush()
        metadata = ctx.backend.store_file(tmp.name, ctx.backend.get_auth_manager().get_nodename(ctx.request))

    return Response("", status=httplibclient.OK)

def post_dex_file(ctx):
    logger.debug("baltrad.exchange.handler.post_dex_file(ctx)")
    if ctx.is_anonymous(): # We don't want unauthorized messages in here unless it has been explicitly allowed
        logger.info("post_dex_file: anonymous calls are not allowed")
        return Response("", status=httplibclient.UNAUTHORIZED)

    with NamedTemporaryFile() as tmp:
        shutil.copyfileobj(ctx.request.stream, tmp)
        tmp.flush()
        metadata = ctx.backend.store_file(tmp.name, ctx.backend.get_auth_manager().get_nodename(ctx.request))

    return Response("", status=httplibclient.OK)

def post_json_message(ctx):
    """A trigger message used to trigger different jobs from the outside

    :param ctx: the request context
    :type ctx: :class:`~.util.RequestContext`
    :return: :class:`~.util.JsonResponse` with status
             *201 Created* and metadata in body
    :raise: :class:`~.util.HttpConflict` when file already
            stored

    See :ref:`doc-rest-op-store-file` for details
    """
    logger.debug("baltrad.exchange.handler.post_json_message(ctx)")
    if ctx.is_anonymous():
        logger.info("post_json_message: anonymous calls are not allowed")
        return Response("", status=httplibclient.UNAUTHORIZED)
    data = ctx.request.get_json_data()
    ctx.backend.post_message(data, ctx.backend.get_auth_manager().get_nodename(ctx.request))
    return Response("", status=httplibclient.OK)

def get_statistics(ctx):
    """Returns the statistics for modules / sources

    :param ctx: the request context
    :type ctx: :class:`~.util.RequestContext`
    :return: :class:`~.util.JsonResponse` with status
             *200 Created* and information in body

    See :ref:`doc-rest-op-get_statistics` for details
    """
    logger.debug("baltrad.exchange.handler.get_statistics(ctx)")
    if ctx.is_anonymous():
        logger.info("get_statistics: anonymous calls are not allowed")
        return Response("", status=httplibclient.UNAUTHORIZED)
    data = ctx.request.get_json_data()
    stats = ctx.backend.get_statistics_manager().get_statistics(ctx.backend.get_auth_manager().get_nodename(ctx.request), data)
    return Response(stats, status=httplibclient.OK)
