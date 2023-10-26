# # Copyright (C) 2021- Swedish Meteorological and Hydrological Institute (SMHI)
# #
# # This file is part of baltrad-exchange.
# #
# # baltrad-exchange is free software: you can redistribute it and/or modify
# # it under the terms of the GNU Lesser General Public License as published by
# # the Free Software Foundation, either version 3 of the License, or
# # (at your option) any later version.
# #
# # baltrad-exchange is distributed in the hope that it will be useful,
# # but WITHOUT ANY WARRANTY; without even the implied warranty of
# # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# # See the GNU Lesser General Public License for more details.
# #
# # You should have received a copy of the GNU Lesser General Public License
# # along with baltrad-exchange.  If not, see <http://www.gnu.org/licenses/>.
# ###############################################################################

# ## Tests bexchange.net.zmq

# ## @file
# ## @author Anders Henja, SMHI
# ## @date 2023-10-23
# from __future__ import absolute_import

# import unittest
# from unittest.mock import MagicMock
# import datetime, hmac, hashlib, logging

# from bexchange.matching import metadata_matcher, filters
# from bexchange.net.zmq import publisher, subscriber

# from baltrad.bdbcommon import oh5, expr
# from baltrad.bdbcommon.oh5.meta import Metadata
# from baltrad.bdbcommon.oh5.node import Attribute, Group

# class test_publisher(unittest.TestCase):
#     def setUp(self):
#         self._backend = MagicMock()
#         self._name = "testname"
#         self._active = True
#         self._origin = []
#         self._ifilter = filters.filter_manager().from_value({"filter_type":"always_filter", "value":{}})
#         self._connections = []
#         self._decorators = []
#         extra_arguments = {
#             "publisher_address":"tcp://*:8078",
#             "hmac":"1234"
#         }
#         #(self, backend, name, active, origin, ifilter, connections, decorators, extra_arguments):
#         self._publisher = publisher.publisher(self._backend, self._name, self._active, self._origin, self._ifilter, self._connections, self._decorators, extra_arguments)
    
#     def tearDown(self):
#         self._backend = None
#         self._ifilter = None
#         self._publisher = None

#     def test_constructor(self):
#         self.assertEqual(b"1234", self._publisher._hmackey)
#         self.assertEqual("tcp://*:8078", self._publisher._address)
#         self.assertEqual("zmqpublisher", self._publisher._name)
#         self.assertEqual("${_baltrad/source_name}_${/what/object}.tolower()_${/what/date}T${/what/time}.h5", self._publisher._namers["default"].template())
#         self.assertEqual("${_baltrad/source_name}_scan_${/dataset1/where/elangle}_${/what/date}T${/what/time}.h5", self._publisher._namers["SCAN"].template())
#         self.assertEqual(None, self._publisher._context)
#         self.assertEqual(None, self._publisher._socket)

#     def test_initialize(self):
#         self._publisher.setup_connection = MagicMock()

#         self._publisher.initialize()

#         self._publisher.setup_connection.assert_called()

#     def test_get_attribute_value(self):
#         from baltrad.bdbcommon.oh5.meta import Metadata
#         node = MagicMock()
#         node.value = 123

#         meta = MagicMock()
#         meta.node = MagicMock(return_value=node)

#         result = self._publisher.get_attribute_value("/what/attribute", meta)
#         meta.node.assert_called_with("/what/attribute")

#         self.assertEqual(123, result)

#     def test_get_attribute_value_not_found(self):
#         from baltrad.bdbcommon.oh5.meta import Metadata
#         meta = MagicMock()
#         meta.node = MagicMock(side_effect=LookupError('bad'))

#         result = self._publisher.get_attribute_value("/what/attribute", meta)
#         meta.node.assert_called_with("/what/attribute")

#         self.assertEqual(None, result)

#     def test_do_publish(self):
#         tmpfile = MagicMock()

#         meta = Metadata();
#         meta.add_node("/", Group("what"))
#         meta.add_node("/what", Attribute("source", "WMO:02606"))
#         meta.add_node("/what", Attribute("date", datetime.date(2000, 1, 2)))
#         meta.add_node("/what", Attribute("time", datetime.time(12, 5)))
#         meta.add_node("/what", Attribute("object", "PVOL"))
#         meta.bdb_source_name = "searl"

