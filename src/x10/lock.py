"""Locking mechanisms using a central cache for running critical sections of code."""
import time
import logging
import contextlib

from django.core.cache import cache as django_cache

logger = logging.getLogger(__name__)


class CacheLockException(Exception):
    """Exception for when a lock is failed."""

    pass


@contextlib.contextmanager
def cache_lock(key, attempts: int=1, expires: int=120, sleep_time: float=1.0):
    """Context manager that holds a lock in the cache.

    Use as follows:
        try:
            with cache_lock('my_key'):
                # do critical code
        except CacheLockException:
            # handle too many tries to grab the lock

    :param key: the cache key to use for the lock
    :param attempts: max number of attempts to try grabbing the lock
    :param expires: when the lock expires, seconds
    :param sleep_time: how long to wait before checking the lock again, seconds
    """
    key = f'__d_lock_{key}'

    got_lock = False
    try:
        got_lock = _acquire_lock(key, attempts, expires, sleep_time)
        yield
    finally:
        if got_lock:
            _release_lock(key)


def _acquire_lock(key: str, attempts: int, expires: int, sleep_time: float):
    """Try to acquire the lock.

    :param key: the cache key to acquire
    :param attempts: max number of attempts to try grabbing the lock
    :param expires: when the lock expires, seconds
    :param sleep_time: how long to wait before checking the lock again, seconds
    :raises CacheLockException: if the number of attempts has been reached
    """
    for i in range(0, attempts):
        stored = django_cache.add(key, 1, expires)
        if stored:
            return True
        if i != attempts-1:
            logger.debug(f'sleeping for {sleep_time} while trying to acquire key: {key}')
            time.sleep(sleep_time)
    raise CacheLockException(f'Could not acquire lock for {key}')


def _release_lock(key):
    """Release the lock by deleting the key from the cache."""
    django_cache.delete(key)
