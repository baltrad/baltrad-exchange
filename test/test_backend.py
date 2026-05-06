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

## Tests bexchange.server.backend

## @file
## @author Anders Henja, SMHI
## @date 2026-05-04
from __future__ import absolute_import

import unittest
import pytest
from unittest.mock import MagicMock
from bexchange.server import backend
from bexchange.storage import storages
from bexchange.processor import processors
from baltrad.bdbcommon.oh5.meta import Metadata

import os

THIS_DIR=os.path.dirname(__file__)

class TestBackend:
    SOURCE_FIXTURE=f"{THIS_DIR}/fixtures/odim_source.xml"

    @pytest.fixture(autouse=True)
    def setup(self):
        self.classUnderTest = backend.SimpleBackend([], "mynode", None, "sqlite:///:memory:", "sqlite:///:memory:", self.SOURCE_FIXTURE, tmpfolder=None)
        
        yield

        self.classUnderTest = None
    
    def test_store_file(self):
        meta = Metadata()
        self.classUnderTest.metadata_from_file = MagicMock(return_value=meta)
        self.classUnderTest.create_fileid_from_meta = MagicMock(return_value="file_identifier")
        self.classUnderTest.publish = MagicMock(return_value="file_identifier")        
        self.classUnderTest.storage_manager = storages.storage_manager()
        self.classUnderTest.processor_manager = MagicMock()

        mock_storage = MagicMock()
        mock_storage.name.return_value = "nisse"
        self.classUnderTest.storage_manager.add_storage(mock_storage)

        mock_subscription = MagicMock()
        mock_subscription.filter_matching.return_value = True
        mock_subscription.storages.return_value = ["nisse"]
        mock_subscription.id.return_value = "id-1"

        self.classUnderTest.subscriptions = [mock_subscription]

        # Execute test
        self.classUnderTest.store_file("abc", "anid")

        self.classUnderTest.metadata_from_file.assert_called_once_with("abc")
        mock_storage.store.assert_called_once_with("abc", meta)
        self.classUnderTest.publish.assert_called_once_with("id-1", "abc", meta)
        self.classUnderTest.processor_manager.process.assert_called_once_with("abc", meta)

    def test_store_file_failed_storage(self):
        meta = Metadata()
        self.classUnderTest.metadata_from_file = MagicMock(return_value=meta)
        self.classUnderTest.create_fileid_from_meta = MagicMock(return_value="file_identifier")
        self.classUnderTest.publish = MagicMock(return_value="file_identifier")        
        self.classUnderTest.storage_manager = storages.storage_manager()
        self.classUnderTest.processor_manager = MagicMock()

        mock_storage = MagicMock()
        mock_storage.name.return_value = "nisse"
        mock_storage.store.side_effect = Exception()
        self.classUnderTest.storage_manager.add_storage(mock_storage)

        mock_subscription = MagicMock()
        mock_subscription.filter_matching.return_value = True
        mock_subscription.storages.return_value = ["nisse"]
        mock_subscription.id.return_value = "id-1"

        self.classUnderTest.subscriptions = [mock_subscription]

        # Execute test
        self.classUnderTest.store_file("abc", "anid")

        self.classUnderTest.metadata_from_file.assert_called_once_with("abc")
        mock_storage.store.assert_called_once_with("abc", meta)
        self.classUnderTest.publish.assert_called_once_with("id-1", "abc", meta)
        self.classUnderTest.processor_manager.process.assert_called_once_with("abc", meta)

    def test_store_file_failed_storage_with_two_storages(self):
        meta = Metadata()
        self.classUnderTest.metadata_from_file = MagicMock(return_value=meta)
        self.classUnderTest.create_fileid_from_meta = MagicMock(return_value="file_identifier")
        self.classUnderTest.publish = MagicMock(return_value="file_identifier")        
        self.classUnderTest.storage_manager = storages.storage_manager()
        self.classUnderTest.processor_manager = MagicMock()

        mock_storage = MagicMock()
        mock_storage.name.return_value = "nisse"
        mock_storage.store.side_effect = Exception()
        self.classUnderTest.storage_manager.add_storage(mock_storage)

        mock_storage_2 = MagicMock()
        mock_storage_2.name.return_value = "pelle"
        self.classUnderTest.storage_manager.add_storage(mock_storage_2)

        mock_subscription = MagicMock()
        mock_subscription.filter_matching.return_value = True
        mock_subscription.storages.return_value = ["nisse", "pelle"]
        mock_subscription.id.return_value = "id-1"

        self.classUnderTest.subscriptions = [mock_subscription]

        # Execute test
        self.classUnderTest.store_file("abc", "anid")

        self.classUnderTest.metadata_from_file.assert_called_once_with("abc")
        mock_storage.store.assert_called_with("abc", meta)
        mock_storage_2.store.assert_called_with("abc", meta)
        self.classUnderTest.publish.assert_called_once_with("id-1", "abc", meta)
        self.classUnderTest.processor_manager.process.assert_called_once_with("abc", meta)

    def test_store_file_failed_publish(self):
        meta = Metadata()
        self.classUnderTest.metadata_from_file = MagicMock(return_value=meta)
        self.classUnderTest.create_fileid_from_meta = MagicMock(return_value="file_identifier")
        self.classUnderTest.publish = MagicMock(side_effect=Exception())        
        self.classUnderTest.storage_manager = storages.storage_manager()
        self.classUnderTest.processor_manager = MagicMock()

        mock_storage = MagicMock()
        mock_storage.name.return_value = "nisse"
        mock_storage.store.side_effect = Exception()
        self.classUnderTest.storage_manager.add_storage(mock_storage)

        mock_subscription = MagicMock()
        mock_subscription.filter_matching.return_value = True
        mock_subscription.storages.return_value = ["nisse"]
        mock_subscription.id.return_value = "id-1"

        self.classUnderTest.subscriptions = [mock_subscription]

        # Execute test
        self.classUnderTest.store_file("abc", "anid")

        self.classUnderTest.metadata_from_file.assert_called_once_with("abc")
        mock_storage.store.assert_called_with("abc", meta)
        self.classUnderTest.publish.assert_called_once_with("id-1", "abc", meta)
        self.classUnderTest.processor_manager.process.assert_called_once_with("abc", meta)

    def test_publish(self):
        meta = Metadata()
        matcher_mock = MagicMock()
        self.classUnderTest.create_matcher = MagicMock(return_value=matcher_mock)

        mock_publication_1 = MagicMock()
        mock_publication_1.origin.return_value = []
        mock_publication_1.active.return_value = True
        mock_publication_2 = MagicMock()
        mock_publication_2.origin.return_value = []
        mock_publication_2.active.return_value = True
        self.classUnderTest.publications = [mock_publication_1, mock_publication_2]
        matcher_mock.match.return_value = True

        # Execute test
        self.classUnderTest.publish("sid", "abc", meta)

        # Verify
        mock_publication_1.publish.assert_called_once_with("abc", meta)
        mock_publication_2.publish.assert_called_once_with("abc", meta)

    def test_publish_one_failure(self):
        meta = Metadata()
        matcher_mock = MagicMock()
        self.classUnderTest.create_matcher = MagicMock(return_value=matcher_mock)

        mock_publication_1 = MagicMock()
        mock_publication_1.origin.return_value = []
        mock_publication_1.active.return_value = True
        mock_publication_1.name.return_value = "publisher-1"
        mock_publication_1.publish.side_effect = Exception()
        mock_publication_2 = MagicMock()
        mock_publication_2.origin.return_value = []
        mock_publication_2.active.return_value = True
        mock_publication_2.name.return_value = "publisher-2"
        self.classUnderTest.publications = [mock_publication_1, mock_publication_2]
        matcher_mock.match.return_value = True

        # Execute test
        self.classUnderTest.publish("sid", "abc", meta)

        # Verify
        mock_publication_1.publish.assert_called_once_with("abc", meta)
        mock_publication_2.publish.assert_called_once_with("abc", meta)

    def test_publish_two_failures(self):
        meta = Metadata()
        matcher_mock = MagicMock()
        self.classUnderTest.create_matcher = MagicMock(return_value=matcher_mock)

        mock_publication_1 = MagicMock()
        mock_publication_1.origin.return_value = []
        mock_publication_1.active.return_value = True
        mock_publication_1.name.return_value = "publisher-1"
        mock_publication_1.publish.side_effect = Exception()
        mock_publication_2 = MagicMock()
        mock_publication_2.origin.return_value = []
        mock_publication_2.active.return_value = True
        mock_publication_2.name.return_value = "publisher-2"
        mock_publication_2.publish.side_effect = Exception()
        self.classUnderTest.publications = [mock_publication_1, mock_publication_2]
        matcher_mock.match.return_value = True

        # Execute test
        self.classUnderTest.publish("sid", "abc", meta)

        # Verify
        mock_publication_1.publish.assert_called_once_with("abc", meta)
        mock_publication_2.publish.assert_called_once_with("abc", meta)
