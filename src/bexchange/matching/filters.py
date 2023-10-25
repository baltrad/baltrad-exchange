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
# All filters should implement this
#
class node_filter:
    def __init__(self):
        """Constructor
        """
        pass
    
    def to_xpr(self):
        """Translates a filter object to a list of expression symbols
        :return: a list of symbols
        """
        raise NotImplementedError("")

##
# Attribute filter
#
class attribute_filter(node_filter):
    """an attribute filter that is used to match a specific attribute against a value.
    """
    def __init__(self, name, op, t, v):
        """Constructor
        :param name: The name of the attribute (or a logical name)
        :param op: The operation that should be used for comparision
        :param t: Type of the value
        :param v: The value to compare against
        """
        self.filter_type = self.name_repr()
        self.name = name
        self.operation = op
        self.value_type = t.lower()
        self.value = v

    @classmethod
    def name_repr(cls):
        """Name of this class
        """
        return "attribute_filter"

    @classmethod
    def from_value(cls, v, manager):
        """Used to create an attribute filter from a dictionary containing the information about this attribute filter. Format is:
             {"filter_type": "attribute_filter", 
              "name": "_bdb/source_name", 
              "operation": "in", 
              "value_type": "string", 
              "value": ["sehem","seang"]}

           :param v: The dictionary
           :param manager: The manager used to instantiate objects       
        """
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
        """The string representation of this instance.
        :return: the string representation
        """
        return 'attribute_filter{"name":"%s", "operation":"%s", "value_type":"%s", "value":"%s"}'%(self.name, self.operation, self.value_type, self.value)

    def to_xpr(self):
        """Creates an expression to be used when matching against metadata.
        :return: The expression
        """
        return [expr.symbol(self.operation), [expr.symbol("attr"), self.name, self.value_type], self.value]

##
# And filter
class and_filter(node_filter):
    """and filter for combining several different expressions
    """
    def __init__(self, childs):
        """Constructor
        :param childs: A list of childs
        """
        self.filter_type = self.name_repr()
        self.value = childs

    @classmethod
    def name_repr(cls):
        """Returns the name of this filter
        :return: name of this filter
        """
        return "and_filter"

    @classmethod
    def from_value(cls, value, manager):
        """Used to create an and filter from a dictionary containing the information about this and filter. Format is:
             {"filter_type": "and_filter", 
              "value": []}

           :param value: The dictionary
           :param manager: The manager used to instantiate objects       
        """
        childs = []
        if not isinstance(value, dict):
            raise Exception("Value to and_filter must be a dict")
        if not "value" in value:
            raise Exception("value to and_filter must be a list")
      
        for v in value["value"]:
            childs.append(manager.from_value(v))
        return and_filter(childs)

    def __repr__(self):
        """The string representation of this instance.
        :return: the string representation
        """
        result = 'and_filter[\n'
        first_added=False
        for child in self.value:
            if first_added:
                result = result + ",\n"
            first_added = True
            result = result + repr(child)
        result = result + "\n]"
        return result
    
    def to_xpr(self):
        """Creates an expression to be used when matching against metadata.
        :return: The expression
        """
        result = [expr.symbol("and")]
        for child in self.value:
            result.append(child.to_xpr())
        return result
    
##
# Or filter
class or_filter(node_filter):
    """or filter for combining several different expressions
    """
    def __init__(self, childs):
        """Constructor
        :param childs: A list of childs
        """
        self.filter_type = self.name_repr()
        self.value = childs

    @classmethod
    def name_repr(cls):
        """Returns the name of this filter
        :return: name of this filter
        """
        return "or_filter"

    @classmethod
    def from_value(cls, value, manager):
        """Used to create an or filter from a dictionary containing the information about this or filter. Format is:
             {"filter_type": "or_filter", 
              "value": [....]}

           :param value: The dictionary
           :param manager: The manager used to instantiate objects       
        """
        childs = []
        if not isinstance(value, dict):
            raise Exception("Value to or_filter must be a dict")
        if not "value" in value:
            raise Exception("value to or_filter must be a list")
      
        for v in value["value"]:
            childs.append(manager.from_value(v))
            
        return and_filter(childs)

    def __repr__(self):
        """The string representation of this instance.
        :return: the string representation
        """
        result = 'or_filter[\n'
        first_added=False
        for child in self.value:
            if first_added:
                result = result + ",\n"
            result = result + repr(child)
        result = result + "\n]"
        return result

    def to_xpr(self):
        """Creates an expression to be used when matching against metadata.
        :return: The expression
        """
        result = [expr.symbol("or")]
        for child in self.value:
            result.append(child.to_xpr())
        return result    