#         metafilename = "searl_pvol_20000102T120500.h5".ljust(256, '\0').encode('latin1')

#         self._publisher.read_bytearray = MagicMock(return_value=bytearray(b'12345'))
#         self._publisher.get_attribute_value = MagicMock(return_value="PVOL")
#         self._publisher.create_hmac = MagicMock(return_value=b'abc123')
#         self._publisher._socket = MagicMock()
#         self._publisher._socket.send = MagicMock()

#         self._publisher.do_publish(tmpfile, meta)

#         self._publisher.create_hmac.assert_called_with(bytearray(metafilename + b'12345'))

#         self._publisher._socket.send.assert_called_with(bytearray(b'abc123'+metafilename+b'12345'))

# class test_subscriber(unittest.TestCase):
#     def setUp(self):
#         self._backend = MagicMock()
#         self._active = True
#         extra_arguments = {
#             "address":"tcp://127.0.0.1:8078",
#             "hmac":"1234",
#             "name":"asubscriber"

#         }
#         self._subscriber = subscriber.subscriber(self._backend, self._active, **extra_arguments)
    
#         logging.getLogger("bexchange.runner.zmq.subscriber").disabled = True

#     def tearDown(self):
#         self._backend = None
#         self._subscriber = None
        
#         logging.getLogger("bexchange.runner.zmq.subscriber").disabled = False

#     def test_constructor(self):
#         self.assertEqual(b"1234", self._subscriber._hmackey)
#         self.assertEqual("tcp://127.0.0.1:8078", self._subscriber._address)
#         self.assertEqual("asubscriber", self._subscriber._name)

#     def test_handle_file(self):
#         filename = MagicMock()

#         self._subscriber.handle_file(filename)

#         self._subscriber._backend.store_file.assert_called_with(filename, self._subscriber._name)

#     def test_calculate_hmac(self):

#         expected = hmac.new(b'1234', b'message', hashlib.sha1)

#         self.assertEqual(expected.digest().hex(), self._subscriber.calculate_hmac(b'message').digest().hex())

#     def test_process(self):
#         b_filename = "myfilename.h5".ljust(256, '\0').encode('latin1')
#         b_content = b'1234'
#         b_hmac = b'12345678901234567890'
#         b_payload = b_hmac + b_filename + b_content
#         hmacmock = MagicMock()
#         hmacmock.digest = MagicMock(return_value=b'12345678901234567890')
#         tempfilemock = MagicMock()
#         tempfilemock.__enter__().name = "tmpfilename"

#         self._subscriber.calculate_hmac = MagicMock(return_value=hmacmock)
#         self._subscriber.handle_file = MagicMock()
#         self._subscriber.create_named_temporary_file = MagicMock(return_value=tempfilemock)

#         self._subscriber.process(b_payload)

#         tempfilemock.__enter__().write.assert_called_with(b_content)
#         tempfilemock.__enter__().flush.assert_called()
#         self._subscriber.handle_file.assert_called_with('tmpfilename')

#     def test_process_failed_handle(self):
#         b_filename = "myfilename.h5".ljust(256, '\0').encode('latin1')
#         b_content = b'1234'
#         b_hmac = b'12345678901234567890'
#         b_payload = b_hmac + b_filename + b_content
#         hmacmock = MagicMock()
#         hmacmock.digest = MagicMock(return_value=b'12345678901234567890')
#         tempfilemock = MagicMock()
#         tempfilemock.__enter__().name = "tmpfilename"

#         self._subscriber.calculate_hmac = MagicMock(return_value=hmacmock)
#         self._subscriber.handle_file = MagicMock(side_effect=Exception("No luck"))
#         self._subscriber.create_named_temporary_file = MagicMock(return_value=tempfilemock)

#         self._subscriber.process(b_payload)

#         tempfilemock.__enter__().write.assert_called_with(b_content)
#         tempfilemock.__enter__().flush.assert_called()
#         self._subscriber.handle_file.assert_called_with('tmpfilename')

#     def test_process_to_little_data(self):
#         b_filename = "myfilename.h5".ljust(100, '\0').encode('latin1')
#         b_content = b'1234'
#         b_hmac = b'12345678901234567890'
#         b_payload = b_hmac + b_filename + b_content

#         self._subscriber.calculate_hmac = MagicMock(side_effect=Exception("Should not come here"))

#         self._subscriber.process(b_payload)
