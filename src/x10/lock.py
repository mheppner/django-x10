import time
import logging
import contextlib
from django.core.cache import cache as django_cache

logger = logging.getLogger(__name__)


class CacheLockException(Exception):
    pass


@contextlib.contextmanager
def cache_lock(key, attempts=1, expires=120, sleep_time=1.0):
    """A context manager that holds a lock in the cache.

    Use as follows:
        try:
            with cache_lock('my_key'):
                # do critical code
        except CacheLockException:
            # handle too many tries to grab the lock

    :param key: the cache key to use for the lock
    :param attempts: max number of attempts to try grabbing the lock
    :param expires: when the lock expires
    :param sleep_time: how long to wait before checking the lock again
    """
    key = '__d_lock_%s' % key

    got_lock = False
    try:
        got_lock = _acquire_lock(key, attempts, expires, sleep_time)
        yield
    finally:
        if got_lock:
            _release_lock(key)


def _acquire_lock(key, attempts, expires, sleep_time):
    for i in range(0, attempts):
        stored = django_cache.add(key, 1, expires)
        if stored:
            return True
        if i != attempts-1:
            logger.debug(f'sleeping for {sleep_time} while trying to acquire key: {key}')
            time.sleep(sleep_time)
    raise CacheLockException('Could not acquire lock for %s' % key)


def _release_lock(key):
    django_cache.delete(key)
