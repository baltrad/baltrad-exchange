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
    def __init__(self):
        self.init_evaluator()
  
    def init_evaluator(self):  
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
        evaluator.add_procedure("not", operator.inv)
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
    
    def find_value(self, name, type_):
        if name.startswith("what/source:"):
            return self.find_source(name, self.meta.source())
        elif name.startswith("_bdb/source:"):
            return self.find_source(name, Source.from_string(self.meta.bdb_source))
        elif name.startswith("_bdb/source_name"):
            return[self.meta.bdb_source_name]
        return self.find_plain(name, type_)

    def find_source(self, name, source):
        key = name[name.rfind(":") + 1:]
        if key in source:
            return [source[key]]
        return []
    
    def find_plain(self, name, type_):
        result = []
        split_path = name.split("/")
        for node in self.meta.iternodes():
            if self.match_path(split_path, node.path()):
                result.append(expr.literal(node.value_str())) 
        return result
  
    def match_path(self, split_path, nodepath):
        node_split_path = nodepath.split("/")
        from_index = len(node_split_path) - len(split_path)
        if from_index < 0:
            return False
        return split_path == node_split_path[from_index:]
 
    def in_(self, lhs, rhs): 
        return any(item in rhs for item in lhs)

    def like(self, lhs, rhs):
        pattern = rhs[0].replace("*", ".*")
        p = re.compile(pattern)
        for i in lhs:
            if p.match(i):
                return True
        return False

    #Synchronize!!!
    def match(self, metadata, xpr):
        with self.lock:
            self.evaluator.add_procedure("attr", self.find_value)
            self.meta = metadata
            try:
                result = self.evaluator.evaluate(xpr);
                return result;
            finally:
                self.evaluator.add_procedure("attr", None)
                self.meta = None
        
