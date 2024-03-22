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
from bexchange.web import auth
from bexchange.web import util as webutil
import datetime
from http import client as httplibclient
import urllib.parse as urlparse

from bexchange.net.exceptions import DuplicateException

from .util import (
    HttpConflict,
    HttpForbidden,
    HttpNotFound,
    JsonResponse,
    NoContentResponse,
    Response,
    TemporaryRedirectResponse
)
import json

import logging
logger = logging.getLogger("bexchange.handler")

def post_file(ctx):
    """Receive a file from some party

    :param ctx: the request context
    :type ctx: :class:`~.util.RequestContext`
    :return: :class:`~.util.JsonResponse` with status
             *200 OK*

    See :ref:`doc-rest-cmd-store-file` for details
    """
    logger.debug("bexchange.handler.post_file(ctx)")
    if ctx.is_anonymous(): # We don't want unauthorized messages in here unless it has been explicitly allowed
        logger.info("post_file: anonymous calls are not allowed")
        return Response("", status=httplibclient.UNAUTHORIZED)

    with NamedTemporaryFile(dir=ctx.backend.get_tmp_folder()) as tmp:
        shutil.copyfileobj(ctx.request.stream, tmp)
        tmp.flush()
        try:
            metadata = ctx.backend.store_file(tmp.name, ctx.backend.get_auth_manager().get_nodename(ctx.request))
        except LookupError as e:
            raise HttpNotAccepatble(str(e))
        except DuplicateException as e:
            raise HttpConflict("duplicate file entry: %s"%str(e))

    return Response("", status=httplibclient.OK)

def post_dex_file(ctx):
    logger.debug("bexchange.handler.post_dex_file(ctx)")
    if ctx.is_anonymous(): # We don't want unauthorized messages in here unless it has been explicitly allowed
        logger.info("post_dex_file: anonymous calls are not allowed")
        return Response("", status=httplibclient.UNAUTHORIZED)

    with NamedTemporaryFile() as tmp:
        shutil.copyfileobj(ctx.request.stream, tmp)
        tmp.flush()
        try:
            metadata = ctx.backend.store_file(tmp.name, ctx.backend.get_auth_manager().get_nodename(ctx.request))
        except LookupError as e:
            raise HttpNotAccepatble(str(e))
        except DuplicateException as e:
            raise HttpConflict("duplicate file entry: %s"%str(e))

    return Response("", status=httplibclient.OK)

