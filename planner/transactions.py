"""Database transaction helper used by write operations."""

from contextlib import contextmanager

from django.db import transaction


@contextmanager
def atomic_write():
    """Run a group of related writes as one database transaction."""
    with transaction.atomic():
        yield

