"""
Persistent event loop per Celery worker process.

Celery's default behavior is to call `asyncio.run()` per task, which creates
and destroys an event loop each time. asyncpg connections retain references
to the loop they were created on at the C level, so the second task crashes
with "got Future ... attached to a different loop".

The fix: keep ONE event loop alive for the lifetime of the worker process.
All async tasks run on that single loop, so all asyncpg connections share it.
"""
import asyncio
from typing import Coroutine, TypeVar

T = TypeVar("T")

_loop: asyncio.AbstractEventLoop | None = None


def get_loop() -> asyncio.AbstractEventLoop:
    """Return the worker-local event loop, creating it on first use."""
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
    return _loop


def run_async(coro: Coroutine[None, None, T]) -> T:
    """Run a coroutine on the persistent worker loop."""
    return get_loop().run_until_complete(coro)
