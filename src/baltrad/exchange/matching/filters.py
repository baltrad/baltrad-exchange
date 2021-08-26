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

## Filters used to specify the criteria for identifiying file content.

## @file
## @author Anders Henja, SMHI
## @date 2021-08-18
import json
from baltrad.bdbcommon import oh5, expr
import threading
import json
import re

from baltrad.bdbcommon.oh5 import (
    Attribute,
    Group,
    Metadata,
    Source,
)

##
# All should implement this
class node_filter:
    def __init__(self):
        pass
    
    def to_xpr(self):
        raise NotImplementedError("")

##
# Attribute filter
#
class attribute_filter(node_filter):
    def __init__(self, name, op, t, v):
        self.filter_type = self.name_repr()
        self.name = name
        self.operation = op
        self.value_type = t.lower()
        self.value = v

    @classmethod
    def name_repr(cls):
        return "attribute_filter"

    @classmethod
    def from_value(cls, v, manager):
        if not isinstance(v, dict):
            raise Exception("Value to attribute_filter must be a dictionary")

        if "filter_type" not in v or \
            "name" not in v or \
            "operation" not in v or \
            "value_type" not in v or \
            "value" not in v:
            raise Exception("Incomplete attribute_filter, must contain filter_type, name, operation, value_type and value")

        return attribute_filter(v["name"],v["operation"],v["value_type"],v["value"])

    def __repr__(self):
        return 'attribute_filter{"name":"%s", "operation":"%s", "value_type":"%s", "value":"%s"}'%(self.name, self.operation, self.value_type, self.value)

    def to_xpr(self):
        return [expr.symbol(self.operation), [expr.symbol("attr"), self.name, self.value_type], self.value]

##
# And filter
class and_filter(node_filter):
    def __init__(self, childs):
        self.filter_type = self.name_repr()
        self.value = childs

    @classmethod
    def name_repr(cls):
        return "and_filter"

    @classmethod
    def from_value(cls, value, manager):
        childs = []
        if not isinstance(value, dict):
            raise Exception("Value to and_filter must be a dict")
        if not "value" in value:
            raise Exception("value to and_filter must be a list")
      
        for v in value["value"]:
            childs.append(manager.from_value(v))
        return and_filter(childs)

    def __repr__(self):
        result = 'and_filter[\n'
        first_added=False
        for child in self.value:
            if first_added:
                result = result + ",\n"
            result = result + repr(child)
        result = result + "\n]"
        return result
    
    def to_xpr(self):
        result = [expr.symbol("and")]
        for child in self.value:
            result.append(child.to_xpr())
        return result
    
##
# Or filter
class or_filter(node_filter):
    def __init__(self, childs):
        self.filter_type = self.name_repr()
        self.value = childs

    @classmethod
    def name_repr(cls):
        return "or_filter"

    @classmethod
    def from_value(cls, value, manager):
        childs = []
        if not isinstance(value, dict):
            raise Exception("Value to or_filter must be a dict")
        if not "value" in value:
            raise Exception("value to or_filter must be a list")
      
        for v in value["value"]:
            childs.append(manager.from_value(v))
            
        return and_filter(childs)

    def __repr__(self):
        result = 'or_filter[\n'
        first_added=False
        for child in self.value:
            if first_added:
                result = result + ",\n"
            result = result + repr(child)
        result = result + "\n]"
        return result

    def to_xpr(self):
        result = [expr.symbol("or")]
        for child in self.value:
            result.append(child.to_xpr())
        return result    
##
# Not filter
class not_filter(node_filter):
    def __init__(self, child):
        self.filter_type = self.name_repr()
        self.value = child

    @classmethod
    def name_repr(cls):
        return "not_filter"

    @classmethod
    def from_value(cls, value, manager):
        child = []
        if not isinstance(value, dict):
            raise Exception("Value to or_filter must be a dict")
        if not "value" in value:
            raise Exception("value to or_filter must be a list")
        child.append(value["value"])
        return not_filter(child)
    
    def __repr__(self):
        result = 'not_filter[\n'
        result = result + repr(self.value) + "\n]"
        return result

    def to_xpr(self):
        result = [expr.symbol("not")]
        result.append(self.value.to_xpr())
        return result
    
class filter_manager:
    def __init__(self):
        self.filters={}
        self.filters[attribute_filter.name_repr()] = attribute_filter.from_value
        self.filters[and_filter.name_repr()] = and_filter.from_value
        self.filters[or_filter.name_repr()] = or_filter.from_value
        self.filters[not_filter.name_repr()] = not_filter.from_value

    def from_value(self, value):
        if "filter_type" in value and "value" in value:
            return self.filters[value["filter_type"]](value, self)
        return None

    def from_json(self, s):
        js = json.loads(s)
        parsed = self.from_value(js)
        return parsed
    
    def to_json(self, filter):
        return json.dumps(filter, default=lambda o: o.__dict__)
    
    def to_xpr(self, filter):
        return filter.to_xpr()

if __name__=="__main__":
    mgr = filter_manager()
    #filter = and_filter([attribute_filter("what/quantity","in","STRING","DBZH,TH")])
    filter = and_filter([
        attribute_filter("_bdb/source_name","=","string","sehem"),
        attribute_filter("/what/object","=","string","PVOL")
    ])
    print(repr(filter))
    print(json.dumps(filter, default=lambda o: o.__dict__))
    print(mgr.to_xpr(filter))
