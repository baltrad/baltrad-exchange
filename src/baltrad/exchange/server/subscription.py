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
    def __init__(self, storages, active=True, ifilter=None, nodenames=[]):
        """Constructor
        :param storages: List of storage names
        :param filter: A filter instance
        :param nodenames: A list of nodenames that should be allowed. 
        """
        self._storages = storages
        self._active = active
        self._filter = ifilter
        self._nodenames = nodenames
    
    def storages(self):
        """
        :return the storage names
        """
        return self._storages
    
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
    
    def nodenames(self):
        """
        :return the nodenames
        """
        return self._nodenames

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
    def create_subscription(self, storages, active, ifilter, nodenames):
        """Creates a subscription instance
        :param storages: List of storage names
        :param active: If subscription should be set to active or not
        :param ifilter: A filter instances
        :param nodenames: A list of nodenames that should be allowed for this subscription
        """
        return subscription(storages, active, ifilter, nodenames)
    
    @classmethod
    def from_conf(self, config, backend):
        filter_manager = filters.filter_manager()
        storages=[]
        active=True
        ifilter = None
        nodenames = []
        
        if "storage" in config:
            storages = config["storage"]
            if not isinstance(storages, list):
                storages = [storages]
            
        if "active" in config:
            active = config["active"]
        
        if "filter" in config:
            ifilter = filter_manager.from_value(config["filter"])
        
        if "nodenames" in config:
            nodenames.extend(config["nodenames"])
        
        if "cryptos" in config:
            for crypto in config["cryptos"]:
                nodename = backend.get_auth_manager().add_key_config(crypto)
                if nodename not in nodenames:
                    nodenames.append(nodename)

        s = self.create_subscription(storages, active, ifilter, nodenames)
        return s