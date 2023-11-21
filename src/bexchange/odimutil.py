import datetime, stat, os
import logging

from baltrad.bdbcommon import oh5, expr

_pyhl = None
h5py = None
try:
    import _pyhl as _pyhl
except:
    pass

try:
    import h5py as h5py
except:
    pass

logger = logging.getLogger("bexchange.odimutil")

class metadata_helper(object):
    @classmethod
    def is_hdf5_file(self, filename):
        if _pyhl:
            return _pyhl.is_file_hdf5(filename) != 0
        elif h5py:
            return h5py.is_hdf5(filename)
        return False

    @classmethod
    def metadata_from_file(self, source_manager, hasher, path):
        """creates metadata from the file
        :param path: full path to the file
        :returns the metadata
        """
        if not self.is_hdf5_file(path):
            raise IOError("Not a HDF5 file: %s"%path)

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