def post_json_message(ctx):
    """A trigger message used to trigger different jobs from the outside

    :param ctx: the request context
    :type ctx: :class:`~.util.RequestContext`
    :return: :class:`~.util.JsonResponse` with status
             *201 Created* and metadata in body
    :raise: :class:`~.util.HttpConflict` when file already
            stored

    See :ref:`doc-rest-cmd-post-json-message` for details
    """
    logger.debug("bexchange.handler.post_json_message(ctx)")
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

    See :ref:`doc-rest-cmd-get_statistics` for details
    """
    logger.debug("bexchange.handler.get_statistics(ctx)")
    if ctx.is_anonymous():
        logger.info("get_statistics: anonymous calls are not allowed")
        return Response("", status=httplibclient.UNAUTHORIZED)
    data = ctx.request.get_json_data()
    stats = ctx.backend.get_statistics_manager().get_statistics(ctx.backend.get_auth_manager().get_nodename(ctx.request), data)
    return Response(stats, status=httplibclient.OK)

def list_statistic_ids(ctx):
    """Returns the statistic ids

    :param ctx: the request context
    :type ctx: :class:`~.util.RequestContext`
    :return: :class:`~.util.JsonResponse` with status
             *200 Created* and information in body

    See :ref:`doc-rest-cmd-list_statistic_ids` for details
    """
    logger.debug("bexchange.handler.list_statistic_ids(ctx)")
    if ctx.is_anonymous():
        logger.info("list_statistic_ids: anonymous calls are not allowed")
        return Response("", status=httplibclient.UNAUTHORIZED)
    stats = ctx.backend.get_statistics_manager().list_statistic_ids(ctx.backend.get_auth_manager().get_nodename(ctx.request))
    return Response(stats, status=httplibclient.OK)


def get_server_uptime(ctx):
    """
    :returns the server uptime

    See :ref:`doc-rest-cmd-server_info` for details
    """
    logger.debug("bexchange.handler.get_server_uptime(ctx)")
    if ctx.is_anonymous():
        logger.info("get_server_uptime: anonymous calls are not allowed")
        return Response("", status=httplibclient.UNAUTHORIZED)
    days, hours, minutes, seconds = ctx.backend.get_server_uptime()
    return Response(json.dumps({"days":days, "hours":hours, "minutes":minutes, "seconds":seconds}), status=httplibclient.OK)

def get_server_nodename(ctx):
    """
    :returns the server nodename

    See :ref:`doc-rest-cmd-server_info` for details
    """
    logger.debug("bexchange.handler.get_server_nodename(ctx)")
    if ctx.is_anonymous():
        logger.info("get_server_nodename: anonymous calls are not allowed")
        return Response("", status=httplibclient.UNAUTHORIZED)
    nodename = ctx.backend.get_server_nodename()
    return Response(json.dumps({"nodename":nodename}), status=httplibclient.OK)

def get_server_publickey(ctx):
    """
    :returns the server publickey

    See :ref:`doc-rest-cmd-server_info` for details
    """
    logger.debug("bexchange.handler.get_server_publickey(ctx)")
    if ctx.is_anonymous():
        logger.info("get_server_publickey: anonymous calls are not allowed")
        return Response("", status=httplibclient.UNAUTHORIZED)
    publickey = ctx.backend.get_server_publickey()
    return Response(publickey, status=httplibclient.OK)

def file_arrival(ctx):
    """Returns if a file with specified source, object type has arrived within limit

    :param ctx: the request context
    :type ctx: :class:`~.util.RequestContext`
    :return: :class:`~.util.JsonResponse` with status
             *200 Created* and information in body

    See :ref:`doc-rest-cmd-file-arrival` for details
    """
    logger.debug("bexchange.handler.file_arrival(ctx)")
    if ctx.is_anonymous():
        logger.info("file_arrival: anonymous calls are not allowed")
        return Response("", status=httplibclient.UNAUTHORIZED)
    data = ctx.request.get_json_data()
    source = None
    object_type = None
    limit = 5
    if "source" in data:
        source = data["source"]
    if "object_type" in data:
        object_type = data["object_type"]
    if "limit" in data:
        limit = int(data["limit"])

    dtfilterdate = (datetime.datetime.utcnow() - datetime.timedelta(minutes=limit))
    dtfilter = "datetime>=%s"%((datetime.datetime.utcnow() - datetime.timedelta(minutes=limit)).strftime("%Y%m%d%H%M"))
    querydata = {"spid":"server-incomming", "sources":source, "object_type":object_type, "dtfilter":dtfilter}
    stats = ctx.backend.get_statistics_manager().get_statistics_entries(ctx.backend.get_auth_manager().get_nodename(ctx.request), querydata)
    result={"status":"ERROR"}
    if stats and len(stats) > 0:
        result={"status":"OK"}
    return Response(json.dumps(result), status=httplibclient.OK)

def supervise(ctx):
    """Provides functionality for supervising the node

    :param ctx: the request context
    :type ctx: :class:`~.util.RequestContext`
    :return: :class:`~.util.JsonResponse` with status
             *200 Created* and information in body

    See :ref:`doc-rest-cmd-file-arrival` for details
    """
    logger.debug("bexchange.handler.supervise(ctx)")
    if ctx.is_anonymous():
        logger.info("supervise: anonymous calls are not allowed")
        return Response("", status=httplibclient.UNAUTHORIZED)
    data = ctx.request.get_json_data()
    source = None
    object_type = None
    limit = 5
    entrylimit = 0
    if "source" in data:
        source = data["source"]
    if "object_type" in data:
        object_type = data["object_type"]
    if "limit" in data:
        limit = int(data["limit"])
    if "entrylimit" in data:
        entrylimit = int(data["entrylimit"])

    dtfilterdate = (datetime.datetime.utcnow() - datetime.timedelta(seconds=limit))
    dtfilter = "datetime>=%s"%((datetime.datetime.utcnow() - datetime.timedelta(seconds=limit)).strftime("%Y%m%d%H%M%S"))
    if entrylimit > 0:
        dtfilter = dtfilter + "&&entrytime>=%s"%((datetime.datetime.utcnow() - datetime.timedelta(seconds=entrylimit)).strftime("%Y%m%d%H%M%S"))
    querydata = {"spid":"server-incomming", "sources":source, "object_type":object_type, "filter":dtfilter}
    logger.info("supervise query=%s"%str(querydata))
    stats = ctx.backend.get_statistics_manager().get_statistics_entries(ctx.backend.get_auth_manager().get_nodename(ctx.request), querydata)
    result={"status":"ERROR"}
    if stats and len(stats) > 0:
        result={"status":"OK"}
    return Response(json.dumps(result), status=httplibclient.OK)