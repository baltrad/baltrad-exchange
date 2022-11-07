import datetime, stat, os
import logging

from baltrad.bdbcommon import oh5, expr

#from baltrad.bdbcommon.oh5 import (
#    Attribute,
#    Group,
#    Metadata,
#    Source,
#)

logger = logging.getLogger("baltrad.exchange.odimutil")

class metadata_helper(object):
    
    @classmethod
    def metadata_from_file(self, source_manager, hasher, path):
        """creates metadata from the file
        :param path: full path to the file
        :returns the metadata
        """
        meta = oh5.Metadata.from_file(path)
        if not meta.what_source:
            raise LookupError("No source in metadata")
        
        metadata_hash = hasher.hash(meta)
        source = source_manager.get_source(meta)
        
        meta.bdb_source = source.to_string()
        meta.bdb_source_name = source.name
        meta.bdb_metadata_hash = metadata_hash
        meta.bdb_file_size = os.stat(path)[stat.ST_SIZE]
        
        logger.debug("Got a source identifier: %s"%str(meta.bdb_source))

        stored_timestamp = datetime.datetime.utcnow()
        meta.bdb_stored_date = stored_timestamp.date()
        meta.bdb_stored_time = stored_timestamp.time()

        return meta  