##
# Not filter
class not_filter(node_filter):
    """not filter for negating an expression
    """
    def __init__(self, child):
        """Constructor
        :param child: A child
        """
        self.filter_type = self.name_repr()
        self.value = child

    @classmethod
    def name_repr(cls):
        """Returns the name of this filter
        :return: name of this filter
        """
        return "not_filter"

    @classmethod
    def from_value(cls, value, manager):
        """Used to create a not filter from a dictionary containing the information about this not filter. Format is:
             {"filter_type": "not_filter", 
              "value": ...}

           :param value: The dictionary
           :param manager: The manager used to instantiate objects       
        """
        child = value["value"]
        return not_filter(manager.from_value(child))

    def __repr__(self):
        """The string representation of this instance.
        :return: the string representation
        """
        result = 'not_filter[\n'
        result = result + repr(self.value) + "\n]"
        return result

    def to_xpr(self):
        """Creates an expression to be used when matching against metadata.
        :return: The expression
        """
        result = [expr.symbol("not")]
        result.append(self.value.to_xpr())
        return result

##
# Always true
class always_filter(node_filter):
    """always filter for returning true
    """
    def __init__(self):
        """Constructor
        :param child: A child
        """
        self.filter_type = self.name_repr()

    @classmethod
    def name_repr(cls):
        """Returns the name of this filter
        :return: name of this filter
        """
        return "always_filter"

    @classmethod
    def from_value(cls, value, manager):
        """Used to create a not filter from a dictionary containing the information about this not filter. Format is:
             {"filter_type": "always_filter"}
           :param value: The dictionary
           :param manager: The manager used to instantiate objects       
        """
        return always_filter()

    def __repr__(self):
        """The string representation of this instance.
        :return: the string representation
        """
        result = 'always_filter'
        return result

    def to_xpr(self):
        """Creates an expression to be used when matching against metadata.
        :return: The expression
        """
        return True

class filter_manager:
    """The filter manager is used to create a filter from a dictionary or json entry
    """
    def __init__(self):
        """Constructor
        """
        self.filters={}
        self.filters[attribute_filter.name_repr()] = attribute_filter.from_value
        self.filters[and_filter.name_repr()] = and_filter.from_value
        self.filters[or_filter.name_repr()] = or_filter.from_value
        self.filters[not_filter.name_repr()] = not_filter.from_value
        self.filters[always_filter.name_repr()] = always_filter.from_value

    def from_value(self, value):
        """Creates a object from a dictionary if it can be parsed
        :param value: The dictionary. If dictionary contains "filter_type" and "value", an atempt will be made to create the filter"
        :return: A filter object on success
        :raise KeyError: If filter_type has not been registered
        """
        if "filter_type" in value and "value" in value:
            return self.filters[value["filter_type"]](value, self)
        return None

    def from_json(self, s):
        """Creates a object from a json entry if it can be parsed
        :param value: The json entry. If json entry (dictionary) contains "filter_type" and "value", an atempt will be made to create the filter"
        :return: A filter object on success
        :raise KeyError: If filter_type has not been registered
        """
        js = json.loads(s)
        parsed = self.from_value(js)
        return parsed
    
    def to_json(self, ifilter):
        """Creates a json entry from a filter
        :param ifilter: The filter to be jsonifyed...
        :return: a filter as a json string
        """
        return json.dumps(ifilter, default=lambda o: o.__dict__)
    
    def to_xpr(self, ifilter):
        """Creates an expression to be used when matching against metadata.
        :return: The expression
        """
        return ifilter.to_xpr()

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
