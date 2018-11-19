from functools import wraps
from time import time
import logging

logger = logging.getLogger('CryptoArbitrageApp')
def timed(f):
  @wraps(f)
  def wrapper(*args, **kwds):
    start = time()
    result = f(*args, **kwds)
    elapsed = time() - start
    logger.info("%s took %d ms" % (f.__module__ + " " + f.__name__, elapsed*1000))
    return result
  return wrapper
