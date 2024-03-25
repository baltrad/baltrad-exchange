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

## Functionality to match metadata against a filter

## @file
## @author Anders Henja, SMHI
## @date 2021-08-18
import operator
import threading
import json
import re, datetime

from baltrad.bdbcommon import expr

from baltrad.bdbcommon.oh5 import (
    Source,
)

##
# Used for matching metadata against an expression
#
class metadata_matcher:
    """ Used for matching metadata against an expression
    """
    def __init__(self):
        """Constructor
        """
        self.init_evaluator()
  
    def init_evaluator(self):  
        """Sets up all operations available for the filter
        """
        evaluator = expr.Evaluator()
        evaluator.add_procedure("+", operator.add)
        evaluator.add_procedure("-", operator.sub)
        evaluator.add_procedure("*", operator.mul)
        evaluator.add_procedure("/", operator.floordiv)
        evaluator.add_procedure("=", operator.eq)
        evaluator.add_procedure("!=", operator.ne)
        evaluator.add_procedure("<", operator.lt)
        evaluator.add_procedure(">", operator.gt)
        evaluator.add_procedure(">=", operator.ge)
        evaluator.add_procedure("<=", operator.le)
        evaluator.add_procedure("and", operator.and_)
        evaluator.add_procedure("or", operator.or_)
        evaluator.add_procedure("not", operator.not_)
        evaluator.add_procedure("like", self.like)
        evaluator.add_procedure("in", self.in_)
        evaluator.add_procedure("date", lambda *args: datetime.date(*args))
        evaluator.add_procedure("time", lambda *args: datetime.time(*args))
        evaluator.add_procedure(
            "datetime", lambda *args: datetime.datetime(*args)
        )
        evaluator.add_procedure(
            "interval", lambda *args: datetime.timedelta(*args)
        )
        self.evaluator = evaluator
        self.lock = threading.Lock()
    
    def find_value(self, name, ttype):
        """Finds a value within the metadata with specified name
        :param name: The name that is requested
        :param ttype: The type we are looking for
        :return: the value if found
        """
        if name.startswith("what/source:"):
            return self.find_source(name, self.meta.source())
        elif name.startswith("_bdb/source:"):
            return self.find_source(name, Source.from_string(self.meta.bdb_source))
        elif name.startswith("_bdb/source_name"):
            return[self.meta.bdb_source_name]
        return self.find_plain(name, ttype)

    def find_source(self, name, source):
        """Finds a source identifier within the source.
        :param name: The source identifier
        :param source: The data source
        :return the found value
        """
        key = name[name.rfind(":") + 1:]
        if key in source:
            return [source[key]]
        return []
    
    def find_plain(self, name, ttype):
        """Finds any name within the metadata.
        :param name: The name of the attribute
        :param ttype: Not used
        :return: The value
        """
        result = []
        split_path = name.split("/")
        for node in self.meta.iternodes():
            if self.match_path(split_path, node.path()):
                result.append(expr.literal(node.value_str())) 
        return result
  
    def match_path(self, split_path, nodepath):
        """Matches the paths
        """
        node_split_path = nodepath.split("/")
        from_index = len(node_split_path) - len(split_path)
        if from_index < 0:
            return False
        return split_path == node_split_path[from_index:]

    def in_(self, lhs, rhs):
        """Matches if items in lhs exists in the rhs.
        :param lhs: Left hand side which is a list of values
        :param rhs: Right hand side which is matched against
        :return: True or False
        """
        return any(item in rhs for item in lhs)

    def like(self, lhs, rhs):
        """Matches against a \*-pattern.
        :param lhs: Left hand side which is a list of value
        :param rhs: Right hand side which is pattern
        :return: True or False
        """
        if isinstance(rhs, list) and len(rhs) > 0:
            rhs = rhs[0]
        pattern = rhs.replace("*", ".*")
        p = re.compile(pattern)
        for i in lhs:
            if p.match(i):
                return True
        return False

    #Synchronize!!!
    def match(self, metadata, xpr):
        """Matches the metadata against the expression. Synchronized.
        :param metadata: The metadata to be matched against
        :param xpr: The expression matched against
        :return: True or False
        """
        with self.lock:
            self.evaluator.add_procedure("attr", self.find_value)
            self.meta = metadata
            try:
                result = self.evaluator.evaluate(xpr);
                return result;
            finally:
                self.evaluator.add_procedure("attr", None)
                self.meta = None
        
