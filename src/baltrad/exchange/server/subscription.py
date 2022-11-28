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

## The subscription class

## @file
## @author Anders Henja, SMHI
## @date 2022-10-25
from baltrad.exchange.matching import filters
from baltrad.exchange.matching.filters import filter_manager
from baltrad.exchange.matching import filters, metadata_matcher
import logging

logger = logging.getLogger("baltrad.exchange.server.subscription")

class subscription(object):
    def __init__(self, storages, subscription_id=None, active=True, ifilter=None, allow_duplicates=False, allowed_ids=[]):
        """Constructor
        :param storages: List of storage names
        :param subscription_id: Id this subscription should be identified if tunneling
        :param active: If this subscription is active or not
        :param ifilter: A filter instance
        :param allow_duplicates: If duplicates should be allowed or not
        :param allowed_ids: A list of nodenames that should be allowed. 
        """
        self._subscription_id = subscription_id
        self._storages = storages
        self._active = active
        self._filter = ifilter
        self._allow_duplicates = allow_duplicates
        self._allowed_ids = allowed_ids
    
    def storages(self):
        """
        :return the storage names
        """
        return self._storages
    
    def id(self):
        """
        :return the subscription id (or None if there is none)
        """
        return self._subscription_id
    
    def isactive(self):
        """
        :return if this subscription is active or not
        """
        return self._active
    
    def setactive(self, active):
        """ Sets this subscription active or not
        :param active: If subscription should be set to active or not
        """
        self._active = active
    
    def filter(self):
        """
        :return the filter
        """
        return self._filter
    
    def allow_duplicates(self):
        """
        :return if duplicates are handled by this subscription or not
        """
        return self._allow_duplicates
    
    def allowed_ids(self):
        """
        :return the nodenames
        """
        return self._allowed_ids

    def filter_matching(self, meta):
        """Matches the meta against the filter.
        :param meta: The metadata
        :return True if filter is None or if metadata matches the filter.
        """
        if self._filter:
            matcher = metadata_matcher.metadata_matcher()
            return matcher.match(meta, self._filter.to_xpr())
        return True
       

class subscription_manager:
    def __init__(self):
        pass

    @classmethod
    def create_subscription(self, storages, subscription_id, active, ifilter, allow_duplicates, allowed_ids):
        """Creates a subscription instance
        :param storages: List of storage names
        :param subscription_id: Subscription id
        :param active: If subscription should be set to active or not
        :param ifilter: A filter instances
        :param allow_duplicate: If duplicates should be allowed or not
        :param allowed_ids: A list of ids that should be allowed for this subscription
        """
        return subscription(storages, subscription_id, active, ifilter, allow_duplicates, allowed_ids)
    
    @classmethod
    def from_conf(self, config, backend):
        filter_manager = filters.filter_manager()
        storages=[]
        subscription_id=None
        active=True
        ifilter = None
        allow_duplicates=False
        
        allowed_ids = []
        
        if "storage" in config:
            storages = config["storage"]
            if not isinstance(storages, list):
                storages = [storages]
        
        if "id" in config:
            subscription_id  = config["id"]
        
        if "active" in config:
            active = config["active"]
        
        if "filter" in config:
            ifilter = filter_manager.from_value(config["filter"])
        
        if "allow_duplicates" in config:
            allow_duplicates = config["allow_duplicates"]
        
        if "allowed_ids" in config:
            allowed_ids.extend(config["allowed_ids"])
        
        if "cryptos" in config:
            for crypto in config["cryptos"]:
                nodename = backend.get_auth_manager().add_key_config(crypto)
                if nodename not in allowed_ids:
                    allowed_ids.append(nodename)

        s = self.create_subscription(storages, subscription_id, active, ifilter, allow_duplicates, allowed_ids)
        return s