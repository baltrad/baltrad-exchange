from __future__ import absolute_import

from baltrad.exchange.decorators.decorator import decorator_manager, decorator
import _raveio, _rave, _polarvolume, _polarscan
from tempfile import NamedTemporaryFile
import shutil

class keep_quantities_decorator(decorator):
    """Removes all quantities in a volume or scan except the ones specified.
    """
    def __init__(self, quantities):
        super(keep_quantities_decorator, self).__init__()
        self._quantities = quantities
    
    def decorate(self, inf):
        outf = inf
        try:
            a = _raveio.open(outf.name).object
            if _polarvolume.isPolarVolume(a) or _polarscan.isPolarScan(a):
    	        a.removeParametersExcept(self._quantities)
    	        newf = NamedTemporaryFile()
    	        rio = _raveio.new()
    	        rio.object = a
    	        rio.save(newf.name)
    	        outf.close()
    	        outf = newf
        except:
    	    import traceback
    	    traceback.print_exc("Failed")
        return outf

