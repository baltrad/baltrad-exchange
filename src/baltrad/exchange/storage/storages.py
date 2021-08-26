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

## Various types of storages.

## @file
## @author Anders Henja, SMHI
## @date 2021-08-18
import json
import logging
import os
import shutil
from baltrad.exchange.naming import namer
logger = logging.getLogger("baltrad.exchange.server.backend")

class storage:
    def __init__(self):
        pass
    def name(self):
        raise NotImplementedError()
    def store(self, path):
        raise NotImplementedError()

class none_storage(storage):
    def __init__(self, name):
        self.type = self.name_repr()
        self._name = name

    def store(self, path, meta):
        logger.debug("Using storage %s of type %s"%(self.name(), self.name_repr()))

    def name(self):
        return self._name

    @classmethod
    def name_repr(cls):
        return "none_storage"

    @classmethod
    def from_value(cls, v):
        if "name" not in v:
            raise Exception("Incomplete none_storage, must contain storage_type and name")
        return none_storage(v["name"])

class file_store:
    def __init__(self, path, name_pattern):
        self.path = path
        self.name_pattern = name_pattern
        self.namer = namer.metadata_namer(self.name_pattern)
    
    def store(self, path, meta):
        oname = "%s/%s"%(self.path, self.namer.name(meta))
        dname = os.path.dirname(oname)
        if not os.path.exists(dname):
            os.makedirs(dname, exist_ok=True)    
        shutil.copy(path, oname)        
        logger.info("Stored file: %s"%(oname))

class file_storage(storage):
    def __init__(self, name, structure_d):
        self.type = self.name_repr()
        self._name = name
        self.structure_d = structure_d
        self.structures = {}
        for s in self.structure_d:
            if ("object" in s and not s["object"]) or "object" not in s:
                self.structures["default"]=file_store(s["path"],s["name_pattern"])
            else:
                self.structures[s["object"]]=file_store(s["path"],s["name_pattern"])

    def get_attribute_value(self, name, meta):
        try:
            return meta.node(name).value
        except LookupError:
            return None

    def store(self, path, meta):
        q = self.get_attribute_value("/what/object", meta)
        logger.debug("Using storage %s"%str(self.structures))
        if q in self.structures:
            return self.structures[q].store(path, meta)
        elif "default" in self.structures:
            return self.structures["default"].store(path, meta)
        else:
            logger.info("Ignoring %s object of type: " % q)

    def name(self):
        return self._name

    @classmethod
    def name_repr(cls):
        return "file_storage"

    @classmethod
    def from_value(cls, v):
        return file_storage(v["name"], v["structure"])
        #if "name" not in v or "path" not in v or "name_pattern" not in v:
        #    raise Exception("Incomplete none_storage, must contain storage_type, name, path & name_pattern")
        #return file_storage(v["name"], v["path"], v["name_pattern"])
        
class storage_manager:
    def __init__(self):
        self.storage_types={}
        self.storage_types[none_storage.name_repr()] = none_storage.from_value
        self.storage_types[file_storage.name_repr()] = file_storage.from_value
        self.storage={}
        
    def from_value(self, value):
        if "storage_type" in value and "name" in value:
            return self.storage_types[value["storage_type"]](value)
        return None

    def from_json(self, s):
        js = json.loads(s)
        parsed = self.from_value(js)
        return parsed
    
    def to_json(self, storage):
        return json.dumps(storage, default=lambda o: o.__dict__)
    
    def add_storage(self, storage):
        self.storage[storage.name()] = storage
    
    def get_storage(self, name):
        return self.storage[name]
    
    def has_storage(self, name):
        return name in self.storage
    
    def store(self, name, path, meta):
        self.storage[name].store(path, meta)
        
